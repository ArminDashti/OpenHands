import React from "react";
import { ApiKeysManager } from "#/components/features/settings/api-keys-manager";
import { createPermissionGuard } from "#/utils/org/permission-guard";

export const clientLoader = createPermissionGuard("manage_api_keys");

function ApiKeysScreen() {
  return (
    <div className="flex flex-col grow overflow-auto p-11">
      <ApiKeysManager />
    </div>
  );
}

export default ApiKeysScreen;
