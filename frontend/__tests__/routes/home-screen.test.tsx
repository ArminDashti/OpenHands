import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { createRoutesStub } from "react-router";
import { Provider } from "react-redux";
import { setupStore } from "test-utils";
import { AxiosError } from "axios";
import HomeScreen from "#/routes/home";
import { AuthProvider } from "#/context/auth-context";
import * as GitService from "#/api/git";
import { GitRepository } from "#/types/git";
import SettingsService from "#/settings-service/settings-service.api";
import OpenHands from "#/api/open-hands";
import UserService from "#/api/user-service/user-service.api";
import MainApp from "#/routes/root-layout";

const createAxiosNotFoundErrorObject = () =>
  new AxiosError(
    "Request failed with status code 404",
    "ERR_BAD_REQUEST",
    undefined,
    undefined,
    {
      status: 404,
      statusText: "Not Found",
      data: { message: "Settings not found" },
      headers: {},
      // @ts-expect-error - we only need the response object for this test
      config: {},
    },
  );

const { DEFAULT_FEATURE_FLAGS, useIsAuthedMock, useConfigMock } = vi.hoisted(
  () => {
    const defaultFeatureFlags = {
      ENABLE_BILLING: false,
      HIDE_LLM_SETTINGS: false,
      ENABLE_JIRA: false,
      ENABLE_JIRA_DC: false,
      ENABLE_LINEAR: false,
    };

    return {
      DEFAULT_FEATURE_FLAGS: defaultFeatureFlags,
      useIsAuthedMock: vi.fn().mockReturnValue({
        data: true,
        isLoading: false,
        isFetching: false,
        isError: false,
      }),
      useConfigMock: vi.fn().mockReturnValue({
        data: {
          APP_MODE: "oss",
          FEATURE_FLAGS: defaultFeatureFlags,
        },
        isLoading: false,
      }),
    };
  },
);

vi.mock("#/hooks/query/use-is-authed", () => ({
  useIsAuthed: () => useIsAuthedMock(),
}));

vi.mock("#/hooks/query/use-config", () => ({
  useConfig: () => useConfigMock(),
}));

const RouterStub = createRoutesStub([
  {
    Component: MainApp,
    path: "/",
    children: [
      {
        Component: HomeScreen,
        path: "/",
      },
      {
        Component: () => <div data-testid="conversation-screen" />,
        path: "/conversations/:conversationId",
      },
      {
        Component: () => <div data-testid="settings-screen" />,
        path: "/settings",
      },
    ],
  },
  {
    Component: () => <div data-testid="login-page" />,
    path: "/login",
  },
]);

const renderHomeScreen = (initialProvidersAreSet = true) =>
  render(<RouterStub />, {
    wrapper: ({ children }) => (
      <Provider store={setupStore()}>
        <AuthProvider initialProvidersAreSet={initialProvidersAreSet}>
          <QueryClientProvider client={new QueryClient()}>
            {children}
          </QueryClientProvider>
        </AuthProvider>
      </Provider>
    ),
  });

const MOCK_RESPOSITORIES: GitRepository[] = [
  {
    id: 1,
    full_name: "octocat/hello-world",
    git_provider: "github",
    is_public: true,
  },
  {
    id: 2,
    full_name: "octocat/earth",
    git_provider: "github",
    is_public: true,
  },
];

