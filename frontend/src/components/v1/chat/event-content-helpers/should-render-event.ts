import { OpenHandsEvent } from "#/types/v1/core";
import { MessageEvent } from "#/types/v1/core/events/message-event";
import {
  isActionEvent,
  isObservationEvent,
  isMessageEvent,
  isAgentErrorEvent,
  isConversationStateUpdateEvent,
} from "#/types/v1/type-guards";

// V1 events that should not be rendered
const NO_RENDER_ACTION_TYPES = [
  "ThinkAction",
  // Add more action types that should not be rendered
];

const NO_RENDER_OBSERVATION_TYPES = [
  "ThinkObservation",
  // Add more observation types that should not be rendered
];

export const shouldRenderEvent = (event: OpenHandsEvent) => {
  if (isConversationStateUpdateEvent(event)) {
    // A finished `/goal` loop renders inline so it settles into the
    // conversation; the live (active) banner is shown separately by
    // GoalStatusBanner, and all other state updates (and the in-progress goal
    // events) stay hidden.
    return isGoalConversationStateUpdateEvent(event) && !event.value.active;
  }

  // Render action events (with filtering)
  if (isActionEvent(event)) {
    // For V1, action is an object with kind property
    const actionType = event.action.kind;

    // Hide user commands from the chat interface
    if (actionType === "ExecuteBashAction" && event.source === "user") {
      return false;
    }

    return !NO_RENDER_ACTION_TYPES.includes(actionType);
  }

  // Render observation events (with filtering)
  if (isObservationEvent(event)) {
    // For V1, observation is an object with kind property
    const observationType = event.observation.kind;

    // Note: ObservationEvent source is always "environment", not "user"
    // So no need to check for user source here

    return !NO_RENDER_OBSERVATION_TYPES.includes(observationType);
  }

  // Render message events (user and assistant messages), except the goal loop's
  // injected re-prompts — the judge feedback they carry is shown in the goal
  // banner, so otherwise they leak into the chat as fake user turns.
  if (isMessageEvent(event)) {
    return !isGoalLoopReprompt(event);
  }

  // Render agent error events
  if (isAgentErrorEvent(event)) {
    return true;
  }

  // Don't render any other event types (system events, etc.)
  return false;
};

export const hasUserEvent = (events: OpenHandsEvent[]) =>
  events.some((event) => event.source === "user");
