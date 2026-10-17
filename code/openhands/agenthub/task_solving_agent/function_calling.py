"""This file contains the function calling implementation for different actions.

This is similar to the functionality of `CodeActResponseParser`.
"""

import json

from litellm import (
    ChatCompletionToolParam,
    ModelResponse,
)

from openhands.agenthub.codeact_agent.llm_diff_parser import (
    DiffBlock,
    parse_llm_response_for_diffs,
)
from openhands.agenthub.codeact_agent.tools import (
    BrowserTool,
    IPythonTool,
    ListDirectoryTool,
    LLMBasedFileEditTool,
    ThinkTool,
    WebReadTool,
    create_cmd_run_tool,
    create_str_replace_editor_tool,
)
from openhands.agenthub.task_solving_agent.tools import (
    FinishTool,
)
from openhands.core.exceptions import (
    FunctionCallNotExistsError,
    FunctionCallValidationError,
)
from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    AgentThinkAction,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    IPythonRunCellAction,
    MessageAction,
)
from openhands.events.action.mcp import McpAction
from openhands.events.event import FileEditSource, FileReadSource
from openhands.events.tool import ToolCallMetadata
from openhands.mcp import MCPClientTool

_finish_count = 0


def combine_thought(action: Action, thought: str) -> Action:
    if not hasattr(action, 'thought'):
        return action
    if thought and action.thought:
        action.thought = f'{thought}\n{action.thought}'
    elif thought:
        action.thought = thought
    return action


