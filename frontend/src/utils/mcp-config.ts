import {
  MCPConfig,
  MCPSSEServer,
  MCPSHTTPServer,
  MCPStdioServer,
} from "#/types/settings";

const EMPTY_MCP_CONFIG: MCPConfig = {
  sse_servers: [],
  stdio_servers: [],
  shttp_servers: [],
};

/**
 * Parse an mcp_config value that may be in either legacy format
 * ({ sse_servers, stdio_servers, shttp_servers }) or SDK format
 * ({ mcpServers: { ... } }), and always return a valid legacy MCPConfig.
 *
 * Mirrors the backend's _sdk_mcp_config_to_legacy conversion.
 */
export function parseMcpConfig(value: unknown): MCPConfig {
  if (!value || typeof value !== "object") {
    return { ...EMPTY_MCP_CONFIG };
  }

  const obj = value as Record<string, unknown>;

  // SDK format: { mcpServers: { serverName: { url, transport, ... } } }
  if (
    "mcpServers" in obj &&
    obj.mcpServers &&
    typeof obj.mcpServers === "object"
  ) {
    const sseServers: (string | MCPSSEServer)[] = [];
    const stdioServers: MCPStdioServer[] = [];
    const shttpServers: (string | MCPSHTTPServer)[] = [];

    const mcpServers = obj.mcpServers as Record<
      string,
      Record<string, unknown>
    >;

    for (const [serverName, serverConfig] of Object.entries(mcpServers)) {
      // eslint-disable-next-line no-continue
      if (!serverConfig || typeof serverConfig !== "object") continue;

      const url = serverConfig.url as string | undefined;

      if (url) {
        const transport = serverConfig.transport as string | undefined;
        const auth = serverConfig.auth as string | undefined;
        const apiKey =
          typeof auth === "string" && auth !== "oauth" ? auth : undefined;

        if (transport === "sse") {
          const server: MCPSSEServer = { url };
          if (apiKey) server.api_key = apiKey;
          sseServers.push(server);
        } else {
          // "http" transport or unspecified → shttp
          const server: MCPSHTTPServer = { url };
          if (apiKey) server.api_key = apiKey;
          if (serverConfig.timeout != null) {
            server.timeout = serverConfig.timeout as number;
          }
          shttpServers.push(server);
        }
      } else {
        // stdio server (no url, has command)
        const stdioServer: MCPStdioServer = {
          name: serverName,
          command: serverConfig.command as string,
        };
        if (serverConfig.args) {
          stdioServer.args = serverConfig.args as string[];
        }
        if (serverConfig.env) {
          stdioServer.env = serverConfig.env as Record<string, string>;
        }
        stdioServers.push(stdioServer);
      }
    }

    return {
      sse_servers: sseServers,
      stdio_servers: stdioServers,
      shttp_servers: shttpServers,
    };
  }

  // Legacy format: ensure arrays exist
  return {
    sse_servers: Array.isArray(obj.sse_servers)
      ? (obj.sse_servers as (string | MCPSSEServer)[])
      : [],
    stdio_servers: Array.isArray(obj.stdio_servers)
      ? (obj.stdio_servers as MCPStdioServer[])
      : [],
    shttp_servers: Array.isArray(obj.shttp_servers)
      ? (obj.shttp_servers as (string | MCPSHTTPServer)[])
      : [],
  };
}
