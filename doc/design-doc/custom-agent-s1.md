# Custom Agent Packages with Custom Runtime Images (Scenario 1)

## 1. Introduction

### 1.1 Problem Statement

OpenHands currently supports agent customization through the software-agent-sdk, but users who need custom system dependencies, specialized tools, or non-Python runtime environments cannot easily deploy their agents. The current V1 architecture uses a fixed agent server image (`ghcr.io/openhands/agent-server:5f62cee-python`) that may not contain the required dependencies for specialized agents.

Users building agents that require:
- Custom system packages (e.g., specialized compilers, databases, ML frameworks)
- Non-Python tools and runtimes (e.g., Node.js, Go, Rust toolchains)
- Custom Docker base images with specific OS configurations
- Proprietary or licensed software installations

Currently have no supported path to deploy their agents to OpenHands Enterprise.

### 1.2 Proposed Solution

We propose extending the existing **Sandbox Specification System** to support custom agent runtime images with proper permissions and security controls. This approach builds directly on OpenHands' current sandbox infrastructure rather than creating parallel systems.

Users will be able to:
1. Create custom Docker images containing their agent code and dependencies
2. Register these images as enhanced sandbox specifications with rich metadata
3. Deploy conversations using their custom sandbox specs (with proper permissions)
4. Maintain full compatibility with existing sandbox management and API infrastructure

The solution extends the current `SandboxSpecService` with:
- **Permission-based access control** to limit custom specs to authorized users
- **Enhanced sandbox specifications** that include agent-specific metadata and requirements
- **Secure image management** with validation and approval workflows
- **Integrated deployment** through existing conversation creation APIs

**Trade-offs**: This approach requires users to build and maintain Docker images, increasing complexity compared to simple Python package deployment. However, it provides the necessary isolation and dependency management for complex agent requirements while leveraging proven sandbox infrastructure.

## 2. User Interface

### 2.1 Custom Agent Image Creation

Users create a custom agent image by extending the base agent server image:

```dockerfile
# Dockerfile for custom agent
FROM ghcr.io/openhands/agent-server:5f62cee-python

# Install custom system dependencies
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    golang-go \
    && rm -rf /var/lib/apt/lists/*

# Install custom Python packages
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# Copy custom agent code
COPY my_custom_agent/ /app/my_custom_agent/
COPY agent_config.json /app/config/

# Set custom agent as default
ENV CUSTOM_AGENT_MODULE=my_custom_agent
ENV CUSTOM_AGENT_CLASS=MySpecializedAgent
```

### 2.2 Enhanced Sandbox Spec Registration

Users register their custom agent image as an enhanced sandbox specification:

```yaml
# enhanced-sandbox-spec.yaml
apiVersion: openhands.ai/v1
kind: SandboxSpec
metadata:
  name: specialized-ml-agent
  version: "1.0.0"
  owner: user@company.com
  permissions:
    users: ["user@company.com", "team-lead@company.com"]
    groups: ["ml-team", "data-science"]
spec:
  image: "myregistry/specialized-ml-agent:v1.0.0"
  description: "ML agent with TensorFlow and custom data processing tools"
  # Agent-specific metadata
  agent:
    capabilities:
      - machine_learning
      - data_analysis
      - custom_visualization
    type: "custom"
    module: "agents.specialized_ml_agent"
    class: "SpecializedMLAgent"
  requirements:
    memory: "4Gi"
    cpu: "2"
  environment:
    TENSORFLOW_VERSION: "2.15.0"
    CUSTOM_MODEL_PATH: "/app/models"
    # Agent server configuration
    CUSTOM_AGENT_MODULE: "agents.specialized_ml_agent"
    CUSTOM_AGENT_CLASS: "SpecializedMLAgent"
  ports:
    - name: agent-server
      port: 8000
    - name: tensorboard
      port: 6006
```

### 2.3 Conversation Creation with Custom Sandbox Spec

Users create conversations using their custom sandbox specs through the existing API:

