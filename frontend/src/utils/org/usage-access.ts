import { Organization, OrganizationUserRole } from "#/types/org";

export const canAccessUsageDashboard = (
  organization: Pick<Organization, "is_personal"> | null | undefined,
  role: OrganizationUserRole | null | undefined,
) => {
  if (!organization) {
    return false;
  }

  if (organization.is_personal === true) {
    return true;
  }

  return role === "admin" || role === "owner";
};
