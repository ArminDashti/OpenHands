import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router";
import { useSettings } from "#/hooks/query/use-settings";
import { ACP_DISABLED_PATHS } from "#/constants/settings-nav";
import { SettingsScope } from "#/types/settings";

/**
 * Redirects to /settings/agent when ACP is active AND the calling route is
 * in the ACP-disabled set declared in ``settings-nav.tsx``. Single source
 * of truth: add ``disableUnderAcp: true`` to a nav item and both the nav
 * (greyed-out + tooltip) and this redirect (on direct navigation) pick it
 * up automatically.
 *
 * @param scope - The settings scope; pass "personal" (default) for user
 *   settings routes. Org-scope routes skip the redirect because org admins
 *   may still need to configure LLM defaults even when users run ACP.
 */
export function useAcpGuard(scope: SettingsScope = "personal") {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: settings } = useSettings(scope);

  const isAcpActive =
    scope === "personal" && settings?.agent_settings?.agent_kind === "acp";
  const shouldRedirect =
    isAcpActive && ACP_DISABLED_PATHS.has(location.pathname);

  useEffect(() => {
    if (shouldRedirect) {
      navigate("/settings/agent", { replace: true });
    }
  }, [shouldRedirect, navigate]);
}