```bash
# Create conversation with custom sandbox spec
curl -X POST "https://api.openhands.ai/api/conversations" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sandbox_spec_id": "specialized-ml-agent:v1.0.0",
    "initial_message": "Analyze this dataset and create a predictive model",
    "workspace": {
      "type": "local",
      "working_dir": "/workspace/ml-project"
    }
  }'
```

### 2.4 Image Management Workflows

#### 2.4.1 Pre-built Image Approach

For organizations that want to manage custom agent images centrally:

```bash
# Admin registers pre-built image as sandbox spec
curl -X POST "https://api.openhands.ai/api/sandbox-specs" \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "company-ml-agent",
    "version": "1.0.0",
    "image": "company-registry/ml-agent:v1.0.0",
    "permissions": {
      "groups": ["ml-team", "data-science"]
    },
    "agent": {
      "type": "custom",
      "capabilities": ["machine_learning", "data_analysis"]
    }
  }'
```

#### 2.4.2 User Upload Approach

For users who want to upload their own custom images:

```bash
# User uploads custom image (with security validation)
curl -X POST "https://api.openhands.ai/api/sandbox-specs/upload" \
  -H "Authorization: Bearer $API_KEY" \
  -F "dockerfile=@Dockerfile" \
  -F "context=@agent-context.tar.gz" \
  -F "spec=@sandbox-spec.yaml"
```

## 3. Other Context

### 3.1 Current Sandbox Specification System

OpenHands V1 uses a sandbox specification system to manage container deployments:

- **Single Default Spec**: Currently only one sandbox spec exists, shared by all users
- **SandboxSpecService**: Manages sandbox specifications and container creation
- **SandboxSpecInfo**: Contains image, environment, and resource configuration
- **No Permissions**: Current system lacks user-based access control

The existing system provides the foundation but needs enhancement for custom agents:
- **Permission Layer**: Required to control access to custom specs
- **Rich Metadata**: Need agent-specific information beyond basic container config
- **Image Management**: Need secure workflows for custom image registration

### 3.2 Enhanced Sandbox Specification Architecture

Our proposal extends the existing system with:

#### 3.2.1 Permission-Based Access Control
- **User Permissions**: Individual user access to specific sandbox specs
- **Group Permissions**: Team-based access control for organizational specs
- **Owner Management**: Spec ownership and delegation capabilities
- **Admin Override**: Administrative access for spec management

#### 3.2.2 Agent-Specific Metadata
- **Agent Configuration**: Module, class, and capability information
- **Resource Requirements**: Memory, CPU, and storage specifications
- **Environment Variables**: Agent-specific configuration and secrets
- **Port Mappings**: Additional ports for agent services (e.g., TensorBoard)

#### 3.2.3 Image Management Integration
- **Registry Support**: Integration with Docker registries for image storage
- **Security Validation**: Image scanning and approval workflows
- **Version Management**: Support for multiple versions of custom specs
- **Build Integration**: Optional image building from Dockerfile uploads

### 3.3 Existing Container Orchestration Integration

The enhanced system leverages existing OpenHands infrastructure:

- **Sandbox Service**: Extended to support permission checks and enhanced specs
- **Container Management**: Same lifecycle management with additional metadata
- **Network Isolation**: Maintains existing security boundaries
- **Resource Enforcement**: Enhanced with custom resource requirements
- **Health Monitoring**: Extended to track custom agent-specific metrics

## 4. Technical Design

### 4.1 Enhanced Sandbox Specification Model

#### 4.1.1 Extended SandboxSpecInfo Structure

The existing `SandboxSpecInfo` model is enhanced to support custom agents:

