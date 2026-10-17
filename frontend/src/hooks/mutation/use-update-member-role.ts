import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { organizationService } from "#/api/organization-service/organization-service.api";
import { OrganizationUserRole } from "#/types/org";
import { useSelectedOrganizationId } from "#/context/use-selected-organization";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { I18nKey } from "#/i18n/declaration";

export const useUpdateMemberRole = () => {
  const queryClient = useQueryClient();
  const { organizationId } = useSelectedOrganizationId();
  const { t } = useTranslation();

  return useMutation({
    mutationFn: async ({
      userId,
      role,
    }: {
      userId: string;
      role: OrganizationUserRole;
    }) => {
      if (!organizationId) {
        throw new Error("Organization ID is required to update member role");
      }
      return organizationService.updateMember({
        orgId: organizationId,
        userId,
        role,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations", "members"] });
      displaySuccessToast(t(I18nKey.ORG$UPDATE_MEMBER_ROLE_SUCCESS));
    },
    onError: () => {
      displayErrorToast(t(I18nKey.ORG$UPDATE_MEMBER_ROLE_FAILED));
    },
  });
};
