import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAutomationSubPageNav } from "#/components/features/automations/dashboard/use-automation-sub-page-nav";
import { RecommendedAutomationsLauncher } from "#/components/features/automations/recommended-automations-launcher";
import { SearchInput } from "#/components/features/automations/search-input";
import { BrandButton } from "#/components/features/settings/brand-button";
import { ManifestSubpageLayout } from "#/components/features/manifest/manifest-subpage-layout";
import { AutomationConversationLaunchModal } from "#/components/features/automations/automation-conversation-launch-modal";
import type { AutomationConversationLaunchRequest } from "#/components/features/automations/use-launch-automation-conversation";
import { I18nKey } from "#/i18n/declaration";
import { getTemplatesPageSpec } from "#/manifests/automation-interface";

/**
 * The templates sub-page. It exists only while the admitted interface
 * manifest declares it — like a setup route for an id no entry claims, an
 * undeclared page is a 404 rendered by the layout's error boundary.
 */
export const clientLoader = () => {
  if (!getTemplatesPageSpec()) {
    throw new Response(null, { status: 404, statusText: "Not Found" });
  }
  return null;
};

export default function AutomationTemplates() {
  const { t } = useTranslation("openhands");
  const [searchQuery, setSearchQuery] = useState("");
  const [launchRequest, setLaunchRequest] =
    useState<AutomationConversationLaunchRequest | null>(null);
  const spec = getTemplatesPageSpec();
  const nav = useAutomationSubPageNav();

  if (!spec || !nav) return null;

  const handleFindOpportunities = () => {
    setLaunchRequest({
      intent: "find_opportunities",
      source: "templates_banner",
      prompt: t(I18nKey.AUTOMATIONS$CREATE_AUTOMATION_PROMPT),
    });
  };

  const handleAddAutomation = () => {
    setLaunchRequest({
      intent: "add_automation",
      source: "templates_banner",
      prompt: t(I18nKey.AUTOMATIONS$ADD_AUTOMATION_PROMPT),
    });
  };

  return (
    <ManifestSubpageLayout
      heading={nav.heading}
      navTestIdBase="automations-navbar"
      items={nav.items}
    >
      <div className="min-w-0">
        <h1 className="text-xl font-semibold text-content">{spec.title}</h1>
        <p className="mt-1 text-sm text-muted">{spec.description}</p>
      </div>
      <div className="w-full">
        <SearchInput value={searchQuery} onChange={setSearchQuery} />
      </div>
      <RecommendedAutomationsLauncher query={searchQuery} />
    </ManifestSubpageLayout>
  );
}
