from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError


class MCPSSEServerConfig(BaseModel):
    """Configuration for a single MCP server.

    Attributes:
        url: The server URL
        api_key: Optional API key for authentication
    """

    url: str
    api_key: str | None = None


class MCPConfig(BaseModel):
    """Configuration for MCP (Message Control Protocol) settings.

    Attributes:
        sse_servers: List of MCP SSE server configs
    """

    sse_servers: list[MCPSSEServerConfig] = Field(default_factory=list)

    model_config = {'extra': 'forbid'}

    def validate_servers(self) -> None:
        """Validate that server URLs are valid and unique."""
        urls = [server.url for server in self.sse_servers]

        # Check for duplicate server URLs
        if len(set(urls)) != len(urls):
            raise ValueError('Duplicate MCP server URLs are not allowed')

        # Validate URLs
        for url in urls:
            try:
                result = urlparse(url)
                if not all([result.scheme, result.netloc]):
                    raise ValueError(f'Invalid URL format: {url}')
            except Exception as e:
                raise ValueError(f'Invalid URL {url}: {str(e)}')


class MCPStdioConfigEntry(BaseModel):
    """Configuration for a single MCP stdio entry.

    Attributes:
        command: The command to run.
        args: List of arguments for the command.
        env: Dictionary of environment variables.
    """

    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)

    model_config = {'extra': 'forbid'}


class MCPStdioConfig(BaseModel):
    """Configuration for MCP stdio settings.

    Attributes:
        tools: Dictionary of tool configurations, where keys are tool names.
    """

    tools: dict[str, MCPStdioConfigEntry] = Field(default_factory=dict)

    model_config = {'extra': 'forbid'}

    def validate_stdio(self) -> None:
        """Validate that tools are properly configured."""
        # Tool names validation
        for tool_name in self.tools:
            if not tool_name.strip():
                raise ValueError('Tool names cannot be empty')
            if not tool_name.replace('-', '').isalnum():
                raise ValueError(
                    f'Invalid tool name: {tool_name}. Tool names must be alphanumeric (hyphens allowed)'
                )


class MCPConfig(BaseModel):
    """Configuration for MCP (Message Control Protocol) settings.

    Attributes:
        sse: SSE-specific configuration.
        stdio: stdio-specific configuration.
    """

    sse: MCPSSEConfig = Field(default_factory=MCPSSEConfig)
    stdio: MCPStdioConfig = Field(default_factory=MCPStdioConfig)

    model_config = {'extra': 'forbid'}

    @classmethod
    def from_toml_section(cls, data: dict) -> dict[str, 'MCPConfig']:
        """
        Create a mapping of MCPConfig instances from a toml dictionary representing the [mcp] section.

        The configuration is built from all keys in data.

        Returns:
            dict[str, MCPConfig]: A mapping where the key "mcp" corresponds to the [mcp] configuration
        """
        # Initialize the result mapping
        mcp_mapping: dict[str, MCPConfig] = {}

        try:
            # Convert all entries in sse_servers to MCPSSEServerConfig objects
            if 'sse_servers' in data:
                servers = []
                for server in data['sse_servers']:
                    if isinstance(server, dict):
                        servers.append(MCPSSEServerConfig(**server))
                    else:
                        # Convert string URLs to MCPSSEServerConfig objects with no API key
                        servers.append(MCPSSEServerConfig(url=server))
                data['sse_servers'] = servers

            # Create SSE config if present
            sse_config = MCPSSEConfig.model_validate(data.get('mcp-sse', {}))
            sse_config.validate_servers()

            # Create stdio config if present
            stdio_config = MCPStdioConfig.model_validate(data.get('mcp-stdio', {}))
            stdio_config.validate_stdio()

            # Create the main MCP config
            mcp_mapping['mcp'] = cls(sse=sse_config, stdio=stdio_config)
        except ValidationError as e:
            raise ValueError(f'Invalid MCP configuration: {e}')

        return mcp_mapping
