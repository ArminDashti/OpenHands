import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import type { Message } from "#/message";

import { ActionSecurityRisk } from "#/state/security-analyzer-slice";
import {
  OpenHandsObservation,
  CommandObservation,
  IPythonObservation,
  RecallObservation,
} from "#/types/core/observations";
import { OpenHandsAction } from "#/types/core/actions";
import { OpenHandsEventType } from "#/types/core/base";
import { Message, ActionMessage, ErrorMessage } from "#/types/message";

type SliceState = {
  messages: Message[];
  systemMessage: {
    content: string;
    tools: Array<Record<string, unknown>> | null;
    openhands_version: string | null;
    agent_class: string | null;
  } | null;
};

const MAX_CONTENT_LENGTH = 1000;

const HANDLED_ACTIONS: OpenHandsEventType[] = [
  "run",
  "run_ipython",
  "write",
  "read",
  "browse",
  "edit",
  "user_feedback",
  "recall",
  "think",
  "system",
  "call_tool_mcp",
  "mcp",
];

function getRiskText(risk: ActionSecurityRisk) {
  switch (risk) {
    case ActionSecurityRisk.LOW:
      return "Low Risk";
    case ActionSecurityRisk.MEDIUM:
      return "Medium Risk";
    case ActionSecurityRisk.HIGH:
      return "High Risk";
    case ActionSecurityRisk.UNKNOWN:
    default:
      return "Unknown Risk";
  }
}

const initialState: SliceState = {
  messages: [],
  systemMessage: null,
};