```python
# openhands/app_server/sandbox/sandbox_spec_models.py (enhanced)
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class AgentMetadata(BaseModel):
    """Agent-specific metadata for custom agents."""
    type: str = Field(default="default", description="Agent type (default|custom)")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    module: Optional[str] = Field(description="Python module containing agent class")
    class_name: Optional[str] = Field(description="Agent class name")

class PermissionSpec(BaseModel):
    """Permission specification for sandbox spec access."""
    users: List[str] = Field(default_factory=list, description="Authorized user emails")
    groups: List[str] = Field(default_factory=list, description="Authorized group names")
    owner: Optional[str] = Field(description="Spec owner")

class EnhancedSandboxSpecInfo(BaseModel):
    """Enhanced sandbox specification with agent metadata and permissions."""
    
    # Existing fields from SandboxSpecInfo
    id: str = Field(description="Docker image identifier")
    command: List[str] = Field(default_factory=lambda: ['--port', '8000'])
    initial_env: Dict[str, str] = Field(default_factory=dict)
    working_dir: str = Field(default="/workspace/project")
    
    # Enhanced fields
    name: str = Field(description="Human-readable spec name")
    version: str = Field(description="Spec version")
    description: Optional[str] = Field(description="Spec description")
    
    # Agent-specific metadata
    agent: AgentMetadata = Field(default_factory=AgentMetadata)
    
    # Permission and access control
    permissions: PermissionSpec = Field(default_factory=PermissionSpec)
    
    # Resource requirements
    memory_limit: Optional[str] = Field(description="Memory limit (e.g., '4Gi')")
    cpu_limit: Optional[str] = Field(description="CPU limit (e.g., '2')")
    
    # Additional ports for custom services
    ports: List[Dict[str, any]] = Field(
        default_factory=lambda: [{"name": "agent-server", "port": 8000}]
    )
```

#### 4.1.2 Custom Agent Image Structure

Custom agent images extend the base agent server with this structure:

```
/app/
├── config/
│   ├── agent_config.json          # Agent configuration
│   └── tool_registry.json         # Custom tool definitions (optional)
├── agents/
│   └── custom_agent.py            # Agent implementation
├── tools/                         # Custom tools (optional)
│   ├── __init__.py
│   └── custom_tools.py
└── startup/
    └── init_agent.py              # Agent initialization script
```

### 4.2 Agent Implementation Interface

#### 4.2.1 Custom Agent Base Class

```python
# agents/custom_agent.py
from openhands.sdk.agent.base import AgentBase
from openhands.sdk.llm import LLM
from openhands.sdk.tool import Tool
from typing import List, Dict, Any

class SpecializedMLAgent(AgentBase):
    """Custom ML agent with TensorFlow capabilities."""

    def __init__(
        self,
        llm: LLM,
        tools: List[Tool],
        config: Dict[str, Any] = None
    ):
        super().__init__(llm=llm, tools=tools)
        self.config = config or {}
        self.model_cache = self.config.get('MODEL_CACHE_DIR', '/app/models')

    async def initialize(self) -> None:
        """Initialize custom agent resources."""
        # Load pre-trained models
        await self._load_models()

        # Initialize custom tools
        await self._setup_custom_tools()

    async def _load_models(self) -> None:
        """Load TensorFlow models from cache."""
        import tensorflow as tf
        # Custom model loading logic
        pass

    async def _setup_custom_tools(self) -> None:
        """Initialize custom tools with agent context."""
        # Custom tool setup logic
        pass
```

#### 4.2.2 Custom Tool Implementation

```python
# tools/custom_tools.py
from openhands.sdk.tool import Tool, ToolExecutor, register_tool
from openhands.sdk import Action, Observation
from pydantic import Field
import tensorflow as tf

class TensorFlowAnalysisAction(Action):
    dataset_path: str = Field(description="Path to dataset file")
    model_type: str = Field(description="Type of ML model to create")
    target_column: str = Field(description="Target column for prediction")

class TensorFlowAnalysisObservation(Observation):
    model_accuracy: float = Field(description="Model accuracy score")
    feature_importance: Dict[str, float] = Field(description="Feature importance scores")
    model_path: str = Field(description="Path to saved model")

class TensorFlowToolExecutor(ToolExecutor[TensorFlowAnalysisAction, TensorFlowAnalysisObservation]):
    def __call__(self, action: TensorFlowAnalysisAction, conversation=None) -> TensorFlowAnalysisObservation:
        # Custom TensorFlow analysis logic
        model = self._create_model(action.dataset_path, action.model_type, action.target_column)
        accuracy = self._evaluate_model(model)
        importance = self._get_feature_importance(model)
        model_path = self._save_model(model)

        return TensorFlowAnalysisObservation(
            model_accuracy=accuracy,
            feature_importance=importance,
            model_path=model_path
        )

# Register the custom tool
register_tool(
    Tool(
        name="TensorFlowTool",
        executor=TensorFlowToolExecutor(),
        definition=ToolDefinition(
            name="tensorflow_analysis",
            description="Perform machine learning analysis using TensorFlow",
            parameters=TensorFlowAnalysisAction.model_json_schema()
        )
    )
)
```

