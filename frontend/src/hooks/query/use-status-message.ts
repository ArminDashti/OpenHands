import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { StatusMessage } from "#/types/message";
import { QueryKeys } from "./query-keys";
// Initial status message
const initialStatusMessage: StatusMessage = {
  status_update: true,
  type: "info",
  id: "",
  message: "",
};
/**
 * Hook to access and manipulate status messages using React Query
 */
export function useStatusMessage() {
  const queryClient = useQueryClient();
  const statusQueryKey = [...QueryKeys.status, "currentMessage"];
  // Query for status message
  const query = useQuery({
    queryKey: statusQueryKey,
    queryFn: () => initialStatusMessage,
    initialData: initialStatusMessage,
    staleTime: Infinity, // We manage updates manually through mutations
  });
  // Mutation to set current status message
  const setStatusMessageMutation = useMutation({
    mutationFn: (statusMessage: StatusMessage) =>
      Promise.resolve(statusMessage),
    onMutate: async (statusMessage) => {
      // eslint-disable-next-line no-console
      console.log("[Status Debug] Setting status message via mutation:", {
        id: statusMessage.id,
        message: statusMessage.message,
        type: statusMessage.type,
      });

      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: statusQueryKey,
      });
      // Get current status message
      const previousStatusMessage =
        queryClient.getQueryData<StatusMessage>(statusQueryKey);
      // Update status message
      queryClient.setQueryData(statusQueryKey, statusMessage);
      return { previousStatusMessage };
    },
    onError: (_, __, context) => {
      // eslint-disable-next-line no-console
      console.error("[Status Debug] Error setting status message");
      // Restore previous status message on error
      if (context?.previousStatusMessage) {
        queryClient.setQueryData(statusQueryKey, context.previousStatusMessage);
      }
    },
    onSuccess: (statusMessage) => {
      // eslint-disable-next-line no-console
      console.log("[Status Debug] Successfully set status message:", {
        id: statusMessage.id,
        message: statusMessage.message,
      });
    },
  });
  return {
    statusMessage: query.data || initialStatusMessage,
    isLoading: query.isLoading,
    setStatusMessage: setStatusMessageMutation.mutate,
  };
}
