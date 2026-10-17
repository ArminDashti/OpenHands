import {
  ActionEvent,
  ExecutionStatus,
  ImageContent,
  OpenHandsEvent,
  TextContent,
} from "#/types/agent-server/core";
import { ConversationStateUpdateEvent } from "#/types/agent-server/core/events/conversation-state-event";
import {
  getExecutionStatusFromConversationStateUpdate,
  isACPToolCallEvent,
  isActionEvent,
  isConversationStateUpdateEvent,
  isMessageEvent,
  isObservationEvent,
  isStreamingDeltaEvent,
} from "#/types/agent-server/type-guards";
import { StreamingDeltaEvent } from "#/types/agent-server/core/events/streaming-delta-event";
import type {
  DeltaFrame,
  ItemStartedFrame,
} from "#/types/agent-server/session-frames";

/**
 * An event as held by the UI list. `seq` is the log index a `durable` frame
 * carried; slots and transient events have none, which is what makes "has a
 * seq" mean "is resumable".
 */
export type UIEvent = OpenHandsEvent & {
  isFromPlanningAgent?: boolean;
  seq?: number;
};

export interface StreamingSlotMeta {
  isFromPlanningAgent?: boolean;
}

const isUserMessage = (event: OpenHandsEvent): boolean =>
  isMessageEvent(event) && event.source === "user";

const reportsAgentLeftRunning = (
  event: ConversationStateUpdateEvent,
): boolean => {
  const status = getExecutionStatusFromConversationStateUpdate(event);
  return status !== null && status !== ExecutionStatus.RUNNING;
};

// A mid-stream user message and a still-RUNNING state snapshot are transparent:
// the deltas either side of them are one bubble. A snapshot that left RUNNING
// ends the run, keeping an interrupted turn's deltas out of the next turn (#1899).
//
// `sender` scopes the check to one agent's run: the main and planning sockets
// share this event store, so a status update sourced from the *other* socket
// says nothing about whether this sender's run ended — it's transparent too
// (#1656). Every caller threads its sender through so an unrelated socket's
// terminal status update never closes a boundary that belongs to a
// different, still-streaming sender.
//
// KNOWN GAP: this still assumes the closing ConversationStateUpdateEvent
// always arrives. If a stream is abandoned with no closing event (dropped
// connection that never recovers, backend crash) its dangling delta stays
// "open" and can be merged into an unrelated later turn. There's no reliable
// signal in this codebase today for "this stream is permanently dead" as
// opposed to "still retrying" (the main socket reconnects with unlimited
// attempts and replays the backlog by design, so closing on every `onclose`
// would reintroduce bubble-splitting on ordinary reconnects). Needs its own
// design work, not a mechanical fix here.
const endsStreamingRun = (
  event: OpenHandsEvent & { isFromPlanningAgent?: boolean },
  sender: OpenHandsEvent & { isFromPlanningAgent?: boolean },
): boolean => {
  if (isUserMessage(event)) {
    return false;
  }
  if (isConversationStateUpdateEvent(event)) {
    if (!isSameStreamingSender(sender, event)) {
      return false;
    }
    return reportsAgentLeftRunning(event);
  }
  return true;
};

const findTrailingStreamStart = (
  events: OpenHandsEvent[],
  sender: OpenHandsEvent & { isFromPlanningAgent?: boolean },
): number => {
  let start = events.length;
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (isStreamingDeltaEvent(event)) {
      // Sender-scoped, like `findTrailingStreamLastDeltaIndex`: the main and
      // planning sockets share this event store, so another sender's delta is
      // transparent here too (#1656). Without the check it drags `start` back
      // past a genuine turn boundary, `findLastUserMessageIndex` then reports
      // the *previous* turn's user message, and the finalized reply both
      // strips that turn's streamed text and renders above the question the
      // current turn actually answered.
      if (isSameStreamingSender(sender, event)) {
        start = index;
      }
    } else if (endsStreamingRun(event, sender)) {
      break;
    }
  }
  return start;
};

// The last delta of the trailing streaming run belonging to `sender`, or -1
// when the tail is not one. A different sender's delta is transparent — the
// main and planning sockets share this event store (#1656) — so scanning
// continues past it instead of stopping there.
const findTrailingStreamLastDeltaIndex = (
  events: OpenHandsEvent[],
  sender: OpenHandsEvent & { isFromPlanningAgent?: boolean },
): number => {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (isStreamingDeltaEvent(event)) {
      if (isSameStreamingSender(sender, event)) {
        return index;
      }
      continue;
    }
    if (endsStreamingRun(event, sender)) {
      break;
    }
  }
  return -1;
};