### 4.3 Runtime Integration

#### 4.3.1 Custom Agent Loader

```python
# startup/init_agent.py
import json
import importlib
from pathlib import Path
from openhands.sdk.agent.base import AgentBase
from openhands.sdk.llm import LLM
from openhands.sdk.tool import Tool, resolve_tool

class CustomAgentLoader:
    """Loads custom agents from configuration."""

    def __init__(self, config_path: str = "/app/config/agent_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load agent configuration from JSON file."""
        with open(self.config_path) as f:
            return json.load(f)

    def create_agent(self, llm: LLM) -> AgentBase:
        """Create custom agent instance."""
        agent_config = self.config["agent"]

        # Import custom agent class
        module = importlib.import_module(agent_config["module"])
        agent_class = getattr(module, agent_config["class"])

        # Load custom tools
        tools = self._load_tools()

        # Create agent instance
        agent = agent_class(
            llm=llm,
            tools=tools,
            config=self.config.get("environment", {})
        )

        return agent

    def _load_tools(self) -> List[Tool]:
        """Load and resolve custom tools."""
        tools = []
        for tool_config in self.config.get("tools", []):
            if "module" in tool_config:
                # Import custom tool module to register it
                importlib.import_module(tool_config["module"])

            tool = resolve_tool(tool_config["name"])
            tools.append(tool)

        return tools
```

#### 4.3.2 Agent Server Startup Integration

```python
# Modified agent server startup in software-agent-sdk
import os
from openhands.agent_server.api import app
from openhands.agent_server.conversation_service import ConversationService
from startup.init_agent import CustomAgentLoader

@app.on_event("startup")
async def startup_event():
    """Initialize custom agent during server startup."""

    # Check for custom agent configuration
    custom_agent_module = os.getenv('CUSTOM_AGENT_MODULE')
    custom_agent_class = os.getenv('CUSTOM_AGENT_CLASS')

    if custom_agent_module and custom_agent_class:
        # Load custom agent
        loader = CustomAgentLoader()
        app.state.agent_factory = loader.create_agent
        print(f"Loaded custom agent: {custom_agent_class}")
    else:
        # Use default agent
        from openhands.sdk.agent import Agent
        app.state.agent_factory = lambda llm: Agent(llm=llm, tools=get_default_tools())
        print("Using default OpenHands agent")
```

### 4.4 Enhanced Sandbox Service Integration

#### 4.4.1 Permission-Aware Sandbox Service

