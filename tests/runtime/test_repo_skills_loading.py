"""Runtime test: repo skills from .openhands/skills are discoverable in a remote workspace.

This is a light-weight integration test that boots a DockerRuntime (action execution
server), writes a .openhands/skills/repo.md inside the sandbox workspace, then runs the
V1 app-server skill loader against that workspace via a minimal execute_command adapter.

We specifically verify that a markdown file with NO `triggers` frontmatter produces a
Skill with trigger=None (always-active repo context).
"""

from dataclasses import dataclass

import pytest

from openhands.app_server.app_conversation import skill_loader
from openhands.events.action.action import ActionSecurityRisk
from openhands.events.action.commands import CmdRunAction
from tests.runtime.conftest import _close_test_runtime, _load_runtime


@dataclass
class _CommandResult:
    exit_code: int
    stdout: str


class _RuntimeWorkspaceAdapter:
    """Minimal AsyncRemoteWorkspace-like adapter for skill_loader tests."""

    def __init__(self, runtime):
        self._runtime = runtime

    async def execute_command(
        self, command: str, cwd: str | None = None, timeout: float = 30.0
    ):
        action = CmdRunAction(
            command=command,
            cwd=cwd,
            security_risk=ActionSecurityRisk.LOW,
        )
        obs = self._runtime.run_action(action)
        return _CommandResult(exit_code=obs.exit_code, stdout=obs.content or '')


@pytest.mark.asyncio
async def test_repo_skill_repo_md_without_triggers_is_repo_context(
    temp_dir, runtime_cls, run_as_openhands
):
    if runtime_cls.__name__ != 'DockerRuntime':
        pytest.skip(
            'This runtime/integration test is only implemented for DockerRuntime'
        )

    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_openhands)
    try:
        sandbox_root = config.workspace_mount_path_in_sandbox
        repo_root = sandbox_root

        # Create .openhands/skills/repo.md in the *sandbox workspace*.
        # No triggers frontmatter => trigger=None
        cmd = (
            f'mkdir -p {repo_root}/.openhands/skills && '
            f"cat > {repo_root}/.openhands/skills/repo.md <<'EOF'\n"
            'This is repo context loaded from .openhands/skills/repo.md\n'
            'EOF\n'
        )
        runtime.run_action(
            CmdRunAction(command=cmd, security_risk=ActionSecurityRisk.LOW)
        )

        ws = _RuntimeWorkspaceAdapter(runtime)

        # selected_repository=None -> repo_root = working_dir
        # Sanity check: file is actually present in the sandbox.
        check = runtime.run_action(
            CmdRunAction(
                command=f'ls -la {repo_root}/.openhands/skills && cat {repo_root}/.openhands/skills/repo.md',
                security_risk=ActionSecurityRisk.LOW,
            )
        )
        assert check.exit_code == 0, check

        skills = await skill_loader.load_repo_skills(
            ws, selected_repository=None, working_dir=repo_root
        )

        repo_skill = next(
            (s for s in skills if s.name.endswith('repo') or s.name == 'repo'), None
        )
        assert repo_skill is not None, (
            f'Expected repo skill; got {[s.name for s in skills]}'
        )
        assert repo_skill.trigger is None
        assert 'This is repo context loaded' in repo_skill.content

    finally:
        _close_test_runtime(runtime)