def response_to_actions(response: ModelResponse) -> list[Action]:
    actions: list[Action] = []
    assert len(response.choices) == 1, 'Only one choice is supported for now'
    choice = response.choices[0]
    assistant_msg = choice.message

    # 1. Extract message content
    if isinstance(assistant_msg.content, str):
        message_content = assistant_msg.content
    elif isinstance(assistant_msg.content, list):
        for msg in assistant_msg.content:
            if msg['type'] == 'text':
                message_content += msg['text']

    # 2. Try parsing diff blocks if enabled and content exists
    if is_llm_diff_enabled and message_content:
        logger.debug('LLM Diff mode enabled, attempting to parse response content.')
        try:
            # Call the updated parser, expecting list[DiffBlock]
            parsed_blocks: list[DiffBlock] = parse_llm_response_for_diffs(
                message_content
            )

            if parsed_blocks:  # Check if the list is not empty
                logger.info(
                    f'Parsed {len(parsed_blocks)} diff blocks from LLM response.'
                )
                # Create FileEditActions from the DiffBlock objects
                for block in parsed_blocks:
                    action = FileEditAction(
                        path=block.filename,
                        search=block.search,
                        replace=block.replace,
                        impl_source=FileEditSource.LLM_DIFF,
                    )
                    parsed_llm_diff_actions.append(action)

        except ValueError as e:
            logger.error(f'Error parsing LLM diff blocks: {e}')
            diff_parse_error = e  # Store error for potential later use
        except Exception as e:
            logger.error(
                f'Unexpected error during LLM diff parsing: {e}', exc_info=True
            )
            diff_parse_error = e  # Store error

    # 3. Process tool calls if they exist
    tool_calls_exist = hasattr(assistant_msg, 'tool_calls') and assistant_msg.tool_calls
    if tool_calls_exist:
        # Process each tool call
        for i, tool_call in enumerate(assistant_msg.tool_calls):
            logger.debug(f'Tool call in function_calling.py: {tool_call}')
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.decoder.JSONDecodeError as e:
                raise RuntimeError(
                    f'Failed to parse tool call arguments: {tool_call.function.arguments}'
                ) from e

            # ================================================
            # CmdRunTool (Bash)
            # ================================================

            if tool_call.function.name == create_cmd_run_tool()['function']['name']:
                if 'command' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "command" in tool call {tool_call.function.name}'
                    )
                # convert is_input to boolean
                is_input = arguments.get('is_input', 'false') == 'true'
                action = CmdRunAction(command=arguments['command'], is_input=is_input)

            # ================================================
            # IPythonTool (Jupyter)
            # ================================================
            elif tool_call.function.name == IPythonTool['function']['name']:
                if 'code' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "code" in tool call {tool_call.function.name}'
                    )
                action = IPythonRunCellAction(code=arguments['code'])
            elif tool_call.function.name == 'delegate_to_browsing_agent':
                action = AgentDelegateAction(
                    agent='BrowsingAgent',
                    prompt=arguments.get('prompt', ''),
                    inputs={},
                )

            # ================================================
            # AgentFinishAction
            # ================================================
            elif tool_call.function.name == FinishTool['function']['name']:
                # hack: think first, and then finish only if finish action is called again
                # if it turns out to be useful, we should rethink about the design and make
                # it generally useful. One idea is to make a micro-agent that gets triggered
                # whenever a function call is made. We need to be able to track the state
                # (e.g. the number of times the function has been called) and have the micro-agent
                # make a decision based on the state, PLUS the history of the conversation
                # (e.g. the original user intent).
                global _finish_count
                if _finish_count == 0:
                    action = MessageAction(
                        content='Final thought: '
                        + arguments.get('message', '')
                        + '\nPlease double check the final answer and make sure it adheres to the instructions, including the format requirements, then call finish function again with the final answer.',
                        wait_for_response=False,
                    )
                    _finish_count += 1
                else:
                    action = AgentFinishAction(
                        final_thought=arguments.get('message', ''),
                        task_completed=arguments.get('task_completed', None),
                    )

            # ================================================
            # LLMBasedFileEditTool (LLM-based file editor, deprecated)
            # ================================================
            elif tool_call.function.name == LLMBasedFileEditTool['function']['name']:
                if 'path' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "path" in tool call {tool_call.function.name}'
                    )
                if 'content' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "content" in tool call {tool_call.function.name}'
                    )
                action = FileEditAction(
                    path=arguments['path'],
                    content=arguments['content'],
                    start=arguments.get('start', 1),
                    end=arguments.get('end', -1),
                )
            elif (
                tool_call.function.name
                == create_str_replace_editor_tool()['function']['name']
            ):
                if 'command' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "command" in tool call {tool_call.function.name}'
                    )
                if 'path' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "path" in tool call {tool_call.function.name}'
                    )
                path = arguments['path']
                command = arguments['command']
                other_kwargs = {
                    k: v for k, v in arguments.items() if k not in ['command', 'path']
                }

                if command == 'view':
                    action = FileReadAction(
                        path=path,
                        impl_source=FileReadSource.OH_ACI,
                        view_range=other_kwargs.get('view_range', None),
                    )
                else:
                    if 'view_range' in other_kwargs:
                        # Remove view_range from other_kwargs since it is not needed for FileEditAction
                        other_kwargs.pop('view_range')
                    action = FileEditAction(
                        path=path,
                        command=command,
                        impl_source=FileEditSource.OH_ACI,
                        **other_kwargs,
                    )
            # ================================================
            # New Utility Tools (Routing to OH_ACI)
            # ================================================
            elif tool_call.function.name == ViewFileTool['function']['name']:
                if 'path' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "path" in tool call {tool_call.function.name}'
                    )
                action = FileReadAction(
                    path=arguments['path'],
                    impl_source=FileReadSource.OH_ACI,
                    view_range=arguments.get('view_range', None),
                )
            elif tool_call.function.name == ListDirectoryTool['function']['name']:
                if 'path' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "path" in tool call {tool_call.function.name}'
                    )
                action = FileReadAction(
                    path=arguments['path'],
                    impl_source=FileReadSource.OH_ACI,
                    # view_range is not applicable for directories
                )
            elif tool_call.function.name == UndoEditTool['function']['name']:
                if 'path' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "path" in tool call {tool_call.function.name}'
                    )
                action = FileEditAction(
                    path=arguments['path'],
                    command='undo_edit',
                    impl_source=FileEditSource.OH_ACI,
                )
            # ================================================
            # AgentThinkAction
            # ================================================
            elif tool_call.function.name == ThinkTool['function']['name']:
                action = AgentThinkAction(thought=arguments.get('thought', ''))

            # ================================================
            # BrowserTool
            # ================================================
            elif tool_call.function.name == BrowserTool['function']['name']:
                if 'code' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "code" in tool call {tool_call.function.name}'
                    )
                action = BrowseInteractiveAction(browser_actions=arguments['code'])

            # ================================================
            # WebReadTool (simplified browsing)
            # ================================================
            elif tool_call.function.name == WebReadTool['function']['name']:
                if 'url' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "url" in tool call {tool_call.function.name}'
                    )
                action = BrowseURLAction(url=arguments['url'])

            # ================================================
            # McpAction (MCP)
            # ================================================
            elif tool_call.function.name.endswith(MCPClientTool.postfix()):
                action = McpAction(
                    name=tool_call.function.name.rstrip(MCPClientTool.postfix()),
                    arguments=tool_call.function.arguments,
                )
            else:
                raise FunctionCallNotExistsError(
                    f'Tool {tool_call.function.name} is not registered. (arguments: {arguments}). Please check the tool name and retry with an existing tool.'
                )

            # Add metadata for tool calling
            action.tool_call_metadata = ToolCallMetadata(
                tool_call_id=tool_call.id,
                function_name=tool_call.function.name,
                model_response=response,
                total_calls_in_response=len(assistant_msg.tool_calls),
            )
            tool_call_actions.append(action)

    # 4. Combine actions: diffs first (if any), then tool calls (if any)
    all_actions.extend(parsed_llm_diff_actions)
    all_actions.extend(tool_call_actions)

    # 5. Handle the case where no actions were generated (neither diffs nor tool calls)
    if not all_actions:
        # If there was a diff parsing error, report it (even if no blocks were parsed)
        if diff_parse_error:
            all_actions.append(
                MessageAction(
                    content=f'[Error parsing diff blocks: {diff_parse_error}]\nOriginal Content:\n{message_content}',
                    wait_for_response=True,
                )
            )
        # Otherwise, treat as a regular message if content exists
        elif message_content:
            all_actions.append(
                MessageAction(
                    content=message_content,
                    wait_for_response=True,
                )
            )
        # If no actions AND no content, add a default Think action
        else:
            logger.warning(
                f'No actions generated and no message content for response: {response.id}'
            )
            all_actions.append(
                AgentThinkAction(
                    thought='[No actionable content or tool calls found in response]'
                )
            )

    # If actions *were* generated, determine and apply thought
    else:
        # 6. Determine contextual thought and apply to the first non-AgentThinkAction
        contextual_thought = message_content.strip() if message_content else None
        if contextual_thought:
            for i, action in enumerate(all_actions):
                if not isinstance(action, AgentThinkAction):
                    all_actions[i] = combine_thought(action, contextual_thought)
                    break  # Apply thought only to the first eligible action

    # 7. Add response id to all actions
    for action in all_actions:
        action.response_id = response.id

    # Add critic score to the LAST action
    if isinstance(response, ModelResponseWithCriticScore):
        actions[-1].critic_score = response.critic_score

    assert len(actions) >= 1
    return actions


def get_tools() -> list[ChatCompletionToolParam]:
    return [FinishTool]
