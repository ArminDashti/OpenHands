import React from "react";
import { useTranslation } from "react-i18next";
import { useUnifiedResumeConversationSandbox } from "#/hooks/mutation/use-unified-start-conversation";
import { useUserProviders } from "#/hooks/use-user-providers";
import { useVisibilityChange } from "#/hooks/use-visibility-change";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { I18nKey } from "#/i18n/declaration";
import type { ConversationStatus } from "#/types/conversation-status";
import type { Conversation } from "#/api/open-hands.types";

interface UseSandboxRecoveryOptions {
  conversationId: string | undefined;
  conversationStatus: ConversationStatus | undefined;
  /** Function to refetch the conversation data - used to get fresh status on tab focus */
  refetchConversation?: () => Promise<{
    data: Conversation | null | undefined;
  }>;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export function useSandboxRecovery({
  conversationId,
  conversationStatus,
  refetchConversation,
  onSuccess,
  onError,
}: UseSandboxRecoveryOptions) {
  const { t } = useTranslation();
  const { providers } = useUserProviders();
  const { mutate: resumeSandbox, isPending: isResuming } =
    useUnifiedResumeConversationSandbox();

  const processedConversationIdRef = React.useRef<string | null>(null);

  const attemptRecovery = React.useCallback(
    (statusOverride?: ConversationStatus) => {
      const status = statusOverride ?? conversationStatus;
      /**
       * Only recover if sandbox is paused (status === STOPPED) and not already resuming
       *
       * Note: ConversationStatus uses different terminology than SandboxStatus:
       *   - SandboxStatus.PAUSED  → ConversationStatus.STOPPED : the runtime is not running but may be restarted
       *   - SandboxStatus.MISSING → ConversationStatus.ARCHIVED : the runtime is not running and will not restart due to deleted files.
       */
      if (!conversationId || status !== "STOPPED" || isResuming) {
        return;
      }

      resumeSandbox(
        { conversationId, providers },
        {
          onSuccess: () => {
            onSuccess?.();
          },
          onError: (error) => {
            displayErrorToast(
              t(I18nKey.CONVERSATION$FAILED_TO_START_WITH_ERROR, {
                error: error.message,
              }),
            );
            onError?.(error);
          },
        },
      );
    },
    [
      conversationId,
      conversationStatus,
      isResuming,
      providers,
      resumeSandbox,
      onSuccess,
      onError,
      t,
    ],
  );

  React.useEffect(() => {
    if (!conversationId || !conversationStatus) return;

    // Only attempt recovery once per conversation (handles both initial load and navigation)
    if (processedConversationIdRef.current === conversationId) return;

    processedConversationIdRef.current = conversationId;

    if (conversationStatus === "STOPPED") {
      attemptRecovery();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, conversationStatus]);

  const handleVisible = React.useCallback(async () => {
    if (!conversationId || !refetchConversation) return;

    try {
      const { data } = await refetchConversation();
      attemptRecovery(data?.status);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(
        "Failed to refetch conversation on visibility change:",
        error,
      );
    }
  }, [conversationId, refetchConversation, isResuming, attemptRecovery]);

  useVisibilityChange({
    enabled: !!conversationId,
    onVisible: handleVisible,
  });

  return { isResuming };
}
