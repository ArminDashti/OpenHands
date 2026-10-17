import { useQuery, useQueryClient } from "@tanstack/react-query";
import { QueryKeys } from "./query-keys";

interface BrowserState {
  url: string;
  screenshotSrc: string;
}

const initialBrowser: BrowserState = {
  url: "https://github.com/All-Hands-AI/OpenHands",
  screenshotSrc: "",
};

/**
 * Hook to access and manipulate browser data using React Query
 */
export function useBrowser() {
  const queryClient = useQueryClient();
  const browserQueryKey = QueryKeys.browser;

  const query = useQuery({
    queryKey: browserQueryKey,
    queryFn: () => {
      // First check if we already have data in the query cache
      const existingData =
        queryClient.getQueryData<BrowserState>(browserQueryKey);
      if (existingData) return existingData;
      // Otherwise use initial state
      return initialBrowser;
    },
    initialData: initialBrowser,
    staleTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const setUrlSync = (url: string) => {
    const previousState =
      queryClient.getQueryData<BrowserState>(browserQueryKey) || initialBrowser;
    // Update state
    const newState = {
      ...previousState,
      url,
    };
    // Debug log
    // eslint-disable-next-line no-console
    console.log("[Browser Debug] Setting URL:", url, "New state:", newState);
    // Set the state synchronously
    queryClient.setQueryData<BrowserState>(browserQueryKey, newState);
  };

  // Function to directly set the screenshot source (synchronous)
  const setScreenshotSrcSync = (screenshotSrc: string) => {
    const previousState =
      queryClient.getQueryData<BrowserState>(browserQueryKey) || initialBrowser;
    // Update state
    const newState = {
      ...previousState,
      screenshotSrc,
    };
    // Debug log
    // eslint-disable-next-line no-console
    console.log(
      "[Browser Debug] Setting Screenshot:",
      screenshotSrc
        ? `Screenshot data present (length: ${screenshotSrc.length})`
        : "Empty screenshot",
      "New state:",
      { ...newState, screenshotSrc: screenshotSrc ? "data present" : "empty" },
    );
    // Set the state synchronously
    queryClient.setQueryData<BrowserState>(browserQueryKey, newState);
  };

  return {
    url: query.data?.url || initialBrowser.url,
    screenshotSrc: query.data?.screenshotSrc || initialBrowser.screenshotSrc,
    isLoading: query.isLoading,
    // Actions
    setUrl: setUrlSync,
    setScreenshotSrc: setScreenshotSrcSync,
  };
}