describe("HomeScreen", () => {
  it("should render", () => {
    renderHomeScreen();
    await screen.findByTestId("home-screen");
  });

  it("should render the repository connector and suggested tasks sections", async () => {
    renderHomeScreen();

    screen.getByTestId("repo-connector");
    screen.getByTestId("task-suggestions");
  });

  it("should filter the suggested tasks based on the selected repository", async () => {
    const retrieveUserGitRepositoriesSpy = vi.spyOn(
      GitService,
      "retrieveUserGitRepositories",
    );
    retrieveUserGitRepositoriesSpy.mockResolvedValue({
      data: MOCK_RESPOSITORIES,
      nextPage: null,
    });

    renderHomeScreen();

    const taskSuggestions = screen.getByTestId("task-suggestions");

    // Initially, all tasks should be visible
    await waitFor(() => {
      within(taskSuggestions).getByText("octocat/hello-world");
      within(taskSuggestions).getByText("octocat/earth");
    });

    // Select a repository from the dropdown
    const repoConnector = screen.getByTestId("repo-connector");

    const dropdown = within(repoConnector).getByTestId("repo-dropdown");
    await userEvent.click(dropdown);

    const repoOption = screen.getAllByText("octocat/hello-world")[1];
    await userEvent.click(repoOption);

    // After selecting a repository, only tasks related to that repository should be visible
    await waitFor(() => {
      within(taskSuggestions).getByText("octocat/hello-world");
      expect(
        within(taskSuggestions).queryByText("octocat/earth"),
      ).not.toBeInTheDocument();
    });
  });

  it("should reset the filtered tasks when the selected repository is cleared", async () => {
    const retrieveUserGitRepositoriesSpy = vi.spyOn(
      GitService,
      "retrieveUserGitRepositories",
    );
    retrieveUserGitRepositoriesSpy.mockResolvedValue({
      data: MOCK_RESPOSITORIES,
      nextPage: null,
    });

    renderHomeScreen();

    const taskSuggestions = screen.getByTestId("task-suggestions");

    // Initially, all tasks should be visible
    await waitFor(() => {
      within(taskSuggestions).getByText("octocat/hello-world");
      within(taskSuggestions).getByText("octocat/earth");
    });

    // Select a repository from the dropdown
    const repoConnector = screen.getByTestId("repo-connector");

    const dropdown = within(repoConnector).getByTestId("repo-dropdown");
    await userEvent.click(dropdown);

    const repoOption = screen.getAllByText("octocat/hello-world")[1];
    await userEvent.click(repoOption);

    // After selecting a repository, only tasks related to that repository should be visible
    await waitFor(() => {
      within(taskSuggestions).getByText("octocat/hello-world");
      expect(
        within(taskSuggestions).queryByText("octocat/earth"),
      ).not.toBeInTheDocument();
    });

    // Clear the selected repository
    await userEvent.clear(dropdown);

    // All tasks should be visible again
    await waitFor(() => {
      within(taskSuggestions).getByText("octocat/hello-world");
      within(taskSuggestions).getByText("octocat/earth");
    });
  });

  describe("launch buttons", () => {
    const setupLaunchButtons = async () => {
      // Mock the branch retrieval to return branches including main
      const getRepositoryBranchesSpy = vi.spyOn(
        OpenHands,
        "getRepositoryBranches",
      );
      getRepositoryBranchesSpy.mockResolvedValue([
        { name: "main" },
        { name: "develop" }
      ]);
      
      let headerLaunchButton = screen.getByTestId("header-launch-button");
      let repoLaunchButton = screen.getByTestId("repo-launch-button");
      let tasksLaunchButtons =
        await screen.findAllByTestId("task-launch-button");

      // Select a repository from the dropdown to enable the repo launch button
      const repoConnector = screen.getByTestId("repo-connector");
      const dropdown = within(repoConnector).getByTestId("repo-dropdown");
      await userEvent.click(dropdown);
      const repoOption = screen.getAllByText("octocat/hello-world")[1];
      await userEvent.click(repoOption);
      
      // Wait for the branch to be auto-selected
      await waitFor(() => {
        expect(repoLaunchButton).toBeEnabled();
      });

      // With the new branch selection logic, main branch should be auto-selected
      expect(headerLaunchButton).toBeEnabled();
      expect(repoLaunchButton).toBeEnabled();
      tasksLaunchButtons.forEach((button) => {
        expect(button).toBeEnabled();
      });

      headerLaunchButton = screen.getByTestId("header-launch-button");
      repoLaunchButton = screen.getByTestId("repo-launch-button");
      tasksLaunchButtons = await screen.findAllByTestId("task-launch-button");

      return {
        headerLaunchButton,
        repoLaunchButton,
        tasksLaunchButtons,
      };
    };

    beforeEach(() => {
      const retrieveUserGitRepositoriesSpy = vi.spyOn(
        GitService,
        "retrieveUserGitRepositories",
      );
      retrieveUserGitRepositoriesSpy.mockResolvedValue({
        data: MOCK_RESPOSITORIES,
        nextPage: null,
      });
    });

    it("should disable the other launch buttons when the header launch button is clicked", async () => {
      renderHomeScreen();
      const { headerLaunchButton, repoLaunchButton } =
        await setupLaunchButtons();

      const tasksLaunchButtonsAfter =
        await screen.findAllByTestId("task-launch-button");

      // All other buttons should be disabled when the header button is clicked
      await userEvent.click(headerLaunchButton);

      expect(headerLaunchButton).toBeDisabled();
      expect(repoLaunchButton).toBeDisabled();
      tasksLaunchButtonsAfter.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });

    it("should disable the other launch buttons when the repo launch button is clicked", async () => {
      renderHomeScreen();
      const { headerLaunchButton, repoLaunchButton } =
        await setupLaunchButtons();

      const tasksLaunchButtonsAfter =
        await screen.findAllByTestId("task-launch-button");

      // All other buttons should be disabled when the repo button is clicked
      await userEvent.click(repoLaunchButton);

      expect(headerLaunchButton).toBeDisabled();
      expect(repoLaunchButton).toBeDisabled();
      tasksLaunchButtonsAfter.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });

    it("should disable the other launch buttons when any task launch button is clicked", async () => {
      renderHomeScreen();
      const { headerLaunchButton, repoLaunchButton, tasksLaunchButtons } =
        await setupLaunchButtons();

      const tasksLaunchButtonsAfter =
        await screen.findAllByTestId("task-launch-button");

      // All other buttons should be disabled when the task button is clicked
      await userEvent.click(tasksLaunchButtons[0]);

      expect(headerLaunchButton).toBeDisabled();
      expect(repoLaunchButton).toBeDisabled();
      tasksLaunchButtonsAfter.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });
  });

  it("should hide the suggested tasks section if not authed with git(hub|lab)", async () => {
    renderHomeScreen(false);

    const taskSuggestions = screen.queryByTestId("task-suggestions");
    const repoConnector = screen.getByTestId("repo-connector");

    expect(taskSuggestions).not.toBeInTheDocument();
    expect(repoConnector).toBeInTheDocument();
  });
});