// One past the trailing run's last delta — where its final event belongs.
const findTrailingStreamEnd = (
  events: OpenHandsEvent[],
  sender: OpenHandsEvent & { isFromPlanningAgent?: boolean },
): number => {
  const lastDeltaIndex = findTrailingStreamLastDeltaIndex(events, sender);
  return lastDeltaIndex === -1 ? events.length : lastDeltaIndex + 1;
};

// The current turn's boundary: the last user message not sent mid-stream.
const findLastUserMessageIndex = (
  events: OpenHandsEvent[],
  sender: OpenHandsEvent & { isFromPlanningAgent?: boolean },
): number => {
  for (
    let index = findTrailingStreamStart(events, sender) - 1;
    index >= 0;
    index -= 1
  ) {
    if (isUserMessage(events[index])) {
      return index;
    }
  }
  return -1;
};

// The delta bubble an incoming delta merges into: the trailing run's last delta
// from the same sender, looking past a mid-stream user message so it doesn't
// split the reply (#1899).
const findStreamingMergeTargetIndex = (
  uiEvents: OpenHandsEvent[],
  incoming: StreamingDeltaEvent,
): number => findTrailingStreamLastDeltaIndex(uiEvents, incoming);

// Join text blocks WITHOUT a separator: streaming deltas concatenate content
// tokens directly with no separator between LLM content blocks, so using "\n"
// here would cause startsWith/findTextSegmentsInOrder to miss when reconciling
// a multi-block message/thought against the already-rendered streaming delta.
const joinTextBlocks = (blocks: (TextContent | ImageContent)[]): string =>
  blocks
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("");

const findTextSegmentsInOrder = (
  text: string,
  segments: string[],
): { matched: boolean; lastMatchEnd: number } => {
  let searchStart = 0;
  let lastMatchEnd = 0;

  for (const segment of segments) {
    const index = text.indexOf(segment, searchStart);
    if (index === -1) {
      return { matched: false, lastMatchEnd };
    }
    lastMatchEnd = index + segment.length;
    searchStart = lastMatchEnd;
  }

  return { matched: true, lastMatchEnd };
};

// Content-bearing streaming deltas of the current turn (after the last user
// message) that share the final event's sender. Reasoning-only deltas are
// excluded: reasoning renders in its own collapsed bubble and never overlaps
// the message text being reconciled. Sender scoping matters because the main
// and planning sockets share this event store — without it, one agent's final
// event would strip the other agent's still-live streamed deltas (#1656).
const getCurrentTurnContentDeltas = (
  uiEvents: OpenHandsEvent[],
  finalEvent: OpenHandsEvent,
): { event: StreamingDeltaEvent; index: number }[] => {
  const lastUserMessageIndex = findLastUserMessageIndex(uiEvents, finalEvent);
  return uiEvents
    .map((event, index) => ({ event, index }))
    .filter(
      (item): item is { event: StreamingDeltaEvent; index: number } =>
        item.index > lastUserMessageIndex &&
        isStreamingDeltaEvent(item.event) &&
        (item.event.content?.length ?? 0) > 0 &&
        isSameStreamingSender(finalEvent, item.event),
    );
};

// The current step's streaming delta(s): the trailing run at the end of
// `uiEvents`. Earlier steps' deltas are separated by their observations, so
// this never folds an earlier step's delta into the current one.
const getTrailingDeltas = (
  uiEvents: OpenHandsEvent[],
  selects: (event: StreamingDeltaEvent) => boolean,
  sender: OpenHandsEvent & { isFromPlanningAgent?: boolean },
): { event: StreamingDeltaEvent; index: number }[] => {
  const deltas: { event: StreamingDeltaEvent; index: number }[] = [];
  for (let index = uiEvents.length - 1; index >= 0; index -= 1) {
    const event = uiEvents[index];
    if (!isStreamingDeltaEvent(event)) {
      // A mid-stream user message / RUNNING snapshot doesn't end the run (#1899).
      if (!endsStreamingRun(event, sender)) {
        continue;
      }
      break;
    }
    if (selects(event)) {
      deltas.unshift({ event, index });
    }
  }
  return deltas;
};

// Sender-scoped: the main and planning sockets share this event store, so a
// main-agent action must not strip the planning agent's live streamed text
// or reasoning (#1656).
const getTrailingContentDeltas = (
  uiEvents: OpenHandsEvent[],
  sender: OpenHandsEvent & { isFromPlanningAgent?: boolean },
) =>
  getTrailingDeltas(
    uiEvents,
    (event) =>
      (event.content?.length ?? 0) > 0 && isSameStreamingSender(sender, event),
    sender,
  );