```python
# openhands/app_server/sandbox/enhanced_sandbox_spec_service.py
from openhands.app_server.sandbox.sandbox_spec_service import SandboxSpecService
from openhands.app_server.sandbox.sandbox_spec_models import SandboxSpecInfo, EnhancedSandboxSpecInfo
from typing import Dict, List, Optional

class EnhancedSandboxSpecService(SandboxSpecService):
    """Enhanced sandbox service with permissions and custom agent support."""

    def __init__(self, spec_registry: Dict[str, EnhancedSandboxSpecInfo]):
        super().__init__()
        self.spec_registry = spec_registry

    def get_available_sandbox_specs(self, user_email: str, user_groups: List[str]) -> List[str]:
        """Get sandbox specs available to the user based on permissions."""
        available_specs = []
        
        for spec_key, spec in self.spec_registry.items():
            if self._has_permission(spec, user_email, user_groups):
                available_specs.append(spec_key)
        
        return available_specs

    def get_sandbox_spec_by_id(
        self, 
        spec_id: str, 
        user_email: str, 
        user_groups: List[str]
    ) -> SandboxSpecInfo:
        """Get sandbox spec by ID with permission check."""
        
        if spec_id not in self.spec_registry:
            # Fall back to default specs for backward compatibility
            return super().get_default_sandbox_specs()[0]
        
        enhanced_spec = self.spec_registry[spec_id]
        
        # Check permissions
        if not self._has_permission(enhanced_spec, user_email, user_groups):
            raise PermissionError(f"User {user_email} does not have access to spec {spec_id}")
        
        # Convert to SandboxSpecInfo for existing infrastructure
        return self._convert_to_sandbox_spec_info(enhanced_spec)

    def _has_permission(
        self, 
        spec: EnhancedSandboxSpecInfo, 
        user_email: str, 
        user_groups: List[str]
    ) -> bool:
        """Check if user has permission to use the sandbox spec."""
        
        # Owner always has access
        if spec.permissions.owner == user_email:
            return True
        
        # Check user permissions
        if user_email in spec.permissions.users:
            return True
        
        # Check group permissions
        for group in user_groups:
            if group in spec.permissions.groups:
                return True
        
        return False

    def _convert_to_sandbox_spec_info(self, enhanced_spec: EnhancedSandboxSpecInfo) -> SandboxSpecInfo:
        """Convert enhanced spec to standard SandboxSpecInfo."""
        
        # Build environment variables including agent configuration
        env_vars = {
            'OPENVSCODE_SERVER_ROOT': '/openhands/.openvscode-server',
            'OH_ENABLE_VNC': '0',
            'LOG_JSON': 'true',
            'OH_CONVERSATIONS_PATH': '/workspace/conversations',
            'OH_BASH_EVENTS_DIR': '/workspace/bash_events',
            'PYTHONUNBUFFERED': '1',
            'ENV_LOG_LEVEL': '20',
            **enhanced_spec.initial_env
        }
        
        # Add custom agent configuration if specified
        if enhanced_spec.agent.type == "custom":
            env_vars.update({
                'CUSTOM_AGENT_MODULE': enhanced_spec.agent.module,
                'CUSTOM_AGENT_CLASS': enhanced_spec.agent.class_name,
            })

        return SandboxSpecInfo(
            id=enhanced_spec.id,
            command=enhanced_spec.command,
            initial_env=env_vars,
            working_dir=enhanced_spec.working_dir,
        )

    def register_sandbox_spec(
        self, 
        spec: EnhancedSandboxSpecInfo,
        admin_user: str
    ) -> str:
        """Register a new sandbox spec (admin only)."""
        
        spec_key = f"{spec.name}:{spec.version}"
        
        # Validate spec
        self._validate_sandbox_spec(spec)
        
        # Store in registry
        self.spec_registry[spec_key] = spec
        
        return spec_key

    def _validate_sandbox_spec(self, spec: EnhancedSandboxSpecInfo) -> None:
        """Validate sandbox spec for security and correctness."""
        
        # Image validation
        if not spec.id or not spec.id.strip():
            raise ValueError("Image ID cannot be empty")
        
        # Permission validation
        if not spec.permissions.owner:
            raise ValueError("Sandbox spec must have an owner")
        
        # Agent validation for custom agents
        if spec.agent.type == "custom":
            if not spec.agent.module or not spec.agent.class_name:
                raise ValueError("Custom agents must specify module and class_name")
```

### 4.5 Enhanced API Integration

#### 4.5.1 Enhanced Conversation Creation

