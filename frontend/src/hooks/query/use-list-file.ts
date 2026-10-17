import { useQuery } from "@tanstack/react-query";
import { useCallback } from "react";
import OpenHands from "#/api/open-hands";
import { useConversation } from "#/context/conversation-context";
import { QueryKeys } from "#/utils/query/query-keys";
import { useFileStateContext } from "#/context/file-state-context";

interface UseListFileConfig {
  path: string;
  enabled?: boolean;
}

/**
 * Hook to get a file's content
 * Uses React Query for data fetching and caching
 * Integrates with the file state context to handle unsaved changes
 */
export const useListFile = (config: UseListFileConfig) => {
  const { conversationId } = useConversation();
  const { getFileState, addOrUpdateFileState } = useFileStateContext();

  // Get file content from API
  const query = useQuery({
    queryKey: QueryKeys.file(conversationId, config.path),
    queryFn: () => OpenHands.getFile(conversationId, config.path),
    enabled: config.enabled ?? false, // don't fetch by default, trigger manually via `refetch`
  });