const getTrailingReasoningDeltas = (
  uiEvents: OpenHandsEvent[],
  finalEvent: OpenHandsEvent,
) =>
  getTrailingDeltas(
    uiEvents,
    (event) =>
      Boolean(event.reasoning_content) &&
      isSameStreamingSender(finalEvent, event),
    finalEvent,
  );

// Strip the streamed content deltas, keeping a delta only when it carries
// reasoning the replacement itself won't render (many models stream reasoning
// solely through the delta). Shared by the finalize and intermediate-action
// reconciliation paths.
const supersedeStreamingContent = (
  uiEvents: OpenHandsEvent[],
  contentDeltas: { event: StreamingDeltaEvent; index: number }[],
  replacementRendersReasoning: boolean,
): OpenHandsEvent[] => {
  const indexesToStrip = new Set(contentDeltas.map(({ index }) => index));
  const nextUiEvents: OpenHandsEvent[] = [];
  uiEvents.forEach((event, index) => {
    if (!indexesToStrip.has(index) || !isStreamingDeltaEvent(event)) {
      nextUiEvents.push(event);
      return;
    }

    // Keep the delta only to render reasoning the replacement itself lacks.
    if (!replacementRendersReasoning && event.reasoning_content) {
      nextUiEvents.push({ ...event, content: null });
    }
  });
  return nextUiEvents;
};

/** The anchor event itself, or the nearest earlier event from the same socket. */
const findAnchor = (
  uiEvents: UIEvent[],
  anchorSeq: number | null | undefined,
  isFromPlanningAgent: boolean,
  insertIndex: number,
): UIEvent | undefined => {
  if (anchorSeq !== null && anchorSeq !== undefined) {
    const exact = uiEvents.find(
      (event) =>
        event.seq === anchorSeq && isSameSocket(event, isFromPlanningAgent),
    );
    if (exact) {
      return exact;
    }
  }

  return false;
};

// The final MessageEvent/FinishAction is authoritative for the turn's text. Drop
// the provisional streamed deltas and render the canonical final event instead,
// so the message is rendered exactly once (never holey or duplicated) and its
// metadata — critic_result, activated_skills — renders too. Stream-only
// reasoning is preserved. Returns null when there is no streamed content to
// reconcile, leaving the caller to append the final event normally.
const finalizeStreamingDeltasInPlace = (
  finalEvent: OpenHandsEvent,
  uiEvents: OpenHandsEvent[],
): OpenHandsEvent[] | null => {
  const contentStreamingDeltas = getCurrentTurnContentDeltas(
    uiEvents,
    finalEvent,
  );

  // Render the final event where the stream ended, not at the tail, so it stays
  // above a message the user sent mid-stream instead of jumping below it (#1899).
  // Scoped to `finalEvent`'s sender so an interleaved planning-agent delta
  // doesn't push it past the point where its own stream actually ended (#1656).
  const streamEnd = findTrailingStreamEnd(uiEvents, finalEvent);

  if (contentStreamingDeltas.length === 0) {
    // Nothing streamed to supersede — but the placement still matters. Models
    // that stream only `reasoning_content` produce no content deltas at all,
    // so returning null here appended the reply at the tail and dropped it
    // below the message the user sent while the reasoning bubble was already
    // on screen. `streamEnd === uiEvents.length` means nothing trails the run
    // (or there was no run), which is the genuine "just append" case.
    if (streamEnd >= uiEvents.length) {
      return null;
    }
    return [
      ...uiEvents.slice(0, streamEnd),
      finalEvent,
      ...uiEvents.slice(streamEnd),
    ];
  }

  const nextUiEvents = supersedeStreamingContent(
    uiEvents.slice(0, streamEnd),
    contentStreamingDeltas,
    eventRendersReasoning(finalEvent),
  );
  nextUiEvents.push(finalEvent);
  return [...nextUiEvents, ...uiEvents.slice(streamEnd)];
};

/**
 * Open (or re-open, for a higher attempt) the slot an `item_started` frame
 * announces. A lower or equal attempt is ignored.
 */