```python
# openhands/server/routes/conversation_routes.py (enhanced)
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID

from openhands.app_server.sandbox.enhanced_sandbox_spec_service import EnhancedSandboxSpecService
from openhands.server.session.agent_session import AgentSession
from openhands.server.auth import get_current_user, get_user_groups

# Enhanced conversation creation request
class CreateConversationRequest(BaseModel):
    initial_message: str
    workspace_config: Optional[Dict[str, Any]] = None
    # New field for custom sandbox spec
    sandbox_spec_id: Optional[str] = None

@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    current_user: str = Depends(get_current_user),
    user_groups: List[str] = Depends(get_user_groups),
    sandbox_service: EnhancedSandboxSpecService = Depends(get_enhanced_sandbox_service)
) -> ConversationResponse:
    """Create conversation with optional custom sandbox spec."""

    try:
        if request.sandbox_spec_id:
            # Use custom sandbox spec with permission check
            sandbox_spec = sandbox_service.get_sandbox_spec_by_id(
                request.sandbox_spec_id, 
                current_user, 
                user_groups
            )
        else:
            # Use default sandbox spec
            sandbox_spec = sandbox_service.get_default_sandbox_specs()[0]

        # Create sandbox and conversation
        sandbox = await sandbox_service.create_sandbox(sandbox_spec)
        await wait_for_agent_server_ready(sandbox)

        conversation = await create_conversation_with_sandbox(
            sandbox=sandbox,
            initial_message=request.initial_message,
            workspace_config=request.workspace_config
        )

        return ConversationResponse(
            conversation_id=conversation.id,
            status="created",
            sandbox_spec_id=request.sandbox_spec_id or "default"
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

#### 4.5.2 Sandbox Spec Management API

```python
# openhands/server/routes/sandbox_spec_routes.py (new)
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import yaml

from openhands.app_server.sandbox.enhanced_sandbox_spec_service import EnhancedSandboxSpecService
from openhands.app_server.sandbox.sandbox_spec_models import EnhancedSandboxSpecInfo
from openhands.server.auth import get_current_user, get_user_groups, require_admin

router = APIRouter(prefix="/api/sandbox-specs", tags=["Sandbox Specs"])

@router.get("/")
async def list_available_sandbox_specs(
    current_user: str = Depends(get_current_user),
    user_groups: List[str] = Depends(get_user_groups),
    sandbox_service: EnhancedSandboxSpecService = Depends(get_enhanced_sandbox_service)
) -> List[str]:
    """List sandbox specs available to the current user."""
    
    return sandbox_service.get_available_sandbox_specs(current_user, user_groups)

