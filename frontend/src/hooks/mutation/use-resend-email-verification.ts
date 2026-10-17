import { AxiosError } from "axios";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import EmailService from "#/api/email-service/email-service.api";
import {
  displaySuccessToast,
  displayErrorToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";

export const useResendEmailVerification = () => {
  const { t } = useTranslation();

  return useMutation({
    mutationFn: ({
      userId,
      isAuthFlow,
    }: {
      userId?: string | null;
      isAuthFlow?: boolean;
    }) => EmailService.resendEmailVerification(userId, isAuthFlow),
    onSuccess: () => {
      displaySuccessToast(t(I18nKey.SETTINGS$VERIFICATION_EMAIL_SENT));
    },
    onError: (error: AxiosError) => {
      // Check if it's a rate limit error (429)
      if (error.response?.status === 429) {
        // FastAPI returns errors in { detail: "..." } format
        const errorData = error.response.data as
          | { detail?: string }
          | undefined;

        const rateLimitMessage =
          errorData?.detail ||
          retrieveAxiosErrorMessage(error) ||
          t(I18nKey.SETTINGS$FAILED_TO_RESEND_VERIFICATION);

        displayErrorToast(rateLimitMessage);
      } else {
        // For other errors, show the generic error message
        displayErrorToast(t(I18nKey.SETTINGS$FAILED_TO_RESEND_VERIFICATION));
      }
    },
  });
};
