import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, AsyncGenerator

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field

from openhands.core.logger import openhands_logger as logger
from openhands.mcp.tool import MCPClientTool


class MCPClient(BaseModel):
    """
    A collection of tools that connects to an MCP server and manages available tools through the Model Context Protocol.
    
    This client uses a stateless approach where a new connection is created for each operation
    and automatically cleaned up afterward using context managers.
    """

    server_url: str = ""
    api_key: Optional[str] = None
    description: str = 'MCP client tools for server interaction'
    tools: List[MCPClientTool] = Field(default_factory=list)
    tool_map: Dict[str, MCPClientTool] = Field(default_factory=dict)
    connection_timeout: float = 30.0

    class Config:
        arbitrary_types_allowed = True

    @asynccontextmanager
    async def _create_session(self, timeout: float | None = None) -> AsyncGenerator[ClientSession, None]:
        """Create a new session for a single operation and clean it up afterward.
        
        This context manager handles all the connection setup and teardown.
        
        Args:
            timeout: Connection timeout in seconds. Default is the client's connection_timeout.
            
        Yields:
            A connected ClientSession that will be automatically cleaned up.
        """
        if not self.server_url:
            raise ValueError('Server URL is required.')
            
        if timeout is None:
            timeout = self.connection_timeout
            
        # Create streams context with timeout
        headers = {'Authorization': f'Bearer {self.api_key}'} if self.api_key else None
        
        try:
            # Use nested async with statements to automatically handle cleanup
            async with sse_client(
                url=self.server_url,
                timeout=timeout,
                headers=headers,
            ) as streams:
                async with ClientSession(*streams) as session:
                    # Yield the session for use
                    yield session
        except Exception as e:
            logger.error(f'Error with MCP session: {str(e)}')
            raise

    async def connect_sse(
        self, server_url: str, timeout: float = 30.0, api_key: str | None = None
    ) -> None:
        """Connect to an MCP server using SSE transport and fetch available tools.
        
        This method stores the connection parameters and fetches the available tools,
        but doesn't maintain an active connection.
        
        Args:
            server_url: The URL of the SSE server to connect to.
            timeout: Connection timeout in seconds. Default is 30 seconds.
            api_key: Optional API key for authentication.
        """
        if not server_url:
            raise ValueError('Server URL is required.')
        if self.session:
            await self.disconnect()

        try:
            import asyncio
            from asyncio import TimeoutError

            # Create a task for the connection
            connection_task = asyncio.create_task(
                self._connect_sse_internal(server_url)
            )

            # Wait for the connection with timeout
            try:
                await asyncio.wait_for(connection_task, timeout=timeout)
            except TimeoutError:
                logger.error(
                    f'Connection to {server_url} timed out after {timeout} seconds'
                )
                # Cancel the connection task
                connection_task.cancel()
                try:
                    await connection_task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.error(f'Error connecting to {server_url}: {str(e)}')

    async def _connect_sse_internal(self, server_url: str) -> None:
        """Internal method to establish SSE connection."""
        streams_context = sse_client(
            url=server_url,
        )
        streams = await self.exit_stack.enter_async_context(streams_context)
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(*streams)
        )

        await self._initialize_and_list_tools()

    async def connect_stdio(
        self,
        command: str,
        args: List[str],
        envs: List[tuple[str, str]],
        timeout: float = 30.0,
    ) -> None:
        """Connect to an MCP server using stdio transport.

        Args:
            command: The command to execute.
            args: The arguments to pass to the command.
            envs: Environment variables as a list of tuples [name, value].
            timeout: Connection timeout in seconds. Default is 30 seconds.
        """
        if not command:
            raise ValueError('Server command is required.')
        if self.session:
            await self.disconnect()

        try:
            import asyncio
            from asyncio import TimeoutError

            # Create a task for the connection
            connection_task = asyncio.create_task(
                self._connect_stdio_internal(command, args, envs)
            )

            # Wait for the connection with timeout
            try:
                await asyncio.wait_for(connection_task, timeout=timeout)
            except TimeoutError:
                logger.error(
                    f'Connection to {command} timed out after {timeout} seconds'
                )
                # Cancel the connection task
                connection_task.cancel()
                try:
                    await connection_task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            logger.error(f'Error connecting to {command}: {str(e)}')

    async def _connect_stdio_internal(
        self, command: str, args: List[str], envs: List[tuple[str, str]]
    ) -> None:
        """Internal method to establish stdio connection."""
        envs_dict: dict[str, str] = {}
        for env in envs:
            envs_dict[env[0]] = env[1]
        server_params = StdioServerParameters(command=command, args=args, env=envs_dict)
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        await self._initialize_and_list_tools()

    async def _initialize_and_list_tools(self) -> None:
        """Initialize session and populate tool map."""
        if not self.session:
            raise RuntimeError('Session not initialized.')

        await self.session.initialize()
        response = await self.session.list_tools()

        # Clear existing tools
        self.tools = []
        self.tool_map = {}
        
        # Fetch available tools using a temporary connection
        await self._fetch_tools(timeout)

    async def _fetch_tools(self, timeout: float = None) -> None:
        """Fetch available tools from the server.
        
        Args:
            timeout: Connection timeout in seconds.
        """
        if not self.server_url:
            raise ValueError('Server URL is not set. Call connect_sse first.')
        
        # Use our context manager to create a session    
        async with self._create_session(timeout) as session:
            # Initialize the session
            await session.initialize()
            
            # Get available tools
            response = await session.list_tools()
            
            # Clear existing tools
            self.tools = []
            self.tool_map = {}
            
            # Create tool objects for each server tool
            for tool in response.tools:
                server_tool = MCPClientTool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema=tool.inputSchema,
                )
                self.tool_map[tool.name] = server_tool
                self.tools.append(server_tool)
                
            logger.info(
                f'Connected to server with tools: {[tool.name for tool in response.tools]}'
            )

    async def call_tool(self, tool_name: str, args: Dict) -> CallToolResult:
        """Call a tool on the MCP server.
        
        Creates a new connection for this specific call and cleans it up afterward.
        
        Args:
            tool_name: The name of the tool to call.
            args: The arguments to pass to the tool.
            
        Returns:
            The result of the tool execution.
        """
        if not self.server_url:
            return CallToolResult(
                content=[{"text": "Not connected to MCP server", "type": "text"}],
                isError=True,
            )
            
        if tool_name not in self.tool_map:
            return CallToolResult(
                content=[{"text": f"Tool {tool_name} not found", "type": "text"}],
                isError=True,
            )
            
        try:
            logger.debug(f"Before creating session")
            async with self._create_session() as session:
                logger.debug(f"After creating session")
                # Call the tool directly with the session
                result = await session.call_tool(tool_name, args)
                logger.debug(f"Tool {tool_name} result: {result}. Returning...")
                return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return CallToolResult(
                content=[{"text": f"Error executing tool: {str(e)}", "type": "text"}],
                isError=True,
            )

    async def disconnect(self) -> None:
        """
        Reset the client state.
        
        Since we're not maintaining persistent connections anymore, this just clears
        the stored tools and connection parameters.
        """
        self.server_url = ""
        self.api_key = None
        self.tools = []
        self.tool_map = {}
        logger.info('MCP client state reset')
