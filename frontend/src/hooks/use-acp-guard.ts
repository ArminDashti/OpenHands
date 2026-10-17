import { useEffect } from "react";
import { useNavigate } from "react-router";
import { useSettings } from "#/hooks/query/use-settings";
import { SettingsScope } from "#/types/settings";

/**
 * Redirects to /settings/agent when ACP is active.
 * Shared by LLM, condenser, and MCP settings routes, which are
 * disabled while an ACP agent is configured.
 *
 * @param scope - The settings scope; pass "personal" (default) for user
 *   settings routes. Org-scope routes skip the redirect because org admins
 *   may still need to configure LLM defaults even when users run ACP.
 */
export function useAcpGuard(scope: SettingsScope = "personal") {
  const navigate = useNavigate();
  const { data: settings } = useSettings(scope);

  const isAcpActive =
    scope === "personal" && settings?.agent_settings?.agent_kind === "acp";

  useEffect(() => {
    if (isAcpActive) {
      navigate("/settings/agent", { replace: true });
    }
  }, [isAcpActive, navigate]);
}