export const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addUserMessage(
      state,
      action: PayloadAction<{
        content: string;
        imageUrls: string[];
        timestamp: string;
        pending?: boolean;
        isSystemMessage?: boolean;
      }>,
    ) {
      const message: Message = {
        type: "thought",
        sender: action.payload.isSystemMessage ? "system" : "user",
        content: action.payload.content,
        imageUrls: action.payload.imageUrls,
        timestamp: action.payload.timestamp || new Date().toISOString(),
        pending: !!action.payload.pending,
      };
      // Remove any pending messages
      let i = state.messages.length;
      while (i) {
        i -= 1;
        const m = state.messages[i] as Message;
        if (m.pending) {
          state.messages.splice(i, 1);
        }
      }
      state.messages.push(message);
    },

    addAssistantMessage(state: SliceState, action: PayloadAction<string>) {
      const message: Message = {
        type: "thought",
        sender: "assistant",
        content: action.payload,
        imageUrls: [],
        timestamp: new Date().toISOString(),
        pending: false,
      };
      state.messages.push(message);
    },

    addAssistantAction(
      state: SliceState,
      action: PayloadAction<OpenHandsAction>,
    ) {
      const actionID = action.payload.action;
      if (!HANDLED_ACTIONS.includes(actionID)) {
        return;
      }
      const translationID = `ACTION_MESSAGE$${actionID.toUpperCase()}`;
      let text = "";
      let filePath: string | undefined;
      if (actionID === "run") {
        text = `Command:\n\`${action.payload.args.command}\``;
      } else if (actionID === "run_ipython") {
        text = `\`\`\`\n${action.payload.args.code}\n\`\`\``;
      } else if (actionID === "write" || actionID === "edit") {
        let content = "";
        if ("content" in action.payload.args) {
          content = action.payload.args.content;
          if (content.length > MAX_CONTENT_LENGTH) {
            content = `${content.slice(0, MAX_CONTENT_LENGTH)}...`;
          }
        }
        text = `${action.payload.args.path}\n${content}`;
        filePath = action.payload.args.path;
      } else if (actionID === "browse") {
        text = `Browsing ${action.payload.args.url}`;
      }
      if (actionID === "run" || actionID === "run_ipython") {
        if (
          action.payload.args.confirmation_state === "awaiting_confirmation"
        ) {
          text += `\n\n${getRiskText(action.payload.args.security_risk as unknown as ActionSecurityRisk)}`;
        }
      } else if (actionID === "think") {
        text = action.payload.args.thought;
      }
      const message: ActionMessage = {
        type: "action",
        sender: "assistant",
        translationID,
        eventID: action.payload.id.toString(),
        content: text,
        imageUrls: [],
        timestamp: new Date().toISOString(),
        filePath,
        args: action.payload.args,
      };
      state.messages.push(message);
    },

    addAssistantObservation(
      state: SliceState,
      observation: PayloadAction<OpenHandsObservation>,
    ) {
      const observationID = observation.payload.observation;
      if (!HANDLED_ACTIONS.includes(observationID)) {
        return;
      }

      // Special handling for RecallObservation - create a new message instead of updating an existing one
      if (observationID === "recall") {
        const recallObs = observation.payload as RecallObservation;
        let content = ``;

        // Handle workspace context
        if (recallObs.extras.recall_type === "workspace_context") {
          if (recallObs.extras.repo_name) {
            content += `\n\n**Repository:** ${recallObs.extras.repo_name}`;
          }
          if (recallObs.extras.repo_directory) {
            content += `\n\n**Directory:** ${recallObs.extras.repo_directory}`;
          }
          if (recallObs.extras.date) {
            content += `\n\n**Date:** ${recallObs.extras.date}`;
          }
          if (
            recallObs.extras.runtime_hosts &&
            Object.keys(recallObs.extras.runtime_hosts).length > 0
          ) {
            content += `\n\n**MicroAgent: Available Hosts**`;
            for (const [host, port] of Object.entries(
              recallObs.extras.runtime_hosts,
            )) {
              content += `\n\n- ${host} (port ${port})`;
            }
          }
          if (recallObs.extras.repo_instructions) {
            content += `\n\n**Repository Instructions:**\n\n${recallObs.extras.repo_instructions}`;
          }
          if (recallObs.extras.additional_agent_instructions) {
            content += `\n\n**Additional Instructions:**\n\n${recallObs.extras.additional_agent_instructions}`;
          }
        }

        // Create a new message for the observation
        // Use the correct translation ID format that matches what's in the i18n file
        const translationID = `OBSERVATION_MESSAGE$${observationID.toUpperCase()}`;

        // Handle microagent knowledge and prepare custom title if needed
        let customTitle = translationID;
        if (
          recallObs.extras.microagent_knowledge &&
          recallObs.extras.microagent_knowledge.length > 0
        ) {
          // Extract microagent names for the title
          const microagentNames = recallObs.extras.microagent_knowledge
            .map((k) => k.name)
            .join(", ");

          // Create custom title with microagent names
          customTitle = `${translationID}: ${microagentNames}`;

          content += `\n\n**Triggered Microagent Knowledge:**`;
          for (const knowledge of recallObs.extras.microagent_knowledge) {
            content += `\n\n- **${knowledge.name}** (triggered by: ${knowledge.trigger})\n\n\`\`\`\n${knowledge.content}\n\`\`\``;
          }
        }

        const message: Message = {
          type: "action",
          sender: "assistant",
          translationID: customTitle,
          eventID: observation.payload.id,
          content,
          imageUrls: [],
          timestamp: new Date().toISOString(),
          success: true,
        };

        state.messages.push(message);
        return; // Skip the normal observation handling below
      }

      // Normal handling for other observation types
      const translationID = `OBSERVATION_MESSAGE$${observationID.toUpperCase()}`;
      const causeID = observation.payload.cause;
      const causeMessage = state.messages.find(
        (message) => message.eventID === causeID.toString(),
      ) as ActionMessage | undefined;
      if (!causeMessage) {
        return;
      }
      causeMessage.translationID = translationID;
      // Set success property based on observation type
      if (observationID === "run") {
        const commandObs = observation.payload as CommandObservation;
        // If exit_code is -1, it means the command timed out, so we set success to undefined
        // to not show any status indicator
        if (commandObs.extras.metadata.exit_code === -1) {
          causeMessage.success = undefined;
        } else {
          causeMessage.success = commandObs.extras.metadata.exit_code === 0;
        }
      } else if (observationID === "run_ipython") {
        // For IPython, we consider it successful if there's no error message
        const ipythonObs = observation.payload as IPythonObservation;
        causeMessage.success = !ipythonObs.content.includes("ERROR:\n");
      } else if (observationID === "read" || observationID === "edit") {
        // For read/edit operations, we consider it successful if there's content and no error

        if (observation.payload.extras.impl_source === "oh_aci") {
          causeMessage.success =
            observation.payload.content.length > 0 &&
            !observation.payload.content.startsWith("ERROR:\n");
        } else {
          causeMessage.success =
            observation.payload.content.length > 0 &&
            !observation.payload.content.toLowerCase().includes("error:");
        }
      }

      if (observationID === "run" || observationID === "run_ipython") {
        let { content } = observation.payload;
        if (content.length > MAX_CONTENT_LENGTH) {
          content = `${content.slice(0, MAX_CONTENT_LENGTH)}...`;
        }
        content = `${
          causeMessage.content
        }\n\nOutput:\n\`\`\`\n${content.trim() || "[Command finished execution with no output]"}\n\`\`\``;
        causeMessage.content = content; // Observation content includes the action
      } else if (observationID === "read") {
        causeMessage.content = `\`\`\`\n${observation.payload.content}\n\`\`\``; // Content is already truncated by the ACI
      } else if (observationID === "edit") {
        if (causeMessage.success) {
          causeMessage.content = `\`\`\`diff\n${observation.payload.extras.diff}\n\`\`\``; // Content is already truncated by the ACI
        } else {
          causeMessage.content = observation.payload.content;
        }
      } else if (observationID === "browse") {
        let content = `**URL:** ${observation.payload.extras.url}\n`;
        if (observation.payload.extras.error) {
          content += `**Error:**\n${observation.payload.extras.error}\n`;
        }
        content += `**Output:**\n${observation.payload.content}`;
        if (content.length > MAX_CONTENT_LENGTH) {
          content = `${content.slice(0, MAX_CONTENT_LENGTH)}...`;
        }
        causeMessage.content = content;
        // RecallObservation is now handled at the beginning of the function
      }
    },

    addErrorMessage(
      state: SliceState,
      action: PayloadAction<{
        id?: string;
        message: string;
        content: string;
        type: "error";
        sender: "assistant";
        timestamp: string;
      }>,
    ) {
      const { id, content, type, sender, timestamp } = action.payload;
      const errorMessage: ErrorMessage = {
        translationID: id,
        content,
        type,
        sender,
        timestamp,
        id,
      };
      state.messages.push(errorMessage);
    },

    clearMessages(state: SliceState) {
      state.messages = [];
      state.systemMessage = null;
    },

    setMessageFeedback(
      state: SliceState,
      action: PayloadAction<{
        messageId: number;
        feedbackType: "positive" | "negative";
      }>,
    ) {
      const { messageId, feedbackType } = action.payload;
      const messageIndex = state.messages.findIndex(
        (message) => message.eventID === messageId,
      );
      if (messageIndex !== -1) {
        state.messages[messageIndex].feedback = feedbackType;
      }
    },
  },
});

export const {
  addUserMessage,
  addAssistantMessage,
  addAssistantAction,
  addAssistantObservation,
  addErrorMessage,
  clearMessages,
  setMessageFeedback,
} = chatSlice.actions;

// Selectors
export const selectSystemMessage = (state: { chat: SliceState }) =>
  state.chat.systemMessage;

export default chatSlice.reducer;
