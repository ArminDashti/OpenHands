import { openHands } from "../open-hands-axios";
import { ConversationTrigger } from "../open-hands.types";
import { Provider } from "#/types/settings";

// V1 API Types for requests
export interface V1MessageContent {
  type: "text" | "image_url";
  text?: string;
  image_url?: {
    url: string;
  };
}

export interface V1SendMessageRequest {
  role: "user" | "system" | "assistant" | "tool";
  content: V1MessageContent[];
}

export interface V1AppConversationStartRequest {
  sandbox_id?: string | null;
  initial_message?: V1SendMessageRequest | null;
  processors?: unknown[]; // EventCallbackProcessor - keeping as unknown for now
  llm_model?: string | null;
  selected_repository?: string | null;
  selected_branch?: string | null;
  git_provider?: Provider | null;
  title?: string | null;
  trigger?: ConversationTrigger | null;
  pr_number?: number[];
}

export type V1AppConversationStartTaskStatus =
  | "WORKING"
  | "WAITING_FOR_SANDBOX"
  | "PREPARING_REPOSITORY"
  | "RUNNING_SETUP_SCRIPT"
  | "SETTING_UP_GIT_HOOKS"
  | "STARTING_CONVERSATION"
  | "READY"
  | "ERROR";

export interface V1AppConversationStartTask {
  id: string;
  created_by_user_id: string | null;
  status: V1AppConversationStartTaskStatus;
  detail: string | null;
  app_conversation_id: string | null;
  sandbox_id: string | null;
  agent_server_url: string | null;
  request: V1AppConversationStartRequest;
  created_at: string;
  updated_at: string;
}

const RESUME_POLL_INTERVAL_MS = 1000;
const RESUME_POLL_TIMEOUT_MS = 15 * 60 * 1000;

class V1ConversationService {
  /**
   * Create a new V1 conversation using the app-conversations API
   * Returns the start task immediately with app_conversation_id as null.
   * You must poll getStartTask() until status is READY to get the conversation ID.
   *
   * @returns AppConversationStartTask with task ID
   */
  static async createConversation(
    selectedRepository?: string,
    git_provider?: Provider,
    initialUserMsg?: string,
    selected_branch?: string,
    conversationInstructions?: string,
    trigger?: ConversationTrigger,
  ): Promise<V1AppConversationStartTask> {
    const body: V1AppConversationStartRequest = {
      selected_repository: selectedRepository,
      git_provider,
      selected_branch,
      title: conversationInstructions,
      trigger,
    };

    // Add initial message if provided
    if (initialUserMsg) {
      body.initial_message = {
        role: "user",
        content: [
          {
            type: "text",
            text: initialUserMsg,
          },
        ],
      };
    }

    const { data } = await openHands.post<V1AppConversationStartTask>(
      "/api/v1/app-conversations",
      body,
    );

    return data;
  }

  static async resumeAppConversation(
    conversationId: string,
  ): Promise<V1AppConversationStartTask> {
    const { data: initialTask } =
      await openHands.post<V1AppConversationStartTask>(
        `/api/v1/app-conversations/${conversationId}/resume`,
      );
    return this.waitForResumeTask(initialTask);
  }

  private static waitForResumeTask(
    initialTask: V1AppConversationStartTask,
  ): Promise<V1AppConversationStartTask> {
    const deadline = Date.now() + RESUME_POLL_TIMEOUT_MS;
    return new Promise((resolve, reject) => {
      const checkTask = (task: V1AppConversationStartTask) => {
        if (task.status === "READY") {
          if (!task.app_conversation_id) {
            reject(new Error("Resume task completed without a conversation"));
            return;
          }
          resolve(task);
          return;
        }
        if (task.status === "ERROR") {
          reject(new Error(task.detail || "Failed to resume conversation"));
          return;
        }
        if (Date.now() >= deadline) {
          reject(new Error("Timed out waiting for conversation resume"));
          return;
        }
        setTimeout(() => {
          this.getStartTask(task.id)
            .then((nextTask) => {
              if (!nextTask) {
                reject(new Error("Resume task not found"));
                return;
              }
              checkTask(nextTask);
            })
            .catch(reject);
        }, RESUME_POLL_INTERVAL_MS);
      };

      checkTask(initialTask);
    });
  }

  /**
   * Get a start task by ID
   * Poll this endpoint until status is READY to get the app_conversation_id
   *
   * @param taskId The task UUID
   * @returns AppConversationStartTask or null
   */
  static async getStartTask(
    taskId: string,
  ): Promise<V1AppConversationStartTask | null> {
    const { data } = await openHands.get<(V1AppConversationStartTask | null)[]>(
      `/api/v1/app-conversations/start-tasks?ids=${taskId}`,
    );

    return data[0] || null;
  }
}

export default V1ConversationService;
