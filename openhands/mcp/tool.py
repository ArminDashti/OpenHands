from typing import Dict

from mcp.types import Tool

from openhands.core.logger import openhands_logger as logger


class MCPClientTool(Tool):
    """
    Represents a tool proxy that can be called on the MCP server from the client side.
    
    This version doesn't store a session reference, as sessions are created on-demand
    by the MCPClient for each operation.
    """

    class Config:
        arbitrary_types_allowed = True

    def to_param(self) -> Dict:
        """Convert tool to function call format."""
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': self.inputSchema,
            },
        }


class MCPClientTool(BaseTool):
    """Represents a tool proxy that can be called on the MCP server from the client side."""

    session: Optional[ClientSession] = None

    async def execute(self, **kwargs) -> CallToolResult:
        """Execute the tool by making a remote call to the MCP server."""
        if not self.session:
            return CallToolResult(
                content=[TextContent(text='Not connected to MCP server')], isError=True
            )

        try:
            result = await self.session.call_tool(self.name, kwargs)
            logger.debug(f'MCP tool result: {result}')
            return result
        except Exception as e:
            return CallToolResult(
                content=[TextContent(text=f'Error executing tool: {str(e)}')],
                isError=True,
            )