export const openStreamingSlot = (
  frame: ItemStartedFrame,
  uiEvents: UIEvent[],
  meta: StreamingSlotMeta = {},
): UIEvent[] => {
  const attempt = frame.attempt ?? 1;
  const existingIndex = findSlotIndex(uiEvents, frame.item_id);

  if (existingIndex !== -1) {
    const slot = uiEvents[existingIndex] as StreamingDeltaEvent;
    // Only a higher attempt supersedes; a repeat of the current one is a no-op.
    if (attemptOf(slot) >= attempt) {
      return uiEvents;
    }
    const next = [...uiEvents];
    next[existingIndex] = {
      ...slot,
      attempt,
      content: null,
      reasoning_content: null,
    };
    return next;
  }

  const isFromPlanningAgent = Boolean(meta.isFromPlanningAgent);
  const insertIndex = slotInsertIndex(
    uiEvents,
    frame.anchor_seq,
    isFromPlanningAgent,
  );
  // Borrow the anchor's timestamp so the store's timestamp sort — which fires
  // whenever durable frames arrive out of order, as they routinely do — keeps
  // the slot right after it. Prefer the anchor event itself: a neighbour may be
  // a client-stamped event whose clock does not match the server's.
  const anchor = findAnchor(
    uiEvents,
    frame.anchor_seq,
    isFromPlanningAgent,
    insertIndex,
  );
  const slot: StreamingDeltaEvent & StreamingSlotMeta = {
    kind: "StreamingDeltaEvent",
    id: frame.item_id,
    source: "agent",
    timestamp:
      anchor && "timestamp" in anchor && anchor.timestamp
        ? anchor.timestamp
        : new Date().toISOString(),
    content: null,
    reasoning_content: null,
    attempt,
    ...meta,
  };

  const next = [...uiEvents];
  next.splice(insertIndex, 0, slot);
  return next;
};

/**
 * Append a batch of `delta` frames to their slots.
 *
 * A delta with no open slot opens one: its `item_started` went by before this
 * socket connected (progress frames are never replayed) — which is the normal
 * case for the first reply of a conversation started from the home page, since
 * the socket waits for the history load. This cannot orphan a bubble: slots
 * and buffered deltas are discarded on connect and disconnect, so the delta is
 * live on this connection, and the server retires every stream on it. The one
 * race — a delta overtaken by its own durable event, which travels a different
 * fan-out — is closed by `isFinished`.
 */
export const appendStreamingDeltas = (
  frames: DeltaFrame[],
  uiEvents: UIEvent[],
  {
    isFinished = () => false,
    ...meta
  }: StreamingSlotMeta & { isFinished?: (itemId: string) => boolean } = {},
): UIEvent[] => {
  let next = uiEvents;
  let copied = false;

  for (const frame of frames) {
    let index = findSlotIndex(next, frame.item_id);
    if (index === -1) {
      if (isFinished(frame.item_id)) {
        continue;
      }
      next = openStreamingSlot(
        {
          type: "item_started",
          item_id: frame.item_id,
          attempt: frame.attempt,
        },
        next,
        meta,
      );
      copied = true;
      index = findSlotIndex(next, frame.item_id);
    }
    const slot = next[index] as StreamingDeltaEvent;
    const attempt = frame.attempt ?? 1;
    if (attempt < attemptOf(slot)) {
      continue;
    }
    // A higher attempt re-streams the item, so the old tail is superseded.
    const superseded = attempt > attemptOf(slot);
    const content = superseded ? "" : (slot.content ?? "");
    const reasoning = superseded ? "" : (slot.reasoning_content ?? "");
    const isReasoning = frame.kind === "reasoning";

    if (!copied) {
      next = [...next];
      copied = true;
    }
    next[index] = {
      ...slot,
      attempt,
      content: (isReasoning ? content : content + frame.content) || null,
      reasoning_content:
        (isReasoning ? reasoning + frame.content : reasoning) || null,
    };
  }

  return next;
};

/**
 * Drop the slot for `itemId`. Used by `item_aborted`: the stream ended without
 * a durable event, so nothing is coming to supersede the provisional text.
 */
export const abortStreamingSlot = (
  itemId: string,
  uiEvents: UIEvent[],
  attempt?: number,
): UIEvent[] => {
  const index = findSlotIndex(uiEvents, itemId);
  if (index === -1) {
    return uiEvents;
  }
  // An abort for a superseded attempt must not delete the live retry's slot.
  if (
    attempt !== undefined &&
    attempt < attemptOf(uiEvents[index] as StreamingDeltaEvent)
  ) {
    return uiEvents;
  }
  return uiEvents.filter((_, position) => position !== index);
};

/**
 * Drop every open slot for one socket. Called on connect and disconnect:
 * progress frames are never replayed, so an open slot cannot survive the gap,
 * and the message it was standing in for arrives on the durable cursor.
 */
export const clearStreamingSlots = (
  uiEvents: UIEvent[],
  isFromPlanningAgent = false,
): UIEvent[] => {
  const next = uiEvents.filter(
    (event) =>
      !isStreamingDeltaEvent(event) ||
      !isSameSocket(event as UIEvent, isFromPlanningAgent),
  );
  return next.length === uiEvents.length ? uiEvents : next;
};

