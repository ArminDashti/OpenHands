import { useTranslation } from "react-i18next";
import {
  BaseModalDescription,
  BaseModalTitle,
} from "#/components/shared/modals/confirmation-modals/base-modal";
import { ModalBackdrop } from "#/components/shared/modals/modal-backdrop";
import { ModalBody } from "#/components/shared/modals/modal-body";
import { BrandButton } from "../settings/brand-button";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { I18nKey } from "#/i18n/declaration";
import { OrganizationUserRole } from "#/types/org";

interface ConfirmRoleChangeModalProps {
  email: string;
  newRole: OrganizationUserRole;
  isPending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmRoleChangeModal({
  email,
  newRole,
  isPending,
  onConfirm,
  onCancel,
}: ConfirmRoleChangeModalProps) {
  const { t } = useTranslation();

  return (
    <ModalBackdrop onClose={isPending ? undefined : onCancel}>
      <ModalBody className="items-start border border-tertiary">
        <div className="flex flex-col gap-2">
          <BaseModalTitle title={t(I18nKey.ORG$CONFIRM_ROLE_CHANGE)} />
          <BaseModalDescription>
            {t(I18nKey.ORG$CONFIRM_ROLE_CHANGE_MESSAGE, {
              email,
              role: newRole,
            })}
          </BaseModalDescription>
        </div>
        <div
          className="flex flex-col gap-2 w-full"
          onClick={(event) => event.stopPropagation()}
        >
          <BrandButton
            type="button"
            variant="primary"
            onClick={onConfirm}
            className="w-full flex items-center justify-center"
            testId="confirm-button"
            isDisabled={isPending}
          >
            {isPending ? (
              <LoadingSpinner size="small" />
            ) : (
              t(I18nKey.BUTTON$CONFIRM)
            )}
          </BrandButton>
          <BrandButton
            type="button"
            variant="secondary"
            onClick={onCancel}
            className="w-full"
            testId="cancel-button"
            isDisabled={isPending}
          >
            {t(I18nKey.BUTTON$CANCEL)}
          </BrandButton>
        </div>
      </ModalBody>
    </ModalBackdrop>
  );
}
