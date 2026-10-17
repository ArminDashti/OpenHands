"""This file contains the function calling implementation for different actions.

This is similar to the functionality of `CodeActResponseParser`.
"""

import json
import re

from litellm import (
    ChatCompletionToolParam,
    ModelResponse,
)

from openhands.agenthub.codeact_agent.tools import (
    BrowserTool,
    IPythonTool,
    LLMBasedFileEditTool,
    ThinkTool,
    WebReadTool,
    create_cmd_run_tool,
    create_str_replace_editor_tool,
    ApplyPatchTool,
)
from openhands.agenthub.planning_agent.tools import (
    DelegateToCodeActAgentTool,
    DelegateToTaskSolvingAgentTool,
    FinishTool,
    PlanningTool,
)
from openhands.core.exceptions import (
    FunctionCallNotExistsError,
    FunctionCallValidationError,
)
from openhands.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    AgentThinkAction,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    CreatePlanAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    IPythonRunCellAction,
    MessageAction,
)
from openhands.events.action.mcp import McpAction
from openhands.events.event import FileEditSource, FileReadSource
from openhands.events.tool import ToolCallMetadata
from openhands.mcp import MCPClientTool


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
    if hasattr(assistant_msg, 'tool_calls') and assistant_msg.tool_calls:
        # Check if there's assistant_msg.content. If so, add it to the thought
        thought = ''
        if isinstance(assistant_msg.content, str):
            thought = assistant_msg.content
        elif isinstance(assistant_msg.content, list):
            for msg in assistant_msg.content:
                if msg['type'] == 'text':
                    thought += msg['text']

        # Process each tool call to OpenHands action
        for i, tool_call in enumerate(assistant_msg.tool_calls):
            action: Action
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.decoder.JSONDecodeError as e:
                raise RuntimeError(
                    f'Failed to parse tool call arguments: {tool_call.function.arguments}'
                ) from e

            # ================================================
            # BashTool (Unified)
            # ================================================
            if tool_call.function.name == EXECUTE_BASH_TOOL_NAME:
                # Use unified tool validation
                bash_tool = _TOOL_INSTANCES[EXECUTE_BASH_TOOL_NAME]
                try:
                    validated_args = bash_tool.validate_parameters(arguments)
                except FunctionCallValidationError as e:
                    msg = str(e)
                    m = re.search(r"Missing required parameter '([^']+)'", msg)
                    if m:
                        raise FunctionCallValidationError(
                            f'Missing required argument "{m.group(1)}"'
                        ) from e
                    raise FunctionCallValidationError(msg) from e

                # convert is_input to boolean
                is_input = bool(validated_args.get('is_input', False))
                action = CmdRunAction(
                    command=validated_args['command'], is_input=is_input
                )

                # Set hard timeout if provided
                if 'timeout' in validated_args:
                    try:
                        action.set_hard_timeout(float(validated_args['timeout']))
                    except ValueError as e:
                        raise FunctionCallValidationError(
                            f"Invalid float passed to 'timeout' argument: {validated_args['timeout']}"
                        ) from e

            # ================================================
            # CmdRunTool (Legacy - fallback)
            # ================================================
            elif tool_call.function.name == create_cmd_run_tool()['function']['name']:
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

                # Set safety_risk from arguments if provided
                set_safety_risk_from_arguments(action, arguments)
            elif tool_call.function.name == 'delegate_to_browsing_agent':
                action = AgentDelegateAction(
                    agent='BrowsingAgent',
                    inputs=arguments,
                )

            # ================================================
            # FinishTool (Unified)
            # ================================================
            elif tool_call.function.name == FINISH_TOOL_NAME:
                # Use unified tool validation
                finish_tool = _TOOL_INSTANCES[FINISH_TOOL_NAME]
                try:
                    validated_args = finish_tool.validate_parameters(arguments)
                except FunctionCallValidationError as e:
                    msg = str(e)
                    m = re.search(r"Missing required parameter '([^']+)'", msg)
                    if m:
                        raise FunctionCallValidationError(
                            f'Missing required argument "{m.group(1)}"'
                        ) from e
                    raise FunctionCallValidationError(msg) from e

                action = AgentFinishAction(
                    final_thought=validated_args.get('summary', ''),
                    outputs=validated_args.get('outputs', {}),
                )

            # ================================================
            # AgentFinishAction (Legacy - fallback)
            # ================================================
            elif tool_call.function.name == LegacyFinishTool['function']['name']:
                action = AgentFinishAction(
                    final_thought=arguments.get('message', ''),
                    task_completed=arguments.get('task_completed', None),
                )

            # ================================================
            # LLMBasedFileEditTool (LLM-based file editor)
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

            # ================================================
            # FileEditorTool (Unified)
            # ================================================
            elif tool_call.function.name == STR_REPLACE_EDITOR_TOOL_NAME:
                # Use unified tool validation
                file_editor_tool = _TOOL_INSTANCES[STR_REPLACE_EDITOR_TOOL_NAME]
                try:
                    validated_args = file_editor_tool.validate_parameters(arguments)
                except FunctionCallValidationError as e:
                    msg = str(e)
                    m = re.search(r"Missing required parameter '([^']+)'", msg)
                    if m:
                        raise FunctionCallValidationError(
                            f'Missing required argument "{m.group(1)}"'
                        ) from e
                    raise FunctionCallValidationError(msg) from e

                path = validated_args['path']
                command = validated_args['command']

                if command == 'view':
                    action = FileReadAction(
                        path=path,
                        impl_source=FileReadSource.OH_ACI,
                        view_range=validated_args.get('view_range', None),
                    )
                else:
                    # Remove view_range for edit commands
                    edit_kwargs = {
                        k: v
                        for k, v in validated_args.items()
                        if k not in ['command', 'path', 'view_range']
                    }

                    action = FileEditAction(
                        path=path,
                        command=command,
                        impl_source=FileEditSource.OH_ACI,
                        **edit_kwargs,
                    )

            # ================================================
            # str_replace_editor (Legacy - fallback)
            # ================================================
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

                    # Set safety_risk from arguments if provided
                    set_safety_risk_from_arguments(action, arguments)
                else:
                    if 'view_range' in other_kwargs:
                        other_kwargs.pop('view_range')
                    action = FileEditAction(
                        path=path,
                        command=command,
                        impl_source=FileEditSource.OH_ACI,
                        **other_kwargs,
                    )
            elif tool_call.function.name == 'apply_patch':
                if 'input' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "input" in tool call {tool_call.function.name}'
                    )
                action = FileEditAction(
                    path=path,
                    command=arguments['input'],
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
            elif tool_call.function.name == BROWSER_TOOL_NAME:
                # Use unified tool validation
                browser_tool = _TOOL_INSTANCES[BROWSER_TOOL_NAME]
                try:
                    validated_args = browser_tool.validate_parameters(arguments)
                except FunctionCallValidationError as e:
                    msg = str(e)
                    m = re.search(r"Missing required parameter '([^']+)'", msg)
                    if m:
                        raise FunctionCallValidationError(
                            f'Missing required argument "{m.group(1)}"'
                        ) from e
                    raise FunctionCallValidationError(msg) from e

                action = BrowseInteractiveAction(browser_actions=validated_args['code'])

            # ================================================
            # BrowserTool (Legacy - fallback)
            # ================================================
            elif tool_call.function.name == LegacyBrowserTool['function']['name']:
                if 'code' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "code" in tool call {tool_call.function.name}'
                    )
                action = BrowseInteractiveAction(browser_actions=arguments['code'])

                # Set safety_risk from arguments if provided
                set_safety_risk_from_arguments(action, arguments)

            # ================================================
            # TaskTrackingAction
            # ================================================
            elif tool_call.function.name == TASK_TRACKER_TOOL_NAME:
                if 'command' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "command" in tool call {tool_call.function.name}'
                    )
                if arguments['command'] == 'plan' and 'task_list' not in arguments:
                    raise FunctionCallValidationError(
                        f'Missing required argument "task_list" for "plan" command in tool call {tool_call.function.name}'
                    )

                action = TaskTrackingAction(
                    command=arguments['command'],
                    task_list=arguments.get('task_list', []),
                )

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
            # CreatePlanAction
            # ================================================
            elif tool_call.function.name == PlanningTool['function']['name']:
                action = CreatePlanAction(
                    plan_id=arguments.get('plan_id', ''),
                    title=arguments.get('title', ''),
                    tasks=arguments.get('tasks', []),
                )

            elif (
                tool_call.function.name
                == DelegateToCodeActAgentTool['function']['name']
            ):
                action = AgentDelegateAction(
                    agent='CodeActAgent',
                    inputs=arguments,
                )
            elif (
                tool_call.function.name
                == DelegateToTaskSolvingAgentTool['function']['name']
            ):
                action = AgentDelegateAction(
                    agent='TaskSolvingAgent',
                    inputs=arguments,
                )

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

            # We only add thought to the first action
            if i == 0:
                action = combine_thought(action, thought)
            # Add metadata for tool calling
            action.tool_call_metadata = ToolCallMetadata(
                tool_call_id=tool_call.id,
                function_name=tool_call.function.name,
                model_response=response,
                total_calls_in_response=len(assistant_msg.tool_calls),
            )
            actions.append(action)
    else:
        actions.append(
            MessageAction(
                content=str(assistant_msg.content) if assistant_msg.content else '',
                wait_for_response=True,
            )
        )

    assert len(actions) >= 1
    return actions


def get_tools() -> list[ChatCompletionToolParam]:
    return [PlanningTool, FinishTool]


def get_delegation_tools() -> list[ChatCompletionToolParam]:
    return [
        DelegateToCodeActAgentTool,
        DelegateToTaskSolvingAgentTool,
    ]