@router.post("/")
async def register_sandbox_spec(
    spec_data: EnhancedSandboxSpecInfo,
    current_user: str = Depends(require_admin),
    sandbox_service: EnhancedSandboxSpecService = Depends(get_enhanced_sandbox_service)
) -> Dict[str, str]:
    """Register a new sandbox spec (admin only)."""
    
    try:
        spec_key = sandbox_service.register_sandbox_spec(spec_data, current_user)
        return {"spec_id": spec_key, "status": "registered"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload")
async def upload_custom_image(
    dockerfile: UploadFile = File(...),
    context: UploadFile = File(...),
    spec: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    sandbox_service: EnhancedSandboxSpecService = Depends(get_enhanced_sandbox_service)
) -> Dict[str, str]:
    """Upload custom image with Dockerfile and context (with security validation)."""
    
    try:
        # Parse spec file
        spec_content = await spec.read()
        spec_data = yaml.safe_load(spec_content)
        
        # Validate user has permission to create specs
        if not _can_user_create_specs(current_user):
            raise HTTPException(status_code=403, detail="User not authorized to create custom specs")
        
        # Security validation of Dockerfile
        dockerfile_content = await dockerfile.read()
        _validate_dockerfile_security(dockerfile_content)
        
        # Build image (implementation depends on build system)
        image_id = await _build_custom_image(dockerfile_content, context, current_user)
        
        # Create enhanced spec
        enhanced_spec = EnhancedSandboxSpecInfo(**spec_data)
        enhanced_spec.id = image_id
        enhanced_spec.permissions.owner = current_user
        
        # Register the spec
        spec_key = sandbox_service.register_sandbox_spec(enhanced_spec, current_user)
        
        return {"spec_id": spec_key, "image_id": image_id, "status": "uploaded"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")
```

## 5. Implementation Plan

All implementation must pass existing lints and tests. New functionality requires comprehensive test coverage including unit tests, integration tests, and end-to-end scenarios.

### 5.1 Enhanced Sandbox Models and Permissions (M1)

#### 5.1.1 Enhanced Sandbox Specification Models

* `openhands/app_server/sandbox/sandbox_spec_models.py` (enhanced)
* `tests/unit/app_server/sandbox/test_enhanced_sandbox_spec_models.py`

Extend existing `SandboxSpecInfo` with `EnhancedSandboxSpecInfo` including agent metadata, permissions, and resource requirements. This is the **core requirement** identified by the engineer.

#### 5.1.2 Permission System Foundation

* `openhands/server/auth/permissions.py`
* `tests/unit/server/auth/test_permissions.py`

Implement user and group-based permission system for sandbox spec access control. This addresses the **security concerns** from V0 mentioned by the engineer.

**Demo**: Create enhanced sandbox specs with permission restrictions and verify access control works correctly.

### 5.2 Enhanced Sandbox Service (M2)

#### 5.2.1 Permission-Aware Sandbox Service

* `openhands/app_server/sandbox/enhanced_sandbox_spec_service.py`
* `tests/unit/app_server/sandbox/test_enhanced_sandbox_spec_service.py`

Extend existing `SandboxSpecService` with permission checks and enhanced spec management. This **builds on existing infrastructure** as the engineer suggested.

#### 5.2.2 Agent Server Startup Integration

* `openhands-agent-server/openhands/agent_server/custom_agent_loader.py`
* `tests/unit/agent_server/test_custom_agent_loader.py`

Implement custom agent loading mechanism in agent server startup process with configuration-driven agent instantiation.

**Demo**: Deploy custom agents using enhanced sandbox specs and verify permission-based access control works end-to-end.

### 5.3 Image Management and API Integration (M3)

#### 5.3.1 Secure Image Management

* `openhands/app_server/sandbox/image_builder.py`
* `openhands/app_server/security/dockerfile_validator.py`
* `tests/unit/app_server/sandbox/test_image_builder.py`
* `tests/unit/app_server/security/test_dockerfile_validator.py`

Implement both **pre-built image registration** and **secure user upload** workflows as identified by the engineer. This addresses the security issues from V0.

#### 5.3.2 Enhanced Conversation API

* `openhands/server/routes/conversation_routes.py` (enhanced)
* `openhands/server/routes/sandbox_spec_routes.py` (new)
* `tests/unit/server/routes/test_enhanced_conversation_routes.py`
* `tests/unit/server/routes/test_sandbox_spec_routes.py`

Enhance existing conversation creation API to support `sandbox_spec_id` parameter and add new sandbox spec management endpoints.

**Demo**: Create conversations with custom sandbox specs through existing API endpoints and demonstrate both pre-built and user-uploaded image workflows.

### 5.4 Advanced Security and Management (M4)

#### 5.4.1 Image Security Validation

* `openhands/app_server/security/image_scanner.py`
* `openhands/app_server/security/security_policies.py`
* `tests/unit/app_server/security/test_image_scanner.py`

Implement comprehensive security validation including image vulnerability scanning, Dockerfile analysis, and approval workflows.

#### 5.4.2 Spec Registry and Lifecycle Management

* `openhands/app_server/sandbox/spec_registry.py`
* `openhands/app_server/sandbox/spec_lifecycle.py`
* `tests/unit/app_server/sandbox/test_spec_registry.py`

Add persistent storage for enhanced sandbox specs, version management, and lifecycle policies (deprecation, cleanup).

**Demo**: Deploy multiple custom agents with different permission levels, demonstrate security validation workflows, and show proper spec lifecycle management.

---

## Key Alignment with Engineer's Approach

This revised implementation plan directly addresses the engineer's requirements:

1. **✅ Uses existing sandbox specs system** - Enhanced rather than replaced
2. **✅ Permissions as core requirement** - Moved to M1 instead of M4
3. **✅ Two image management approaches** - Pre-built registration and secure user uploads
4. **✅ Security-first design** - Addresses V0 security issues with comprehensive validation
5. **✅ Minimal infrastructure changes** - Builds on existing `SandboxSpecService` and conversation APIs
