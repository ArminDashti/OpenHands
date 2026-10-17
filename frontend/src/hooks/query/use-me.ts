import { useQuery } from "@tanstack/react-query";
import { useConfig } from "./use-config";
import { organizationService } from "#/api/organization-service/organization-service.api";
import { useSelectedOrganizationId } from "#/context/use-selected-organization";
import { OrganizationMember } from "#/types/org";

export const useMe = () => {
  const { data: config } = useConfig();
  const { orgId } = useSelectedOrganizationId();

  const isSaas = config?.APP_MODE === "saas";

  return useQuery({
    queryKey: ["organizations", orgId, "me"],
    queryFn: async () => {
      const response = await organizationService.getMe({ orgId: orgId! });
      // Find the current organization (isCurrent: true)
      const currentOrg = response.orgs.find((org) => org.isCurrent);

      if (!currentOrg) {
        throw new Error("Current organization not found in response");
      }

      const me: OrganizationMember = {
        id: response.userId,
        email: response.email,
        role: currentOrg.role,
        status: "active",
      };

      return me;
    },
    enabled: isSaas && !!orgId,
  });
};
