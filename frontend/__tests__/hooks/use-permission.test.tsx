import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { usePermission } from "#/hooks/organizations/use-permissions";
import { rolePermissions, PermissionKey } from "#/utils/org/permissions";
import { OrganizationUserRole } from "#/types/org";

describe("usePermission", () => {
  const setup = (role: OrganizationUserRole) =>
    renderHook(() => usePermission(role)).result.current;

  describe("hasPermission", () => {
    it("returns true when the role has the permission", () => {
      const { hasPermission } = setup("admin");

      expect(hasPermission("invite_user_to_organization")).toBe(true);
    });

    it("returns false when the role does not have the permission", () => {
      const { hasPermission } = setup("user");

      expect(hasPermission("invite_user_to_organization")).toBe(false);
    });
  });

  describe("rolePermissions integration", () => {
    it("matches the permissions defined for the role", () => {
      const { hasPermission } = setup("user");

      rolePermissions.user.forEach((permission: PermissionKey) => {
        expect(hasPermission(permission)).toBe(true);
      });
    });
  });

  describe("change_user_role permission behavior", () => {
    const run = (
      activeUserRole: OrganizationUserRole,
      targetUserId: string,
      targetRole: OrganizationUserRole,
      activeUserId = "123",
    ) => {
      const { hasPermission } = renderHook(() =>
        usePermission(activeUserRole),
      ).result.current;

      // users can't change their own roles
      if (activeUserId === targetUserId) return false;

      return hasPermission(`change_user_role:${targetRole}`);
    };

    describe("user role", () => {
      it("cannot change any roles", () => {
        expect(run("user", "u2", "user")).toBe(false);
        expect(run("user", "u2", "admin")).toBe(false);
        expect(run("user", "u2", "owner")).toBe(false);
      });
    });

    describe("admin role", () => {
      it("cannot change owner role", () => {
         expect(run("admin", "u2", "owner")).toBe(false);
      });

      it("can change user or admin roles", () => {
        expect(run("admin", "u2", "user")).toBe(
          rolePermissions.admin.includes("change_user_role:user")
        );
        expect(run("admin", "u2", "admin")).toBe(
          rolePermissions.admin.includes("change_user_role:admin")
        );
      });
    });

    describe("owner role", () => {
      it("can change owner, admin, and user roles", () => {
        expect(run("owner", "u2", "admin")).toBe(
          rolePermissions.owner.includes("change_user_role:admin"),
        );

        expect(run("owner", "u2", "user")).toBe(
          rolePermissions.owner.includes("change_user_role:user"),
        );

        expect(run("owner", "u2", "owner")).toBe(
          rolePermissions.owner.includes("change_user_role:owner"),
        );
      });
    });

    describe("self role change", () => {
      it("is always disallowed", () => {
        expect(run("owner", "u2", "user", "u2")).toBe(false);
        expect(run("admin", "u2", "user", "u2")).toBe(false);
      });
    });
  });
});
