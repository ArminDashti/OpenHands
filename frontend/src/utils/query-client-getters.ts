import { queryClient } from "#/query-client-config";
import { OrganizationMember } from "#/types/org";
import { organizationService } from "#/api/organization-service/organization-service.api";

export const getMeFromQueryClient = (orgId: string | undefined) =>
  queryClient.getQueryData<OrganizationMember>(["organizations", orgId, "me"]);

export const getSelectedOrgFromQueryClient = () =>
  queryClient.getQueryData<string>(["selected_organization"]);

/**
 * Fetches and transforms the user's organization membership data.
 * Checks cache first, then fetches from API if not cached.
 * Transforms GetMeResponse to OrganizationMember format.
 *
 * @param orgId - The organization ID to fetch membership for
 * @returns The transformed OrganizationMember, or null if not found
 */
export const fetchAndCacheMe = async (
  orgId: string,
): Promise<OrganizationMember | null> => {
  // Check cache first
  let me = getMeFromQueryClient(orgId);
  if (me) {
    return me;
  }

  // Fetch from API
  const response = await organizationService.getMe({ orgId });
  const currentOrg = response.orgs.find((org) => org.isCurrent);

  if (!currentOrg) {
    throw new Error("Current organization not found in response");
  }

  // Transform to OrganizationMember format
  me = {
    id: response.userId,
    email: response.email,
    role: currentOrg.role,
    status: "active",
  };

  // Cache the result
  queryClient.setQueryData(["organizations", orgId, "me"], me);

  return me;
};