/**
 * Handles adding an event to the UI events array
 * Replaces actions with observations when they arrive (so UI shows observation instead of action)
 * Exception: ThinkAction is NOT replaced because the thought content is in the action, not in the observation
 *
 * ACPToolCallEvent merge: the SDK emits two events per ``tool_call_id`` — an
 * early ``started`` event (``pending`` / ``in_progress``) and one terminal
 * (completed / failed) event, the action->observation pair for a tool call.
 * Replace the started entry in place with the terminal one so a single card
 * updates from running to its result, exactly like an observation superseding
 * its action below.
 */
export const handleEventForUI = (
  event: UIEvent,
  uiEvents: UIEvent[],
): UIEvent[] => {
  const newUiEvents = [...uiEvents];

  // The durable event *is* the item: the SDK mints its id when the stream
  // opens, so one equality test retires the slot — and replacing in place
  // keeps the finished message where the streamed text already was.
  const eventId = "id" in event ? event.id : undefined;
  if (eventId !== undefined) {
    const slotIndex = findSlotIndex(newUiEvents, eventId);
    if (slotIndex !== -1) {
      newUiEvents[slotIndex] = event;
      return newUiEvents;
    }

    const mergeIndex = findStreamingMergeTargetIndex(newUiEvents, event);
    if (mergeIndex !== -1) {
      newUiEvents[mergeIndex] = mergeStreamingDeltaEvent(
        event,
        newUiEvents[mergeIndex] as StreamingDeltaEvent,
      );
      return newUiEvents;
    }

    newUiEvents.push(event);
    return newUiEvents;
  }

  if (
    (isActionEvent(event) && event.action.kind === "FinishAction") ||
    (isMessageEvent(event) && event.source === "agent")
  ) {
    const finalizedUiEvents = finalizeStreamingDeltasInPlace(
      event,
      newUiEvents,
    );
    if (finalizedUiEvents) {
      return finalizedUiEvents;
    }
  }

  // Intermediate tool-calling action whose thought was streamed: clear the
  // duplicated text from the delta (issue #1534). ThinkAction is excluded — its
  // thought renders through its own collapsible, not a hoisted thought.
  if (
    isActionEvent(event) &&
    event.action.kind !== "FinishAction" &&
    event.action.kind !== "ThinkAction"
  ) {
    // Place the action where its stream ended rather than at the tail, for the
    // same reason as `finalizeStreamingDeltasInPlace`: `group-events.ts` hoists
    // the action's thought into its own message, so appending it below a
    // mid-stream user message reintroduces exactly the jump this fixes — and
    // tool-calling steps are the bulk of a run, not an edge case (#1899).
    // Reconciling within the head keeps the superseded delta indexes valid.
    const streamEnd = findTrailingStreamEnd(newUiEvents, event);
    const head = newUiEvents.slice(0, streamEnd);
    const tail = newUiEvents.slice(streamEnd);
    const reconciledHead =
      supersedeStreamedThoughtWithAction(event, head) ??
      supersedeStreamedReasoningWithAction(event, head);
    if (reconciledHead) {
      reconciledHead.push(event);
      return [...reconciledHead, ...tail];
    }
  }

  if (isACPToolCallEvent(event)) {
    const existingIndex = newUiEvents.findIndex(
      (uiEvent) =>
        isACPToolCallEvent(uiEvent) &&
        uiEvent.tool_call_id === event.tool_call_id,
    );
    if (existingIndex !== -1) {
      newUiEvents[existingIndex] = event;
    } else {
      newUiEvents.push(event);
    }
    return newUiEvents;
  }

  if (isObservationEvent(event)) {
    // Don't add ThinkObservation at all - we keep the ThinkAction instead
    // The thought content is in the action, not the observation
    if (event.observation.kind === "ThinkObservation") {
      return newUiEvents;
    }

    // Don't add FinishObservation at all - we keep the FinishAction instead
    // Both contain the same message content, so we only need to display one
    // This also prevents duplicate messages when events arrive out of order due to React batching
    if (event.observation.kind === "FinishObservation") {
      return newUiEvents;
    }

    // Find and replace the corresponding action from uiEvents
    const actionIndex = newUiEvents.findIndex(
      (uiEvent) => uiEvent.id === event.action_id,
    );
    if (actionIndex !== -1) {
      newUiEvents[actionIndex] = event;
    } else {
      // Action not found in uiEvents, just add the observation
      newUiEvents.push(event);
    }
  } else {
    // For non-observation events, just add them to uiEvents
    newUiEvents.push(event);
  }

  return newUiEvents;
};
