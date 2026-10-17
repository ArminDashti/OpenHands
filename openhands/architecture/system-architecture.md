# System Architecture Overview

OpenHands uses a multi-tier architecture with these main components:

```mermaid
flowchart TB
    subgraph AppServer["OpenHands App Server (Single Instance)"]
        API["REST API<br/>(FastAPI)"]
        Auth["Authentication"]
        ConvMgr["Conversation<br/>Manager"]
        SandboxSvc["Sandbox<br/>Service"]
    end

    subgraph RuntimeAPI["Runtime API (Separate Service)"]
        RuntimeMgr["Runtime<br/>Manager"]
        WarmPool["Warm Runtime<br/>Pool"]
    end

    subgraph Sandbox["Sandbox (Docker/K8s Container)"]
        AS["Agent Server<br/>(openhands-agent-server)"]
        AES["Action Execution<br/>Server"]
        Browser["Browser<br/>Environment"]
        FS["File System"]
    end

    User["User"] -->|"1. HTTP/REST"| API
    API --> Auth
    Auth --> ConvMgr
    ConvMgr --> SandboxSvc

    SandboxSvc -->|"2. POST /start"| RuntimeMgr
    RuntimeMgr -->|"Check pool"| WarmPool
    WarmPool -->|"Warm runtime<br/>available?"| RuntimeMgr
    RuntimeMgr -->|"3. Provision or<br/>assign runtime"| Sandbox

    User -.->|"4. WebSocket<br/>(Direct)"| AS

    AS -->|"HTTP"| AES
    AES --> Browser
    AES --> FS
```

### Component Responsibilities

| Component | Location | Instances | Purpose |
|-----------|----------|-----------|---------|
| **App Server** | Host | 1 per deployment | REST API, auth, conversation management |
| **Sandbox Service** | Inside App Server | 1 | Manages sandbox lifecycle, calls Runtime API |
| **Runtime API** | Separate service | 1 per deployment | Provisions runtimes, manages warm pool |
| **Agent Server** | Inside sandbox | 1 per sandbox | AI agent loop, LLM calls, state management |
| **Action Execution Server** | Inside sandbox | 1 per sandbox | Execute bash, file ops, browser actions |

### Runtime API Endpoints

The Runtime API manages the actual container/pod lifecycle:

| Endpoint | Purpose |
|----------|---------|
| `POST /start` | Start a new runtime (or assign from warm pool) |
| `POST /stop` | Stop and clean up a runtime |
| `POST /pause` | Pause a running runtime |
| `POST /resume` | Resume a paused runtime |
| `GET /sessions/{id}` | Get runtime status |
| `GET /list` | List all active runtimes |