describe("Settings 404", () => {
  const getConfigSpy = vi.spyOn(OpenHands, "getConfig");
  const getSettingsSpy = vi.spyOn(SettingsService, "getSettings");

  beforeEach(() => {
    vi.resetAllMocks();

    useIsAuthedMock.mockReturnValue({
      data: true,
      isLoading: false,
      isFetching: false,
      isError: false,
    });
    useConfigMock.mockReturnValue({
      data: { APP_MODE: "oss", FEATURE_FLAGS: DEFAULT_FEATURE_FLAGS },
      isLoading: false,
    });

    getConfigSpy.mockResolvedValue({
      APP_MODE: "oss",
      GITHUB_CLIENT_ID: "test-client-id",
      POSTHOG_CLIENT_KEY: "test-posthog-key",
      PROVIDERS_CONFIGURED: ["github"],
      AUTH_URL: "https://auth.example.com",
      FEATURE_FLAGS: DEFAULT_FEATURE_FLAGS,
    } as Awaited<ReturnType<typeof OptionService.getConfig>>);

    vi.spyOn(AuthService, "authenticate").mockResolvedValue(true);

    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);

    vi.stubGlobal("localStorage", {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("should open the settings modal if GET /settings fails with a 404", async () => {
    const error = createAxiosNotFoundErrorObject();
    getSettingsSpy.mockRejectedValue(error);

    renderHomeScreen();

    const settingsModal = await screen.findByTestId("ai-config-modal");
    expect(settingsModal).toBeInTheDocument();
  });

  it("should navigate to the settings screen when clicking the advanced settings button", async () => {
    const error = createAxiosNotFoundErrorObject();
    getSettingsSpy.mockRejectedValue(error);

    const user = userEvent.setup();
    renderHomeScreen();

    const settingsScreen = screen.queryByTestId("settings-screen");
    expect(settingsScreen).not.toBeInTheDocument();

    const settingsModal = await screen.findByTestId("ai-config-modal");
    expect(settingsModal).toBeInTheDocument();

    const advancedSettingsButton = await screen.findByTestId(
      "advanced-settings-link",
    );
    await user.click(advancedSettingsButton);

    const settingsScreenAfter = await screen.findByTestId("settings-screen");
    expect(settingsScreenAfter).toBeInTheDocument();

    const settingsModalAfter = screen.queryByTestId("ai-config-modal");
    expect(settingsModalAfter).not.toBeInTheDocument();
  });

  it("should not open the settings modal if GET /settings fails but is SaaS mode", async () => {
    useConfigMock.mockReturnValue({
      data: { APP_MODE: "saas", FEATURE_FLAGS: DEFAULT_FEATURE_FLAGS },
      isLoading: false,
    });

    // @ts-expect-error - we only need APP_MODE for this test
    getConfigSpy.mockResolvedValue({
      APP_MODE: "saas",
      FEATURE_FLAGS: {
        ENABLE_BILLING: false,
        HIDE_LLM_SETTINGS: false,
      },
    });
    const error = createAxiosNotFoundErrorObject();
    getSettingsSpy.mockRejectedValue(error);

    renderHomeScreen();

    // small hack to wait for the modal to not appear
    await expect(
      screen.findByTestId("ai-config-modal", {}, { timeout: 1000 }),
    ).rejects.toThrow();
  });
});

describe("Setup Payment modal", () => {
  const getConfigSpy = vi.spyOn(OpenHands, "getConfig");
  const getSettingsSpy = vi.spyOn(SettingsService, "getSettings");

  beforeEach(() => {
    vi.clearAllMocks();

    useIsAuthedMock.mockReturnValue({
      data: true,
      isLoading: false,
      isFetching: false,
      isError: false,
    });
    useConfigMock.mockReturnValue({
      data: {
        APP_MODE: "saas",
        FEATURE_FLAGS: { ...DEFAULT_FEATURE_FLAGS, ENABLE_BILLING: true },
      },
      isLoading: false,
    });

    getConfigSpy.mockResolvedValue({
      APP_MODE: "saas",
      FEATURE_FLAGS: {
        ENABLE_BILLING: true,
        HIDE_LLM_SETTINGS: false,
      },
    });

    renderHomeScreen();

    await screen.findByTestId("root-layout");

    const setupPaymentModal = await screen.findByTestId(
      "proceed-to-stripe-button",
    );
    expect(setupPaymentModal).toBeInTheDocument();
  });
});
