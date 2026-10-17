export interface CodeExample {
  language: string;
  label?: string;
  code: string;
}

export interface PageSection {
  type: 'heading' | 'paragraph' | 'code' | 'table' | 'callout' | 'list' | 'steps';
  level?: number;
  content?: string;
  items?: string[];
  headers?: string[];
  rows?: string[][];
  variant?: 'info' | 'warning' | 'success' | 'danger';
  steps?: { title: string; content: string }[];
  examples?: CodeExample[];
}

export interface PageContent {
  title: string;
  description: string;
  route: string;
  sections: PageSection[];
  codeExamples?: CodeExample[];
  tryItOut?: {
    method: string;
    endpoint: string;
    fields?: { name: string; type: string; required: boolean; description: string }[];
  };
}

export const pages: Record<string, PageContent> = {
  '/': {
    title: 'What is OpenHands?',
    description: 'OpenHands is an AI-powered software development platform that enables autonomous coding agents to write code, run tests, fix bugs, and complete complex engineering tasks.',
    route: '/',
    sections: [
      {
        type: 'callout',
        variant: 'info',
        content: '🏆 OpenHands achieves 77.6% on SWE-bench — the industry-leading benchmark for autonomous software engineering.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'What is OpenHands?',
      },
      {
        type: 'paragraph',
        content: 'OpenHands is an AI-powered software development platform that enables autonomous coding agents to write code, run tests, fix bugs, and complete complex engineering tasks. It provides multiple deployment options to fit your workflow: from a fully hosted cloud service to a self-hosted enterprise solution.',
      },
      {
        type: 'heading',
        level: 2,
        content: '5 Ways to Use OpenHands',
      },
      {
        type: 'table',
        headers: ['Mode', 'Best For', 'Setup Required'],
        rows: [
          ['SDK', 'Building AI agent pipelines programmatically', 'pip install openhands-sdk'],
          ['CLI', 'Terminal-based agent interactions', 'Install from repo or package'],
          ['Local GUI (OSS)', 'Self-hosted open source deployment', 'Docker in 2 commands'],
          ['Cloud', 'Hosted service, no infrastructure', 'Sign in at app.all-hands.dev'],
          ['Enterprise', 'VPC/Kubernetes with SSO, RBAC', 'Kubernetes + Helm chart'],
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Key Capabilities',
      },
      {
        type: 'list',
        items: [
          'Autonomous code writing, editing, and debugging',
          'Full bash/terminal access inside isolated sandboxes',
          'Browser control for web-based tasks',
          'Git integration (GitHub, GitLab, Bitbucket, Azure DevOps)',
          'Multi-LLM support via LiteLLM (GPT-4, Claude, Gemini, and more)',
          'Skills system for reusable agent behaviors',
          'MCP (Model Context Protocol) server integration',
          'Real-time streaming via SSE',
          'Webhook support for automation',
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Community',
      },
      {
        type: 'paragraph',
        content: 'OpenHands has a vibrant open-source community with thousands of contributors. Join us on Slack, GitHub, or Discord to get help, share ideas, and contribute to the project.',
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'Docker Quick Start',
        code: `# Pull and run OpenHands in one command
docker pull ghcr.io/all-handsmachinelearning/openhands:latest

docker run -it --rm \\
  -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-handsmachinelearning/runtime:0.21-nikolaik \\
  -e LOG_ALL_EVENTS=true \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -v ~/.openhands:/home/openhands/.openhands \\
  -p 3000:3000 \\
  ghcr.io/all-handsmachinelearning/openhands:latest

# Then open http://localhost:3000`,
      },
      {
        language: 'python',
        label: 'SDK Quick Start',
        code: `pip install openhands-sdk

from openhands.sdk import LLM, Agent, Conversation

llm = LLM(model="gpt-4o", api_key="your-api-key")
agent = Agent(llm=llm)
conversation = Conversation(agent=agent, workspace="/tmp/my-project")

conversation.send_message("Write a Python script that sorts a list of numbers")
conversation.run()`,
      },
    ],
  },

  '/architecture': {
    title: 'Architecture Overview',
    description: 'How OpenHands is structured — from the agent layer to the runtime sandbox.',
    route: '/architecture',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'System Architecture',
      },
      {
        type: 'paragraph',
        content: 'OpenHands follows a layered architecture where an AI agent interacts with a sandboxed runtime environment through a well-defined event system. Each conversation gets its own isolated Docker sandbox.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Core Components',
      },
      {
        type: 'table',
        headers: ['Component', 'Description', 'Technology'],
        rows: [
          ['Agent', 'Reasoning loop that plans and executes tasks', 'Python / LiteLLM'],
          ['Event System', 'Typed action/observation bus', 'Python dataclasses'],
          ['Runtime Sandbox', 'Isolated execution environment', 'Docker containers'],
          ['App Server', 'REST API + WebSocket backend', 'FastAPI + Python'],
          ['Frontend', 'Single-page application', 'React + TypeScript'],
          ['Database', 'Conversation and event storage', 'SQLite / PostgreSQL'],
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Agent ↔ Runtime Pipeline',
      },
      {
        type: 'steps',
        steps: [
          { title: 'User Input', content: 'User sends a task message via the UI or API' },
          { title: 'Agent Planning', content: 'The LLM-backed agent analyzes the task and determines actions' },
          { title: 'Action Emission', content: 'Agent emits typed action events (CmdRunAction, FileWriteAction, BrowseInteractiveAction, etc.)' },
          { title: 'Sandbox Execution', content: 'Runtime sandbox executes actions in isolated Docker container' },
          { title: 'Observation Return', content: 'Execution results returned as typed observation events' },
          { title: 'Loop Continuation', content: 'Agent processes observations and decides next actions until task is complete' },
        ],
      },
    ],
    codeExamples: [
      {
        language: 'python',
        label: 'Event Types',
        code: `# Action types (agent → runtime)
class CmdRunAction:
    command: str
    
class FileWriteAction:
    path: str
    content: str

class BrowseInteractiveAction:
    browser_actions: str

# Observation types (runtime → agent)  
class CmdOutputObservation:
    content: str
    exit_code: int
    
class FileReadObservation:
    content: str
    path: str`,
      },
    ],
  },

  '/getting-started/cloud': {
    title: 'Quickstart — Cloud',
    description: 'Get started with OpenHands Cloud in minutes. No infrastructure required.',
    route: '/getting-started/cloud',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'Prerequisites',
      },
      {
        type: 'list',
        items: [
          'A GitHub or GitLab account for OAuth',
          'A code repository to work with (optional for first try)',
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Step 1: Sign In',
      },
      {
        type: 'paragraph',
        content: 'Visit app.all-hands.dev and sign in with your GitHub or GitLab account. First-time users will be prompted to accept the Terms of Service and complete a brief onboarding form.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Step 2: Connect a Repository',
      },
      {
        type: 'paragraph',
        content: 'On the home screen, click "Connect a repository" to link your GitHub or GitLab repositories. OpenHands will request the necessary permissions to read, write, and create pull requests.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Step 3: Start Your First Task',
      },
      {
        type: 'paragraph',
        content: 'Enter a task description in the conversation input. For example: "Fix the failing tests in src/utils.ts" or "Add input validation to the user registration form". OpenHands will spin up a sandbox and begin working autonomously.',
      },
      {
        type: 'callout',
        variant: 'success',
        content: '🆓 Free tier includes access using the Minimax model at no cost. Upgrade to use premium models like GPT-4o or Claude.',
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'API Authentication',
        code: `# Get your API key from Settings → API Keys
# Then use it in API calls:
curl -X POST https://app.all-hands.dev/api/v1/conversations \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"task": "Fix the bug in utils.ts"}'`,
      },
    ],
    tryItOut: {
      method: 'POST',
      endpoint: '/api/v1/conversations',
      fields: [
        { name: 'task', type: 'string', required: true, description: 'The task for the agent to complete' },
        { name: 'repository', type: 'string', required: false, description: 'Repository URL to work with' },
        { name: 'branch', type: 'string', required: false, description: 'Branch name (default: main)' },
      ],
    },
  },

  '/getting-started/local-oss': {
    title: 'Quickstart — Local GUI (OSS)',
    description: 'Run OpenHands locally with Docker in under 2 minutes.',
    route: '/getting-started/local-oss',
    sections: [
      {
        type: 'callout',
        variant: 'info',
        content: 'Prerequisites: Docker Desktop (Mac/Windows) or Docker Engine (Linux), 8GB RAM minimum',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Quick Start (2 Commands)',
      },
      {
        type: 'steps',
        steps: [
          {
            title: 'Pull the image',
            content: 'docker pull ghcr.io/all-handsmachinelearning/openhands:latest',
          },
          {
            title: 'Run the container',
            content: 'docker run -it --rm -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-handsmachinelearning/runtime:0.21-nikolaik -e LOG_ALL_EVENTS=true -v /var/run/docker.sock:/var/run/docker.sock -v ~/.openhands:/home/openhands/.openhands -p 3000:3000 --add-host host.docker.internal:host-gateway ghcr.io/all-handsmachinelearning/openhands:latest',
          },
          {
            title: 'Open the UI',
            content: 'Visit http://localhost:3000 in your browser',
          },
          {
            title: 'Configure LLM',
            content: 'Go to Settings (gear icon) and enter your LLM API key',
          },
        ],
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'Docker Run Command',
        code: `docker run -it --rm \\
  -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-handsmachinelearning/runtime:0.21-nikolaik \\
  -e LOG_ALL_EVENTS=true \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -v ~/.openhands:/home/openhands/.openhands \\
  -p 3000:3000 \\
  --add-host host.docker.internal:host-gateway \\
  ghcr.io/all-handsmachinelearning/openhands:latest`,
      },
      {
        language: 'yaml',
        label: 'Docker Compose',
        code: `version: '3'
services:
  openhands:
    image: ghcr.io/all-handsmachinelearning/openhands:latest
    ports:
      - "3000:3000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ~/.openhands:/home/openhands/.openhands
    environment:
      - SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-handsmachinelearning/runtime:0.21-nikolaik
      - LOG_ALL_EVENTS=true
    extra_hosts:
      - "host.docker.internal:host-gateway"`,
      },
    ],
  },

  '/getting-started/sdk': {
    title: 'Quickstart — SDK',
    description: 'Build AI agent pipelines with the OpenHands Python SDK.',
    route: '/getting-started/sdk',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'Installation',
      },
      {
        type: 'paragraph',
        content: 'Install the OpenHands SDK via pip. Python 3.12+ is required.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Your First Agent',
      },
      {
        type: 'paragraph',
        content: 'The SDK provides a clean, composable API for creating AI agents that can write software. Configure an LLM, create an Agent, and run a Conversation.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Core Concepts',
      },
      {
        type: 'table',
        headers: ['Class', 'Purpose'],
        rows: [
          ['LLM', 'Provider-agnostic language model interface'],
          ['Agent', 'Reasoning-action loop'],
          ['Conversation', 'Orchestrates agent execution'],
          ['Tool', 'Defines what agents can do (terminal, file editor, etc.)'],
          ['Skill', 'Reusable prompt/behavior system'],
        ],
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'Install',
        code: `pip install openhands-sdk openhands-tools`,
      },
      {
        language: 'python',
        label: 'Hello World',
        code: `import os
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.terminal import TerminalTool

llm = LLM(
    model=os.getenv("LLM_MODEL", "gpt-4o"),
    api_key=os.getenv("LLM_API_KEY"),
)

agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
    ],
)

conversation = Conversation(agent=agent, workspace="/tmp/my-project")
conversation.send_message("Create a Python calculator with basic arithmetic operations")
conversation.run()
print("Done!")`,
      },
    ],
  },

  '/installation/local-oss/docker': {
    title: 'Docker (Recommended)',
    description: 'The easiest way to run OpenHands locally using Docker.',
    route: '/installation/local-oss/docker',
    sections: [
      {
        type: 'callout',
        variant: 'info',
        content: 'Prerequisites: Docker Desktop 4.x+ (Mac/Windows) or Docker Engine 24.x+ (Linux)',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Environment Variables',
      },
      {
        type: 'table',
        headers: ['Variable', 'Required', 'Description'],
        rows: [
          ['SANDBOX_RUNTIME_CONTAINER_IMAGE', 'Yes', 'Runtime image for the sandbox container'],
          ['LOG_ALL_EVENTS', 'No', 'Enable verbose event logging'],
          ['WORKSPACE_MOUNT_PATH', 'No', 'Host path to mount as workspace'],
          ['SANDBOX_USER_ID', 'No', 'User ID for sandbox (default: current user)'],
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Volume Mounts',
      },
      {
        type: 'list',
        items: [
          '/var/run/docker.sock — Required for spawning sandbox containers',
          '~/.openhands — Persists settings, conversations, and LLM config',
          'Optional: Mount your project directory for direct file access',
        ],
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'Basic Run',
        code: `docker run -it --rm \\
  -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-handsmachinelearning/runtime:0.21-nikolaik \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -v ~/.openhands:/home/openhands/.openhands \\
  -p 3000:3000 \\
  --add-host host.docker.internal:host-gateway \\
  ghcr.io/all-handsmachinelearning/openhands:latest`,
      },
      {
        language: 'bash',
        label: 'With Workspace Mount',
        code: `export WORKSPACE_BASE=$(pwd)

docker run -it --rm \\
  -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-handsmachinelearning/runtime:0.21-nikolaik \\
  -e WORKSPACE_MOUNT_PATH=$WORKSPACE_BASE \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -v ~/.openhands:/home/openhands/.openhands \\
  -v $WORKSPACE_BASE:/opt/workspace_base \\
  -p 3000:3000 \\
  --add-host host.docker.internal:host-gateway \\
  ghcr.io/all-handsmachinelearning/openhands:latest`,
      },
    ],
  },

  '/api/conversations/start': {
    title: 'Start Conversation',
    description: 'Create a new conversation and start an agent task.',
    route: '/api/conversations/start',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'Endpoint',
      },
      {
        type: 'callout',
        variant: 'info',
        content: 'POST /api/v1/conversations',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Request Body',
      },
      {
        type: 'table',
        headers: ['Field', 'Type', 'Required', 'Description'],
        rows: [
          ['task', 'string', 'Yes', 'The task description for the agent'],
          ['repository', 'string', 'No', 'Repository URL to clone and work with'],
          ['branch', 'string', 'No', 'Branch name (default: main/master)'],
          ['selected_repository', 'object', 'No', 'Repository object with full details'],
          ['initial_user_msg', 'string', 'No', 'Alias for task field'],
          ['agent_settings', 'object', 'No', 'Override default agent settings'],
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Response',
      },
      {
        type: 'paragraph',
        content: 'Returns the created conversation object with a unique ID that can be used for subsequent API calls.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Status Codes',
      },
      {
        type: 'table',
        headers: ['Code', 'Description'],
        rows: [
          ['201', 'Conversation created successfully'],
          ['400', 'Invalid request body'],
          ['401', 'Authentication required'],
          ['429', 'Rate limit exceeded'],
        ],
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'cURL',
        code: `curl -X POST https://app.all-hands.dev/api/v1/conversations \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "task": "Fix the failing unit tests in src/auth/login.ts",
    "repository": "https://github.com/myorg/myrepo",
    "branch": "main"
  }'`,
      },
      {
        language: 'python',
        label: 'Python',
        code: `import requests

response = requests.post(
    "https://app.all-hands.dev/api/v1/conversations",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "task": "Fix the failing unit tests in src/auth/login.ts",
        "repository": "https://github.com/myorg/myrepo",
        "branch": "main",
    }
)

conversation = response.json()
print(f"Conversation ID: {conversation['id']}")`,
      },
      {
        language: 'json',
        label: 'Response',
        code: `{
  "id": "conv_01j9x2y3z4a5b6c7d8e9f0g1h",
  "status": "running",
  "created_at": "2025-05-30T10:00:00Z",
  "task": "Fix the failing unit tests in src/auth/login.ts",
  "repository": "https://github.com/myorg/myrepo",
  "branch": "main"
}`,
      },
    ],
    tryItOut: {
      method: 'POST',
      endpoint: '/api/v1/conversations',
      fields: [
        { name: 'task', type: 'string', required: true, description: 'The task for the agent to complete' },
        { name: 'repository', type: 'string', required: false, description: 'Repository URL to work with' },
        { name: 'branch', type: 'string', required: false, description: 'Branch name (default: main)' },
      ],
    },
  },

  '/api/sandboxes/create': {
    title: 'Create Sandbox',
    description: 'Create a new sandbox environment for agent execution.',
    route: '/api/sandboxes/create',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'Endpoint',
      },
      {
        type: 'callout',
        variant: 'info',
        content: 'POST /api/v1/sandboxes',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Request Body',
      },
      {
        type: 'table',
        headers: ['Field', 'Type', 'Required', 'Description'],
        rows: [
          ['image', 'string', 'No', 'Docker image for the sandbox (default: runtime image)'],
          ['workspace_dir', 'string', 'No', 'Initial working directory'],
          ['environment', 'object', 'No', 'Environment variables for the sandbox'],
          ['timeout', 'integer', 'No', 'Sandbox timeout in seconds'],
        ],
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'cURL',
        code: `curl -X POST https://app.all-hands.dev/api/v1/sandboxes \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "environment": {
      "NODE_ENV": "test",
      "DATABASE_URL": "sqlite:///tmp/test.db"
    }
  }'`,
      },
    ],
    tryItOut: {
      method: 'POST',
      endpoint: '/api/v1/sandboxes',
      fields: [
        { name: 'image', type: 'string', required: false, description: 'Docker image for the sandbox' },
        { name: 'timeout', type: 'integer', required: false, description: 'Timeout in seconds' },
      ],
    },
  },

  '/configuration': {
    title: 'Configuration Reference',
    description: 'Complete reference for all OpenHands configuration options.',
    route: '/configuration',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'Configuration Methods',
      },
      {
        type: 'paragraph',
        content: 'OpenHands can be configured through the settings UI, environment variables, or the config.toml file. Environment variables take precedence over config file values.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Key Configuration Options',
      },
      {
        type: 'table',
        headers: ['Option', 'Type', 'Default', 'Description'],
        rows: [
          ['core.workspace_base', 'string', './workspace', 'Base directory for agent workspaces'],
          ['core.debug', 'boolean', 'false', 'Enable debug logging'],
          ['llm.model', 'string', 'gpt-4o', 'Default LLM model to use'],
          ['llm.api_key', 'string', '', 'API key for the LLM provider'],
          ['llm.base_url', 'string', '', 'Custom base URL for LLM API'],
          ['agent.name', 'string', 'CodeActAgent', 'Agent class to use'],
          ['sandbox.runtime_image', 'string', 'runtime:latest', 'Docker image for sandbox'],
          ['sandbox.timeout', 'integer', '120', 'Sandbox execution timeout (seconds)'],
        ],
      },
    ],
    codeExamples: [
      {
        language: 'toml',
        label: 'config.template.toml',
        code: `[core]
workspace_base = "./workspace"
debug = false
save_screenshots = false

[llm]
model = "gpt-4o"
api_key = "your-api-key"
# base_url = "https://api.openai.com/v1"
temperature = 0.0
max_input_tokens = 128000
max_output_tokens = 4096

[agent]
name = "CodeActAgent"
memory_enabled = false
memory_max_threads = 2

[sandbox]
runtime_container_image = "docker.all-hands.dev/all-handsmachinelearning/runtime:0.21-nikolaik"
timeout = 120
user_id = 1000`,
      },
      {
        language: 'bash',
        label: 'Environment Variables',
        code: `# Core
export WORKSPACE_MOUNT_PATH=/path/to/workspace
export DEBUG=false

# LLM
export LLM_MODEL=gpt-4o
export LLM_API_KEY=your-api-key

# Sandbox
export SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-handsmachinelearning/runtime:0.21-nikolaik
export SANDBOX_TIMEOUT=120

# Server
export FRONTEND_PORT=3000
export BACKEND_HOST=0.0.0.0`,
      },
    ],
  },

  '/integrations/github': {
    title: 'GitHub Integration',
    description: 'Connect OpenHands with GitHub for seamless repository access and PR creation.',
    route: '/integrations/github',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'GitHub Integration Overview',
      },
      {
        type: 'paragraph',
        content: 'OpenHands integrates with GitHub to allow agents to clone repositories, create branches, commit code, and open pull requests automatically. The integration uses OAuth apps for secure access.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Required Permissions',
      },
      {
        type: 'table',
        headers: ['Permission', 'Scope', 'Why Needed'],
        rows: [
          ['Contents', 'read/write', 'Clone repos, read/write files'],
          ['Pull Requests', 'read/write', 'Create and update PRs'],
          ['Issues', 'read', 'Read issue context for task suggestions'],
          ['Metadata', 'read', 'Repository metadata'],
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Setup Steps',
      },
      {
        type: 'steps',
        steps: [
          { title: 'Open Settings', content: 'Go to Settings → Integrations in the OpenHands UI' },
          { title: 'Click Connect GitHub', content: 'Click the Connect GitHub button' },
          { title: 'OAuth Authorization', content: 'Authorize the OpenHands GitHub App in the OAuth flow' },
          { title: 'Select Repositories', content: 'Choose which repositories to grant access to' },
          { title: 'Verify Connection', content: 'Your repositories will appear in the repo selector on the home screen' },
        ],
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'Search Repositories',
        code: `# List accessible repositories
curl -X GET "https://app.all-hands.dev/api/v1/git/repositories/search?query=myrepo" \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
      },
      {
        language: 'json',
        label: 'Response',
        code: `{
  "repositories": [
    {
      "id": "12345",
      "full_name": "myorg/myrepo",
      "html_url": "https://github.com/myorg/myrepo",
      "default_branch": "main",
      "private": false
    }
  ]
}`,
      },
    ],
  },

  '/features/conversations': {
    title: 'Conversations',
    description: 'Understanding how OpenHands conversations work — lifecycle, states, and interaction patterns.',
    route: '/features/conversations',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'What is a Conversation?',
      },
      {
        type: 'paragraph',
        content: 'A conversation is the primary unit of work in OpenHands. Each conversation represents a task given to an agent, running in its own isolated sandbox environment. Conversations persist their state and can be resumed, shared, or exported.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Conversation Tabs',
      },
      {
        type: 'table',
        headers: ['Tab', 'Description'],
        rows: [
          ['Chat', 'Main conversation view with agent messages and user input'],
          ['Changes', 'Diff viewer showing file modifications made by the agent'],
          ['Planner', 'Task planning view with high-level decomposition'],
          ['Task List', 'Checklist of subtasks and their completion status'],
          ['Terminal', 'Embedded terminal showing agent bash commands'],
          ['Browser', 'Agent-controlled browser for web-based tasks'],
          ['VSCode', 'Open workspace in VS Code via tunnel'],
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Conversation Lifecycle',
      },
      {
        type: 'steps',
        steps: [
          { title: 'Created', content: 'User sends a task. Sandbox is provisioned.' },
          { title: 'Loading', content: 'Agent and runtime are initializing.' },
          { title: 'Running', content: 'Agent is actively working on the task.' },
          { title: 'Awaiting Input', content: 'Agent needs clarification from the user.' },
          { title: 'Finished', content: 'Task completed. Agent has stopped.' },
          { title: 'Error', content: 'An unrecoverable error occurred.' },
        ],
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'Send a Message',
        code: `# Send a follow-up message to an existing conversation
curl -X POST https://app.all-hands.dev/api/v1/conversations/CONV_ID/messages \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"content": "Also add unit tests for the new function"}'`,
      },
    ],
    tryItOut: {
      method: 'POST',
      endpoint: '/api/v1/conversations/{id}/messages',
      fields: [
        { name: 'content', type: 'string', required: true, description: 'Message to send to the agent' },
      ],
    },
  },

  '/enterprise/architecture': {
    title: 'Enterprise Architecture',
    description: 'How OpenHands Enterprise is deployed in VPC and Kubernetes environments.',
    route: '/enterprise/architecture',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'Deployment Overview',
      },
      {
        type: 'paragraph',
        content: 'OpenHands Enterprise is designed for organizations that require data sovereignty, advanced security controls, and scalability. It runs entirely within your VPC on Kubernetes.',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Components',
      },
      {
        type: 'table',
        headers: ['Component', 'Description', 'Scaling'],
        rows: [
          ['App Server', 'FastAPI backend, REST + WebSocket', 'Horizontal (stateless)'],
          ['Frontend', 'React SPA, served via nginx', 'Horizontal (stateless)'],
          ['Agent Runtime', 'Docker-in-Docker or node pools', 'Per-conversation isolation'],
          ['Database', 'PostgreSQL with Alembic migrations', 'Vertical / Read replicas'],
          ['Auth', 'Keycloak SSO, GitHub/SAML/OIDC', 'High availability'],
          ['Storage', 'S3-compatible or local filesystem', 'Based on provider'],
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Security Model',
      },
      {
        type: 'list',
        items: [
          'Each conversation runs in an isolated Kubernetes pod or Docker container',
          'Network policies restrict inter-pod communication',
          'Secrets managed via Kubernetes Secrets or Vault integration',
          'RBAC controls access at org, team, and user levels',
          'All LLM calls made from within VPC (no data leaves your network)',
          'Audit logging for all user actions and agent executions',
        ],
      },
    ],
    codeExamples: [
      {
        language: 'yaml',
        label: 'Helm Values (minimal)',
        code: `# values.yaml
replicaCount: 2

image:
  repository: ghcr.io/all-handsmachinelearning/openhands-enterprise
  tag: "0.21.0"

database:
  host: postgres.internal
  port: 5432
  name: openhands
  existingSecret: openhands-db-secret

auth:
  keycloakUrl: https://auth.company.com
  realm: openhands

storage:
  type: s3
  bucket: openhands-workspaces
  region: us-east-1`,
      },
    ],
  },

  '/contributing': {
    title: 'Contributing to OpenHands',
    description: 'How to contribute code, documentation, and ideas to the OpenHands project.',
    route: '/contributing',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: 'Welcome, Contributor!',
      },
      {
        type: 'paragraph',
        content: 'OpenHands is an open-source project and welcomes contributions from everyone. Whether you\'re fixing a bug, adding a feature, improving documentation, or creating evaluation benchmarks — we appreciate your help!',
      },
      {
        type: 'heading',
        level: 2,
        content: 'Ways to Contribute',
      },
      {
        type: 'list',
        items: [
          '🐛 Report bugs by opening GitHub issues',
          '✨ Request features via discussions',
          '📝 Improve documentation',
          '🔧 Fix bugs and submit PRs',
          '🧪 Add evaluation benchmarks',
          '🌍 Help with translations',
          '💬 Answer questions on Slack and Discord',
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: 'Development Setup',
      },
      {
        type: 'callout',
        variant: 'info',
        content: 'See the Development Setup page for OS-specific instructions for macOS, Linux, and Windows.',
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'Quick Dev Setup',
        code: `# Clone the repo
git clone https://github.com/All-Hands-AI/OpenHands.git
cd OpenHands

# Install dependencies
make install-python-dependencies

# Build and run
make build
make run

# Run tests
pytest ./tests/unit/test_*.py`,
      },
    ],
  },

  '/changelog': {
    title: 'Release Notes',
    description: 'What\'s new in each OpenHands release.',
    route: '/changelog',
    sections: [
      {
        type: 'heading',
        level: 2,
        content: '0.21.0 — May 2025',
      },
      {
        type: 'list',
        items: [
          '✨ New: Skills settings page for managing agent skills',
          '✨ New: MCP (Model Context Protocol) server integration',
          '✨ New: Verification settings for output validation',
          '🐛 Fix: Improved sandbox cleanup on conversation end',
          '🐛 Fix: WebSocket reconnection stability',
          '📈 Performance: Faster conversation loading with pagination',
          '🔐 Security: Enhanced secret masking in terminal output',
        ],
      },
      {
        type: 'heading',
        level: 2,
        content: '0.20.0 — April 2025',
      },
      {
        type: 'list',
        items: [
          '✨ New: Organization management with RBAC',
          '✨ New: Shared conversation URLs (/shared/conversations/:id)',
          '✨ New: Webhook support for conversation events',
          '✨ New: Azure DevOps integration',
          '🐛 Fix: Multiple browser control improvements',
          '📈 Performance: Agent context condensation',
        ],
      },
    ],
    codeExamples: [
      {
        language: 'bash',
        label: 'Upgrade Docker Image',
        code: `# Pull the latest version
docker pull ghcr.io/all-handsmachinelearning/openhands:latest

# Or pin to specific version
docker pull ghcr.io/all-handsmachinelearning/openhands:0.21.0`,
      },
    ],
  },
};

// Generate stub pages for routes not explicitly defined
export function getPage(route: string): PageContent {
  if (pages[route]) return pages[route];

  // Generate a stub page
  const title = route
    .split('/')
    .pop()!
    .replace(/-/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase()) || 'Documentation';

  return {
    title,
    description: `Documentation for ${title}`,
    route,
    sections: [
      {
        type: 'callout',
        variant: 'info',
        content: '📖 This page is part of the OpenHands documentation. Full content coming soon.',
      },
      {
        type: 'heading',
        level: 2,
        content: title,
      },
      {
        type: 'paragraph',
        content: `This section covers ${title.toLowerCase()} in OpenHands. Navigate using the left sidebar to explore related topics.`,
      },
    ],
  };
}
