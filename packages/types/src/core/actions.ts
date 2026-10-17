import { OpenHandsActionEvent } from "./base";
import { ActionSecurityRisk } from "./security";

export interface UserMessageAction extends OpenHandsActionEvent<"message"> {
  source: "user";
  args: {
    content: string;
    image_urls: string[];
  };
}

export interface SystemMessageAction extends OpenHandsActionEvent<"system"> {
  source: "agent";
  args: {
    content: string;
    tools: Array<Record<string, unknown>> | null;
    openhands_version: string | null;
    agent_class: string | null;
  };
}

export interface CommandAction extends OpenHandsActionEvent<"run"> {
  source: "agent" | "user";
  args: {
    command: string;
    safety_risk: ActionSafetyRisk;
    confirmation_state: "confirmed" | "rejected" | "awaiting_confirmation";
    thought: Thought;
    hidden?: boolean;
    reasoning_content?: string | null;
  };
}

export interface AssistantMessageAction
  extends OpenHandsActionEvent<"message"> {
  source: "agent";
  args: {
    thought: Thought;
    image_urls: string[] | null;
    wait_for_response: boolean;
    reasoning_content?: string | null;
  };
}

export interface IPythonAction extends OpenHandsActionEvent<"run_ipython"> {
  source: "agent";
  args: {
    code: string;
    safety_risk: ActionSafetyRisk;
    confirmation_state: "confirmed" | "rejected" | "awaiting_confirmation";
    kernel_init_code: string;
    thought: Thought;
  };
}

export interface ThinkAction extends OpenHandsActionEvent<"think"> {
  source: "agent";
  args: {
    thought: Thought;
  };
}

export interface FinishAction extends OpenHandsActionEvent<"finish"> {
  source: "agent";
  args: {
    final_thought: string;
    task_completed: "success" | "failure" | "partial";
    outputs: Record<string, unknown>;
    thought: Thought;
  };
}

export interface DelegateAction extends OpenHandsActionEvent<"delegate"> {
  source: "agent";
  timeout: number;
  args: {
    agent: "BrowsingAgent";
    inputs: Record<string, string>;
    thought: Thought;
  };
}

export interface BrowseAction extends OpenHandsActionEvent<"browse"> {
  source: "agent";
  args: {
    url: string;
    thought: Thought;
  };
}

export interface BrowseInteractiveAction
  extends OpenHandsActionEvent<"browse_interactive"> {
  source: "agent";
  timeout: number;
  args: {
    browser_actions: string;
    thought: Thought | null;
    browsergym_send_msg_to_user: string;
  };
}

export interface FileReadAction extends OpenHandsActionEvent<"read"> {
  source: "agent";
  args: {
    path: string;
    thought: string;
    safety_risk: ActionSafetyRisk | null;
    impl_source?: string;
    view_range?: number[] | null;
    reasoning_content?: string | null;
  };
}

export interface FileWriteAction extends OpenHandsActionEvent<"write"> {
  source: "agent";
  args: {
    path: string;
    content: string;
    thought: Thought;
  };
}

export interface FileEditAction extends OpenHandsActionEvent<"edit"> {
  source: "agent";
  args: {
    path: string;
    command?: string;
    file_text?: string | null;
    view_range?: number[] | null;
    old_str?: string | null;
    new_str?: string | null;
    insert_line?: number | null;
    content?: string;
    start?: number;
    end?: number;
    thought: string;
    safety_risk: ActionSafetyRisk | null;
    impl_source?: string;
    reasoning_content?: string | null;
  };
}

export interface RejectAction extends OpenHandsActionEvent<"reject"> {
  source: "agent";
  args: {
    thought: Thought;
  };
}

export interface TaskTrackingAction
  extends OpenHandsActionEvent<"task_tracking"> {
  source: "agent";
  args: {
    command: string;
    task_list: Array<{
      id: string;
      title: string;
      status: "todo" | "in_progress" | "done";
      notes?: string;
    }>;
    thought: string;
  };
}

export interface RecallAction extends OpenHandsActionEvent<"recall"> {
  source: "agent";
  args: {
    recall_type: "workspace_context" | "knowledge";
    query: string;
    thought: string;
  };
}

export type OpenHandsAction =
  | UserMessageAction
  | AssistantMessageAction
  | SystemMessageAction
  | CommandAction
  | IPythonAction
  | ThinkAction
  | FinishAction
  | DelegateAction
  | BrowseAction
  | BrowseInteractiveAction
  | FileReadAction
  | FileEditAction
  | FileWriteAction
  | RejectAction
  | RecallAction;
