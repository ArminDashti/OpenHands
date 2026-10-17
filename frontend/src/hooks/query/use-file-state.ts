import { useQuery, useQueryClient } from "@tanstack/react-query";
import { QueryKeys } from "./query-keys";
interface FileStateState {
  changed: Record<string, boolean>;
}
// Initial state
const initialFileState: FileStateState = {
  changed: {},
};
/**
 * Hook to access and manipulate file state data using React Query
 * Hook to access and manipulate state data
 */
export function useFileState() {
  const queryClient = useQueryClient();
  const queryClient = useQueryClient();
    }
    return initialFileState;
  };
  // Query for file state
  const query = useQuery({
    queryKey: QueryKeys.fileState,
    queryFn: () => {
      const existingData = queryClient.getQueryData<FileStateState>([
        "fileState",
      ]);
      if (existingData) return existingData;
      return getInitialFileStateState();
    },
    initialData: initialFileState,
    staleTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
  // Function to set changed state for a file path (synchronous)
  const setChanged = (path: string, changed: boolean) => {
    const previousState =
      queryClient.getQueryData<FileStateState>(QueryKeys.fileState) ||
      initialFileState;
    // Update state
    const newState = {
      ...previousState,
      changed: {
        ...previousState.changed,
        [path]: changed,
      },
    };
    // Debug log
    // eslint-disable-next-line no-console
    console.log("[FileState Debug] Setting changed state:", {
      path,
      changed,
      newState,
    });
    // Set the state synchronously
    queryClient.setQueryData<FileStateState>(QueryKeys.fileState, newState);
  };
  return {
    changed: query.data?.changed || initialFileState.changed,
    isLoading: query.isLoading,
    // Actions
    setChanged,
  };
}
