import { useState } from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import ChevronDownIcon from "#/icons/chevron-down.svg?react";
import MessageSquareShareIcon from "#/icons/message-square-share.svg?react";
import { cn } from "#/utils/utils";
import { BrandButton } from "#/components/features/settings/brand-button";
import { getAutomationsDocsUrl } from "#/manifests/automation-interface";
import { AutomationConversationLaunchModal } from "./automation-conversation-launch-modal";
import type { AutomationConversationLaunchRequest } from "./use-launch-automation-conversation";

function InlineExampleWrap({ children }: { children?: ReactNode }) {
  return <span className="whitespace-nowrap">{children}</span>;
}

function InlineCodeChip({ children }: { children?: ReactNode }) {
  return (
    <code
      data-testid="automations-create-instructions-example"
      className={cn(
        "mx-0.5 inline-block rounded-sm border border-border-subtle",
        "bg-surface-raised px-1.5 py-0.5 align-baseline font-mono text-[11px] text-contrast",
      )}
    >
      {children}
    </code>
  );
}

function InlinePunctuation({ children }: { children?: ReactNode }) {
  return <>{children}</>;
}

const CREATE_INSTRUCTIONS_INLINE_COMPONENTS = {
  example: <InlineExampleWrap />,
  cmd: <InlineCodeChip />,
  punct: <InlinePunctuation />,
};

interface CreateInstructionsProps {
  /** If true, the instructions are collapsible and start collapsed */
  collapsible?: boolean;
}

interface CreateInstructionsContentProps {
  onLaunch?: () => void;
}

interface AutomationStartOptionProps {
  title: string;
  description: string;
  buttonLabel: string;
  testId: string;
  buttonTestId: string;
  onClick: () => void;
}

function AutomationStartOption({
  title,
  description,
  buttonLabel,
  testId,
  buttonTestId,
  onClick,
}: AutomationStartOptionProps) {
  return (
    <section
      data-testid={testId}
      className="flex h-full min-w-0 flex-col justify-between gap-4 rounded-lg border border-[var(--oh-border)] bg-[var(--oh-surface)] p-4"
    >
      <div className="min-w-0">
        <h4 className="text-sm font-medium text-content">{title}</h4>
        <p className="mt-1 text-xs leading-relaxed text-tertiary-light">
          {description}
        </p>
      </div>
      <BrandButton
        type="button"
        variant="primary"
        testId={buttonTestId}
        className="mt-auto h-auto min-h-10 w-full px-4 py-2 text-center leading-tight"
        onClick={onClick}
        startContent={
          <MessageSquareShareIcon className="size-4 shrink-0" aria-hidden />
        }
      >
        {buttonLabel}
      </BrandButton>
    </section>
  );
}

export function CreateInstructionsContent({
  onLaunch,
}: CreateInstructionsContentProps = {}) {
  const { t } = useTranslation("openhands");
  const [launchRequest, setLaunchRequest] =
    useState<AutomationConversationLaunchRequest | null>(null);

  const handleFindOpportunities = () => {
    setLaunchRequest({
      intent: "find_opportunities",
      source: "empty_state",
      prompt: t(I18nKey.AUTOMATIONS$CREATE_AUTOMATION_PROMPT),
    });
  };

  const handleAddAutomation = () => {
    setLaunchRequest({
      intent: "add_automation",
      source: "empty_state",
      prompt: t(I18nKey.AUTOMATIONS$ADD_AUTOMATION_PROMPT),
    });
  };

  const handleLaunchModalClose = () => {
    setLaunchRequest(null);
    onLaunch?.();
  };

  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm leading-relaxed text-tertiary-light">
        <Trans
          ns="openhands"
          i18nKey={I18nKey.AUTOMATIONS$EMPTY_OPTION_CONVERSATION_DESC}
          components={CREATE_INSTRUCTIONS_INLINE_COMPONENTS}
        />{" "}
        {t(I18nKey.AUTOMATIONS$CREATE_INSTRUCTIONS_GUIDANCE)}{" "}
        <a
          href={getAutomationsDocsUrl()}
          target="_blank"
          rel="noopener noreferrer"
          className="text-muted underline transition-colors hover:text-foreground"
        >
          {t(I18nKey.AUTOMATIONS$EMPTY_LEARN_MORE)}
        </a>
      </p>

      <div className="flex justify-center">
        <BrandButton
          type="button"
          variant="primary"
          testId="automations-create-automation"
          isDisabled={createConversation.isPending}
          onClick={handleCreateAutomation}
          startContent={
            <MessageSquareShareIcon className="size-4" aria-hidden />
          }
        >
          {t(I18nKey.AUTOMATIONS$CREATE_AUTOMATION_BUTTON)}
        </BrandButton>
      </div>
      <AutomationConversationLaunchModal
        request={launchRequest}
        onClose={handleLaunchModalClose}
      />
    </>
  );
}

export function CreateInstructions({
  collapsible = false,
}: CreateInstructionsProps) {
  const { t } = useTranslation("openhands");
  const [isExpanded, setIsExpanded] = useState(!collapsible);

  if (collapsible) {
    return (
      <div className="w-full rounded-lg border border-border bg-surface">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-expanded={isExpanded}
          className="flex w-full items-center justify-between rounded-lg p-4 text-left transition-colors hover:bg-surface-raised"
        >
          <span className="text-sm font-normal text-content">
            {t(I18nKey.AUTOMATIONS$EMPTY_HOW_TO_CREATE_TITLE)}
          </span>
          <ChevronDownIcon
            className={cn(
              "size-5 text-muted transition-transform",
              isExpanded && "rotate-180",
            )}
          />
        </button>
        {isExpanded ? (
          <div className="px-4 pb-4">
            <CreateInstructionsContent />
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl">
      <CreateInstructionsContent />
    </div>
  );
}
