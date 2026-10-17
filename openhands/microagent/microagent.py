import io
import re
from pathlib import Path
from typing import List, Union

import frontmatter
from pydantic import BaseModel

from openhands.core.exceptions import (
    MicroAgentValidationError,
)
from openhands.microagent.types import MicroAgentMetadata, MicroAgentType


class BaseMicroAgent(BaseModel):
    """Base class for all microagents."""

    name: str
    content: str
    metadata: MicroAgentMetadata
    source: str  # path to the file
    type: MicroAgentType

    @classmethod
    def load(
        cls, path: Union[str, Path], file_content: str | None = None
    ) -> 'BaseMicroAgent':
        """Load a microagent from a markdown file with frontmatter."""
        path = Path(path) if isinstance(path, str) else path

        # Only load directly from path if file_content is not provided
        if file_content is None:
            with open(path) as f:
                file_content = f.read()

        # Legacy repo instructions are stored in .openhands_instructions
        if path.name == '.openhands_instructions':
            return RepoMicroAgent(
                name='repo_legacy',
                content=file_content,
                metadata=MicroAgentMetadata(name='repo_legacy'),
                source=str(path),
                type=MicroAgentType.REPO_KNOWLEDGE,
            )

        file_io = io.StringIO(file_content)
        loaded = frontmatter.load(file_io)
        content = loaded.content
        try:
            metadata = MicroAgentMetadata(**loaded.metadata)
        except Exception as e:
            raise MicroAgentValidationError(f'Error loading metadata: {e}') from e

        # Create appropriate subclass based on type
        subclass_map = {
            MicroAgentType.KNOWLEDGE: KnowledgeMicroAgent,
            MicroAgentType.REPO_KNOWLEDGE: RepoMicroAgent,
            MicroAgentType.TASK: TaskMicroAgent,
        }
        if metadata.type not in subclass_map:
            raise ValueError(f'Unknown microagent type: {metadata.type}')

        agent_class = subclass_map[metadata.type]
        return agent_class(
            name=metadata.name,
            content=content,
            metadata=metadata,
            source=str(path),
            type=metadata.type,
        )


class KnowledgeMicroAgent(BaseMicroAgent):
    """Knowledge micro-agents provide specialized expertise that's triggered by keywords in conversations. They help with:
    - Language best practices
    - Framework guidelines
    - Common patterns
    - Tool usage
    """

    def __init__(self, **data):
        super().__init__(**data)
        if self.type != MicroAgentType.KNOWLEDGE:
            raise ValueError('KnowledgeMicroAgent must have type KNOWLEDGE')

    def match_trigger(self, message: str, repo_name: str | None = None) -> str | None:
        """Match a trigger in the message or repository name.

        It returns the first trigger that matches the message or repository name.

        Args:
            message: The message to check for triggers
            repo_name: Optional repository name to check against repo_triggers

        Returns:
            The matched trigger or None if no match is found
        """
        # Check repository name triggers if provided
        if repo_name and self.repo_triggers:
            repo_name = repo_name.lower()
            for trigger in self.repo_triggers:
                if trigger.lower() == repo_name:
                    return f'repo:{trigger}'

        # Check message triggers
        message = message.lower()
        for trigger in self.triggers:
            if trigger.lower() in message:
                return trigger
        return None

    @property
    def triggers(self) -> list[str]:
        return self.metadata.triggers

    @property
    def repo_triggers(self) -> list[str]:
        return self.metadata.repo_triggers


class RepoMicroAgent(BaseMicroAgent):
    """MicroAgent specialized for repository-specific knowledge and guidelines.

    RepoMicroAgents are loaded from `.openhands/microagents/repo.md` files within repositories
    and contain private, repository-specific instructions that are automatically loaded when
    working with that repository. They are ideal for:
        - Repository-specific guidelines
        - Team practices and conventions
        - Project-specific workflows
        - Custom documentation references
    """

    def __init__(self, **data):
        super().__init__(**data)
        if self.type != MicroAgentType.REPO_KNOWLEDGE:
            raise ValueError('RepoMicroAgent must have type REPO_KNOWLEDGE')


class TaskMicroAgent(BaseMicroAgent):
    """MicroAgent specialized for task-based operations."""

    def __init__(self, **data):
        super().__init__(**data)
        if self.type != MicroAgentType.TASK:
            raise ValueError('TaskMicroAgent must have type TASK')


class TaskMicroagent(KnowledgeMicroagent):
    """TaskMicroagent is a special type of KnowledgeMicroagent that requires user input.

    These microagents are triggered by a special format: "/{agent_name}"
    and will prompt the user for any required inputs before proceeding.
    """

    def __init__(self, **data):
        super().__init__(**data)
        if self.type != MicroagentType.TASK:
            raise ValueError(
                f'TaskMicroagent initialized with incorrect type: {self.type}'
            )

        # Append a prompt to ask for missing variables
        self._append_missing_variables_prompt()

    def _append_missing_variables_prompt(self) -> None:
        """Append a prompt to ask for missing variables."""
        # Check if the content contains any variables or has inputs defined
        if not self.requires_user_input() and not self.metadata.inputs:
            return

        prompt = "\n\nIf the user didn't provide any of these variables, ask the user to provide them first before the agent can proceed with the task."
        self.content += prompt

    def extract_variables(self, content: str) -> List[str]:
        """Extract variables from the content.

        Variables are in the format ${variable_name}.
        """
        pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.findall(pattern, content)
        return matches

    def requires_user_input(self) -> bool:
        """Check if this microagent requires user input.

        Returns True if the content contains variables in the format ${variable_name}.
        """
        # Check if the content contains any variables
        variables = self.extract_variables(self.content)
        logger.debug(f'This microagent requires user input: {variables}')
        return len(variables) > 0

    @property
    def inputs(self) -> List[InputMetadata]:
        """Get the inputs for this microagent."""
        return self.metadata.inputs


def load_microagents_from_dir(
    microagent_dir: Union[str, Path],
) -> tuple[
    dict[str, RepoMicroAgent], dict[str, KnowledgeMicroAgent], dict[str, TaskMicroAgent]
]:
    """Load all microagents from the given directory.

    Args:
        microagent_dir: Path to the microagents directory.

    Returns:
        Tuple of (repo_agents, knowledge_agents) dictionaries
    """
    if isinstance(microagent_dir, str):
        microagent_dir = Path(microagent_dir)

    repo_agents = {}
    knowledge_agents = {}
    task_agents = {}

    # Load all agents
    for file in microagent_dir.rglob('*.md'):
        # skip README.md
        if file.name == 'README.md':
            continue
        try:
            agent = BaseMicroAgent.load(file)
            if isinstance(agent, RepoMicroAgent):
                repo_agents[agent.name] = agent
            elif isinstance(agent, KnowledgeMicroAgent):
                knowledge_agents[agent.name] = agent
            elif isinstance(agent, TaskMicroAgent):
                task_agents[agent.name] = agent
        except Exception as e:
            raise ValueError(f'Error loading agent from {file}: {e}')

    return repo_agents, knowledge_agents, task_agents
