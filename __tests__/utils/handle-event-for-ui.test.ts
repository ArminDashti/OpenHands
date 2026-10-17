import { describe, expect, it } from "vitest";
import {
  ActionEvent,
  ObservationEvent,
  MessageEvent,
  SecurityRisk,
  OpenHandsEvent,
} from "#/types/agent-server/core";
import { ACPToolCallEvent } from "#/types/agent-server/core/events/acp-tool-call-event";
import { StreamingDeltaEvent } from "#/types/agent-server/core/events/streaming-delta-event";
import { handleEventForUI } from "#/utils/handle-event-for-ui";
import {
  makeExecutionStatusUpdate,
  makeFullStateSnapshot,
} from "../helpers/conversation-state-update-fixtures";

describe("handleEventForUI", () => {
  const mockObservationEvent: ObservationEvent = {
    id: "test-observation-1",
    timestamp: Date.now().toString(),
    source: "environment",
    tool_name: "execute_bash",
    tool_call_id: "call_123",
    observation: {
      kind: "ExecuteBashObservation",
      content: [{ type: "text", text: "hello\n" }],
      command: "echo hello",
      exit_code: 0,
      error: false,
      timeout: false,
      metadata: {
        exit_code: 0,
        pid: 12345,
        username: "user",
        hostname: "localhost",
        working_dir: "/home/user",
        py_interpreter_path: null,
        prefix: "",
        suffix: "",
      },
    },
    action_id: "test-action-1",
  };

  const mockActionEvent: ActionEvent = {
    id: "test-action-1",
    timestamp: Date.now().toString(),
    source: "agent",
    thought: [{ type: "text", text: "I need to execute a bash command" }],
    thinking_blocks: [],
    action: {
      kind: "ExecuteBashAction",
      command: "echo hello",
      is_input: false,
      timeout: null,
      reset: false,
    },
    tool_name: "execute_bash",
    tool_call_id: "call_123",
    tool_call: {
      id: "call_123",
      type: "function",
      function: {
        name: "execute_bash",
        arguments: '{"command": "echo hello"}',
      },
    },
    llm_response_id: "response_123",
    security_risk: SecurityRisk.UNKNOWN,
  };

  const mockMessageEvent: MessageEvent = {
    id: "test-event-1",
    timestamp: Date.now().toString(),
    source: "user",
    llm_message: {
      role: "user",
      content: [{ type: "text", text: "Hello, world!" }],
    },
    activated_skills: [],
    extended_content: [],
  };

  const mockFinishActionEvent: ActionEvent = {
    id: "test-finish-action-1",
    timestamp: Date.now().toString(),
    source: "agent",
    thought: [],
    thinking_blocks: [],
    action: {
      kind: "FinishAction",
      message: "I'll start working on that. Done.",
    },
    tool_name: "finish",
    tool_call_id: "call_finish_1",
    tool_call: {
      id: "call_finish_1",
      type: "function",
      function: {
        name: "finish",
        arguments: JSON.stringify({
          message: "I'll start working on that. Done.",
        }),
      },
    },
    llm_response_id: "response_finish",
    security_risk: SecurityRisk.UNKNOWN,
  };

  const mockAgentMessageEvent: MessageEvent = {
    id: "test-agent-message-1",
    timestamp: Date.now().toString(),
    source: "agent",
    llm_message: {
      role: "assistant",
      content: [{ type: "text", text: "I'll start working on that. Done." }],
    },
    activated_skills: [],
    extended_content: [],
  };

  const makeStreamingDelta = (
    id: string,
    content: string | null,
  ): StreamingDeltaEvent => ({
    id,
    kind: "StreamingDeltaEvent",
    timestamp: Date.now().toString(),
    source: "agent",
    content,
    reasoning_content: null,
  });

  it("should add non-observation events to the end of uiEvents", () => {
    const initialUiEvents = [mockMessageEvent];
    const result = handleEventForUI(mockActionEvent, initialUiEvents);

    expect(result).toEqual([mockMessageEvent, mockActionEvent]);
    expect(result).not.toBe(initialUiEvents); // Should return a new array
  });

  it("should replace corresponding action with observation when action exists", () => {
    const initialUiEvents = [mockMessageEvent, mockActionEvent];
    const result = handleEventForUI(mockObservationEvent, initialUiEvents);

    expect(result).toEqual([mockMessageEvent, mockObservationEvent]);
    expect(result).not.toBe(initialUiEvents); // Should return a new array
  });

  it("should add observation to end when corresponding action is not found", () => {
    const initialUiEvents = [mockMessageEvent];
    const result = handleEventForUI(mockObservationEvent, initialUiEvents);

    expect(result).toEqual([mockMessageEvent, mockObservationEvent]);
    expect(result).not.toBe(initialUiEvents); // Should return a new array
  });

  it("should handle empty uiEvents array", () => {
    const initialUiEvents: OpenHandsEvent[] = [];
    const result = handleEventForUI(mockObservationEvent, initialUiEvents);

    expect(result).toEqual([mockObservationEvent]);
    expect(result).not.toBe(initialUiEvents); // Should return a new array
  });

  it("should not mutate the original uiEvents array", () => {
    const initialUiEvents = [mockMessageEvent, mockActionEvent];
    const originalLength = initialUiEvents.length;
    const originalFirstEvent = initialUiEvents[0];

    handleEventForUI(mockObservationEvent, initialUiEvents);

    expect(initialUiEvents).toHaveLength(originalLength);
    expect(initialUiEvents[0]).toBe(originalFirstEvent);
    expect(initialUiEvents[1]).toBe(mockActionEvent); // Should not be replaced
  });

  it("should replace the correct action when multiple actions exist", () => {
    const anotherActionEvent: ActionEvent = {
      ...mockActionEvent,
      id: "test-action-2",
    };

    const initialUiEvents = [
      mockMessageEvent,
      mockActionEvent,
      anotherActionEvent,
    ];
    const result = handleEventForUI(mockObservationEvent, initialUiEvents);

    expect(result).toEqual([
      mockMessageEvent,
      mockObservationEvent,
      anotherActionEvent,
    ]);
  });

  it("should NOT replace ThinkAction with ThinkObservation", () => {
    const mockThinkAction: ActionEvent = {
      id: "test-think-action-1",
      timestamp: Date.now().toString(),
      source: "agent",
      thought: [{ type: "text", text: "I am thinking..." }],
      thinking_blocks: [],
      action: {
        kind: "ThinkAction",
        thought: "I am thinking...",
      },
      tool_name: "think",
      tool_call_id: "call_think_1",
      tool_call: {
        id: "call_think_1",
        type: "function",
        function: {
          name: "think",
          arguments: "",
        },
      },
      llm_response_id: "response_think",
      security_risk: SecurityRisk.UNKNOWN,
    };

    const mockThinkObservation: ObservationEvent = {
      id: "test-think-observation-1",
      timestamp: Date.now().toString(),
      source: "environment",
      tool_name: "think",
      tool_call_id: "call_think_1",
      observation: {
        kind: "ThinkObservation",
        content: [{ type: "text", text: "Your thought has been logged." }],
      },
      action_id: "test-think-action-1",
    };

    const initialUiEvents = [mockMessageEvent, mockThinkAction];
    const result = handleEventForUI(mockThinkObservation, initialUiEvents);

    // ThinkObservation should NOT be added - ThinkAction should remain
    expect(result).toEqual([mockMessageEvent, mockThinkAction]);
    expect(result).not.toBe(initialUiEvents);
  });

  describe("ACPToolCallEvent dedup", () => {
    const mockInProgress: ACPToolCallEvent = {
      kind: "ACPToolCallEvent",
      id: "acp-evt-1",
      timestamp: "2026-04-16T19:32:29.828069",
      source: "agent",
      tool_call_id: "toolu_ABC",
      title: "gh pr diff 490",
      tool_kind: "execute",
      status: "in_progress",
      raw_input: { command: "gh pr diff 490" },
      raw_output: null,
      content: null,
      is_error: false,
    };

    const mockCompleted: ACPToolCallEvent = {
      ...mockInProgress,
      id: "acp-evt-2",
      status: "completed",
      raw_output: "output text",
    };

    it("appends the first tool call for a new tool_call_id", () => {
      const result = handleEventForUI(mockInProgress, [mockMessageEvent]);

      expect(result).toEqual([mockMessageEvent, mockInProgress]);
    });

    it("replaces a later status event at the original position", () => {
      const result = handleEventForUI(mockCompleted, [
        mockMessageEvent,
        mockInProgress,
      ]);

      expect(result).toEqual([mockMessageEvent, mockCompleted]);
    });

    it("leaves tool calls with different tool_call_ids untouched", () => {
      const other: ACPToolCallEvent = {
        ...mockInProgress,
        id: "acp-evt-99",
        tool_call_id: "toolu_XYZ",
        title: "ls -la",
      };
      const result = handleEventForUI(mockCompleted, [
        mockMessageEvent,
        other,
        mockInProgress,
      ]);

      expect(result).toEqual([mockMessageEvent, other, mockCompleted]);
    });
  });

  describe("streaming slots", () => {
    const started = (
      itemId: string,
      extra: Partial<ItemStartedFrame> = {},
    ): ItemStartedFrame => ({
      type: "item_started",
      item_id: itemId,
      attempt: 1,
      ...extra,
    });

    const delta = (
      itemId: string,
      content: string,
      extra: Partial<DeltaFrame> = {},
    ): DeltaFrame => ({
      type: "delta",
      item_id: itemId,
      attempt: 1,
      order: 0,
      kind: "text",
      content,
      ...extra,
    });

    const slotsOf = (events: OpenHandsEvent[]) =>
      events.filter((event): event is StreamingDeltaEvent =>
        isStreamingDeltaEvent(event),
      );

    it("opens a slot keyed by item_id and accumulates its deltas", () => {
      const opened = openStreamingSlot(started("item-1"), [mockMessageEvent]);
      const result = appendStreamingDeltas(
        [delta("item-1", "I'll start "), delta("item-1", "working on that.")],
        opened,
      );

      expect(slotsOf(result)).toHaveLength(1);
      expect(slotsOf(result)[0]).toMatchObject({
        id: "item-1",
        content: "I'll start working on that.",
        reasoning_content: null,
      });
    });

    it("routes reasoning deltas to reasoning_content, independently of text", () => {
      const opened = openStreamingSlot(started("item-1"), []);
      const result = appendStreamingDeltas(
        [
          delta("item-1", "thinking", { kind: "reasoning" }),
          delta("item-1", "answer"),
          delta("item-1", " more", { kind: "reasoning" }),
        ],
        opened,
      );

      expect(slotsOf(result)[0]).toMatchObject({
        content: "answer",
        reasoning_content: "thinking more",
      });
    });

    it("retires the slot when the durable event carries its id", () => {
      const opened = openStreamingSlot(started("test-agent-message-1"), [
        mockMessageEvent,
      ]);
      const streamed = appendStreamingDeltas(
        [delta("test-agent-message-1", "partial text")],
        opened,
      );

      const result = handleEventForUI(mockAgentMessageEvent, streamed);

      // One equality test on the id — the streamed text is never compared.
      expect(result).toEqual([mockMessageEvent, mockAgentMessageEvent]);
    });

    it("retires the slot in place, keeping events that arrived beside it", () => {
      const opened = openStreamingSlot(
        started("test-agent-message-1", { anchor_seq: 0 }),
        [{ ...mockMessageEvent, seq: 0 }],
      );
      const streamed = appendStreamingDeltas(
        [delta("test-agent-message-1", "partial")],
        opened,
      );
      // A user message lands mid-stream, sequenced after the slot's anchor.
      const interrupted = handleEventForUI(
        { ...mockMessageEvent, id: "mid-stream", seq: 1 },
        streamed,
      );

      const result = handleEventForUI(mockAgentMessageEvent, interrupted);

      expect(result.map((event) => event.id)).toEqual([
        mockMessageEvent.id,
        mockAgentMessageEvent.id,
        "mid-stream",
      ]);
    });

    it("keeps a mid-stream event below the slot rather than splitting it (#15433)", () => {
      const opened = openStreamingSlot(started("item-1", { anchor_seq: 0 }), [
        { ...mockMessageEvent, seq: 0 },
      ]);
      const firstHalf = appendStreamingDeltas(
        [delta("item-1", "first half")],
        opened,
      );
      const interrupted = handleEventForUI(
        { ...mockMessageEvent, id: "mid-stream", seq: 1 },
        firstHalf,
      );
      const result = appendStreamingDeltas(
        [delta("item-1", " second half")],
        interrupted,
      );

      // One slot, still whole, still above the interrupting message.
      expect(slotsOf(result)).toHaveLength(1);
      expect(slotsOf(result)[0].content).toBe("first half second half");
      expect(result.map((event) => event.id)).toEqual([
        mockMessageEvent.id,
        "item-1",
        "mid-stream",
      ]);
    });

    it("supersedes the slot's text when a higher attempt streams it again", () => {
      const opened = openStreamingSlot(started("item-1"), []);
      const first = appendStreamingDeltas([delta("item-1", "retried")], opened);

      const reopened = openStreamingSlot(
        started("item-1", { attempt: 2 }),
        first,
      );
      expect(slotsOf(reopened)[0].content).toBeNull();

      const result = appendStreamingDeltas(
        [delta("item-1", "fresh text", { attempt: 2 })],
        reopened,
      );
      expect(slotsOf(result)).toHaveLength(1);
      expect(slotsOf(result)[0].content).toBe("fresh text");
    });

    it("keeps streamed text when the current attempt's start is repeated", () => {
      const opened = openStreamingSlot(started("item-1"), []);
      const streamed = appendStreamingDeltas([delta("item-1", "kept")], opened);

      const result = openStreamingSlot(started("item-1"), streamed);

      expect(result).toBe(streamed);
      expect(slotsOf(result)[0].content).toBe("kept");
    });

    it("places the slot by anchor_seq when a message lands before the first token", () => {
      // The SDK reads the anchor when the step opens, before the LLM call; a
      // user message persisted while waiting for the first token has a higher
      // seq and has already rendered by the time item_started arrives.
      const history = [
        { ...mockMessageEvent, seq: 0 },
        { ...mockMessageEvent, id: "sent-while-waiting", seq: 1 },
      ];

      const result = openStreamingSlot(
        started("item-1", { anchor_seq: 0 }),
        history,
      );

      expect(result.map((event) => event.id)).toEqual([
        mockMessageEvent.id,
        "item-1",
        "sent-while-waiting",
      ]);
      // Borrowing the anchor's timestamp keeps it there through a re-sort.
      expect(slotsOf(result)[0].timestamp).toBe(mockMessageEvent.timestamp);
    });

    it("borrows the anchor event's timestamp, not its neighbour's", () => {
      const history = [
        {
          ...mockMessageEvent,
          timestamp: "2026-09-16T10:00:00.000001",
          seq: 4,
        },
        // e.g. a transient or client-stamped event with a different clock
        {
          ...mockMessageEvent,
          id: "no-seq",
          timestamp: "2026-09-16T23:59:59Z",
        },
      ];

      const result = openStreamingSlot(
        started("item-1", { anchor_seq: 4 }),
        history,
      );

      expect(slotsOf(result)[0].timestamp).toBe("2026-09-16T10:00:00.000001");
    });

    it("supersedes on a higher-attempt delta even without its item_started", () => {
      const opened = openStreamingSlot(started("item-1"), []);
      const first = appendStreamingDeltas([delta("item-1", "stale")], opened);

      const result = handleEventForUI(finalMessage, [
        mockMessageEvent,
        streamedDelta,
      ]);

      expect(result).toEqual([mockMessageEvent, finalMessage]);
    });

    it("preserves streamed reasoning when the final message replaces unmatched text", () => {
      const streamedDelta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-1", "Stale partial text"),
        reasoning_content: "Reasoning available only in the stream",
      };
      const finalMessage: MessageEvent = {
        ...mockAgentMessageEvent,
        llm_message: {
          role: "assistant",
          content: [{ type: "text", text: "Canonical final text" }],
        },
      };

      const result = handleEventForUI(finalMessage, [
        mockMessageEvent,
        streamedDelta,
      ]);

      expect(result).toEqual([
        mockMessageEvent,
        { ...streamedDelta, content: null },
        finalMessage,
      ]);
    });

    it("drops streamed reasoning when the final message renders it inline", () => {
      const streamedDelta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-1", "Canonical final text"),
        reasoning_content: "Reasoning rendered by the final message",
      };
      const finalMessage: MessageEvent = {
        ...mockAgentMessageEvent,
        llm_message: {
          role: "assistant",
          content: [
            {
              type: "text",
              text: "<think>Reasoning rendered by the final message</think>Canonical final text",
            },
          ],
        },
      };

      const result = handleEventForUI(finalMessage, [
        mockMessageEvent,
        streamedDelta,
      ]);

      expect(result).toEqual([mockMessageEvent, finalMessage]);
    });

    it("keeps deltas from older turns when a later turn finishes", () => {
      // The status update on leaving RUNNING ends the old turn's dangling delta,
      // distinguishing it from a mid-stream message (#1899).
      const executionStatusUpdate = makeExecutionStatusUpdate(
        "execution-status-idle",
        "idle",
      );
      const oldUserMessage: MessageEvent = {
        ...mockMessageEvent,
        id: "old-user-message",
      };
      const nextUserMessage: MessageEvent = {
        ...mockMessageEvent,
        id: "next-user-message",
        llm_message: {
          role: "user",
          content: [{ type: "text", text: "Next task" }],
        },
      };
      const oldDelta = makeStreamingDelta("old-delta", "Old live text");
      const currentDelta = makeStreamingDelta(
        "current-delta",
        "Current live text",
      );

      const result = handleEventForUI(mockFinishActionEvent, [
        oldUserMessage,
        oldDelta,
        executionStatusUpdate,
        nextUserMessage,
        currentDelta,
      ]);

      expect(result).toEqual([
        oldUserMessage,
        oldDelta,
        executionStatusUpdate,
        nextUserMessage,
        mockFinishActionEvent,
      ]);
    });

    describe("message sent mid-stream (#1899)", () => {
      const midStreamUserMessage: MessageEvent = {
        ...mockMessageEvent,
        id: "mid-stream-user-message",
        llm_message: {
          role: "user",
          content: [{ type: "text", text: "also update the README" }],
        },
      };

      const replay = (events: OpenHandsEvent[]): OpenHandsEvent[] =>
        events.reduce<OpenHandsEvent[]>(
          (uiEvents, event) => handleEventForUI(event, uiEvents),
          [],
        );

      // Captured live between the two deltas, agent still RUNNING.
      const runningStateSnapshot = makeFullStateSnapshot(
        "state-running",
        "running",
      );

      it("keeps the reply in one bubble, with the message below it", () => {
        const result = replay([
          mockMessageEvent,
          makeStreamingDelta("delta-1", "I'll start working on that. "),
          midStreamUserMessage,
          makeStreamingDelta("delta-2", "Done."),
        ]);

        // Both deltas in one bubble, message below it.
        expect(result).toEqual([
          mockMessageEvent,
          {
            ...makeStreamingDelta("delta-1", "I'll start working on that. "),
            content: "I'll start working on that. Done.",
            timestamp: expect.any(String),
          },
          midStreamUserMessage,
        ]);
      });

      it("renders the canonical final message in the stream's place", () => {
        const result = replay([
          mockMessageEvent,
          makeStreamingDelta("delta-1", "I'll start working on that. "),
          midStreamUserMessage,
          makeStreamingDelta("delta-2", "Done."),
          mockAgentMessageEvent,
        ]);

        // Once, above the message — no orphaned half.
        expect(result).toEqual([
          mockMessageEvent,
          mockAgentMessageEvent,
          midStreamUserMessage,
        ]);
      });

      it("survives the state snapshot the server emits after the message", () => {
        // Exact frame order captured live; the still-RUNNING snapshot must not
        // break the run.
        const result = replay([
          mockMessageEvent,
          makeStreamingDelta("delta-1", "I'll start working on that. "),
          midStreamUserMessage,
          runningStateSnapshot,
          makeStreamingDelta("delta-2", "Done."),
          mockAgentMessageEvent,
        ]);

        expect(result).toEqual([
          mockMessageEvent,
          mockAgentMessageEvent,
          midStreamUserMessage,
          runningStateSnapshot,
        ]);
      });

      it("still treats a snapshot that leaves RUNNING as a turn boundary", () => {
        // An interrupted turn's dangling delta must survive the next turn.
        const idleStateSnapshot = {
          ...(runningStateSnapshot as unknown as Record<string, unknown>),
          id: "state-idle",
          value: { execution_status: "idle" },
        } as unknown as OpenHandsEvent;
        const danglingDelta = makeStreamingDelta("delta-old", "Interrupted...");

        const result = replay([
          mockMessageEvent,
          danglingDelta,
          idleStateSnapshot,
          midStreamUserMessage,
          makeStreamingDelta("delta-2", "I'll start working on that. Done."),
          mockAgentMessageEvent,
        ]);

        expect(result).toEqual([
          mockMessageEvent,
          danglingDelta,
          idleStateSnapshot,
          midStreamUserMessage,
          mockAgentMessageEvent,
        ]);
      });

      it("places a reasoning-only turn's reply above the message too", () => {
        // Models that stream `reasoning_content` and no `content` produce no
        // content deltas, so there is nothing to supersede — but the reply
        // still has to land where the stream ended. Appending it at the tail
        // dropped it below a message the user sent while the reasoning bubble
        // was already on screen.
        const reasoningDelta: StreamingDeltaEvent = {
          ...makeStreamingDelta("delta-reasoning", null),
          reasoning_content: "Considering the request...",
        };

        const result = replay([
          mockMessageEvent,
          reasoningDelta,
          midStreamUserMessage,
          mockAgentMessageEvent,
        ]);

        expect(result).toEqual([
          mockMessageEvent,
          reasoningDelta,
          mockAgentMessageEvent,
          midStreamUserMessage,
        ]);
      });

      it("does not let another sender's delta drag the turn boundary back (#1656)", () => {
        // The main and planning sockets share this event store. A planning
        // delta interleaved into the main agent's run must stay transparent to
        // the main agent's turn-boundary scan: counting it pulled the scan
        // back past `secondQuestion`, so the reply both stripped the previous
        // turn's streamed text and rendered above the question it answered.
        const idleStateSnapshot = {
          ...(runningStateSnapshot as unknown as Record<string, unknown>),
          id: "state-idle",
          value: { execution_status: "idle" },
        } as unknown as OpenHandsEvent;
        const previousTurnDelta = makeStreamingDelta(
          "delta-old",
          "First answer.",
        );
        const planningDelta = {
          ...makeStreamingDelta("delta-planning", "Planning..."),
          isFromPlanningAgent: true,
        } as OpenHandsEvent;
        const secondQuestion: MessageEvent = {
          ...mockMessageEvent,
          id: "second-question",
          llm_message: {
            role: "user",
            content: [{ type: "text", text: "now do the other thing" }],
          },
        };

        const result = replay([
          mockMessageEvent,
          previousTurnDelta,
          idleStateSnapshot,
          planningDelta,
          secondQuestion,
          makeStreamingDelta("delta-2", "I'll start working on that. Done."),
          mockAgentMessageEvent,
        ]);

        // The previous turn's delta survives, and the reply stays below the
        // question that prompted it.
        expect(result).toEqual([
          mockMessageEvent,
          previousTurnDelta,
          idleStateSnapshot,
          planningDelta,
          secondQuestion,
          mockAgentMessageEvent,
        ]);
      });

      it("reconciles a streamed thought split by the message", () => {
        const thought = "Let me gather information.";
        const action: ActionEvent = {
          ...mockActionEvent,
          id: "intermediate-1",
          thought: [{ type: "text", text: thought }],
        };

        const result = replay([
          mockMessageEvent,
          makeStreamingDelta("delta-1", "Let me gather "),
          midStreamUserMessage,
          makeStreamingDelta("delta-2", "information."),
          action,
        ]);

        // Streamed thought still stripped even though the message split it
        // (#1534), and the action lands where the stream ended rather than at
        // the tail — the same placement a finalized reply gets, so a
        // tool-calling step doesn't jump below the mid-stream message (#1899).
        expect(result).toEqual([
          mockMessageEvent,
          action,
          midStreamUserMessage,
        ]);
      });
    });

    it("appends final message normally when all deltas are reasoning-only", () => {
      // When every streaming delta carries only reasoning_content (no content),
      // streamingSegments is empty → finalizeStreamingDeltasInPlace returns null
      // → finalEvent is appended after the delta as a regular message bubble.
      const reasoningDelta: StreamingDeltaEvent = {
        id: "delta-reasoning",
        kind: "StreamingDeltaEvent",
        timestamp: Date.now().toString(),
        source: "agent",
        content: null,
        reasoning_content: "thinking...",
      };
      const result = handleEventForUI(mockAgentMessageEvent, [
        mockMessageEvent,
        reasoningDelta,
      ]);
      expect(result).toEqual([
        mockMessageEvent,
        reasoningDelta,
        mockAgentMessageEvent,
      ]);
    });

    it("does not merge deltas from different senders into one bubble (#1656)", () => {
      // A planning-agent delta must not concatenate onto a main-agent delta;
      // they stay separate bubbles.
      const mainDelta = makeStreamingDelta("delta-main", "Main agent says ");
      const planningDelta = {
        ...makeStreamingDelta("delta-planning", "planning agent says"),
        isFromPlanningAgent: true,
      });

      expect(clearStreamingSlots(both).map((event) => event.id)).toEqual([
        mockMessageEvent.id,
        "plan-item",
      ]);
      expect(clearStreamingSlots(both, true).map((event) => event.id)).toEqual([
        mockMessageEvent.id,
        "main-item",
      ]);
    });

    it("planning final preserves a still-live main-agent delta (#1656)", () => {
      // Main and planning sockets share this event store. A planning-agent
      // final must supersede only the planning stream; the main agent's live
      // delta must survive.
      const mainDelta = makeStreamingDelta("delta-main", "Main still typing");
      const planningDelta = {
        ...makeStreamingDelta("delta-planning", "Planning says hello"),
        isFromPlanningAgent: true,
      };
      const planningFinal = {
        ...mockAgentMessageEvent,
        id: "planning-final",
        isFromPlanningAgent: true,
        llm_message: {
          role: "assistant" as const,
          content: [{ type: "text" as const, text: "Planning says hello" }],
        },
      };

      const result = handleEventForUI(planningFinal, [
        mockMessageEvent,
        mainDelta,
        planningDelta,
      ]);

      expect(result).toEqual([mockMessageEvent, mainDelta, planningFinal]);
    });

    it("main final preserves a still-live planning-agent delta (#1656)", () => {
      const mainDelta = makeStreamingDelta("delta-main", "Main says hello");
      const planningDelta = {
        ...makeStreamingDelta("delta-planning", "Planning still typing"),
        isFromPlanningAgent: true,
      };
      const mainFinal = {
        ...mockAgentMessageEvent,
        id: "main-final",
        llm_message: {
          role: "assistant" as const,
          content: [{ type: "text" as const, text: "Main says hello" }],
        },
      };

      const result = handleEventForUI(mainFinal, [
        mockMessageEvent,
        mainDelta,
        planningDelta,
      ]);

      // The main agent's final message splices in where its own trailing run
      // ended (right after mainDelta), not after the unrelated planning delta.
      expect(result).toEqual([mockMessageEvent, mainFinal, planningDelta]);
    });
  });

  it("should NOT add ThinkObservation even when ThinkAction is not found", () => {
    const mockThinkObservation: ObservationEvent = {
      id: "test-think-observation-1",
      timestamp: Date.now().toString(),
      source: "environment",
      tool_name: "think",
      tool_call_id: "call_think_1",
      observation: {
        kind: "ThinkObservation",
        content: [{ type: "text", text: "Your thought has been logged." }],
      },
      action_id: "test-think-action-not-found",
    };

    const initialUiEvents = [mockMessageEvent];
    const result = handleEventForUI(mockThinkObservation, initialUiEvents);

    // ThinkObservation should never be added to uiEvents
    expect(result).toEqual([mockMessageEvent]);
    expect(result).not.toBe(initialUiEvents);
  });

  // Regression for issue #1534: with stream=true an agent step streams its
  // pre-tool-call text as a StreamingDeltaEvent, then the step arrives as an
  // intermediate ActionEvent whose `thought` is that same text. The chat hoists
  // the action's thought into its own message, so the leftover streaming delta
  // must not also render the text or it appears twice.
  describe("intermediate action / streamed thought reconciliation (#1534)", () => {
    const makeThoughtAction = (id: string, thought: string): ActionEvent => ({
      ...mockActionEvent,
      id,
      tool_call_id: `call_${id}`,
      thought: [{ type: "text", text: thought }],
    });

    it("clears the streamed content from the delta, keeping its reasoning", () => {
      const thought = "Let me gather accurate information.";
      const delta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-1", thought),
        reasoning_content: "pondering the request",
      };
      const action = makeThoughtAction("intermediate-1", thought);

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      expect(result).toEqual([
        mockMessageEvent,
        { ...delta, content: null },
        action,
      ]);
    });

    it("drops the delta entirely when it has no reasoning left to render", () => {
      const thought = "Let me gather accurate information.";
      const delta = makeStreamingDelta("delta-1", thought);
      const action = makeThoughtAction("intermediate-1", thought);

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      expect(result).toEqual([mockMessageEvent, action]);
    });

    it("reconciles across multiple streamed segments in order", () => {
      const first = makeStreamingDelta("delta-1", "Let me gather ");
      const merged = handleEventForUI(
        makeStreamingDelta("delta-2", "accurate information."),
        handleEventForUI(first, [mockMessageEvent]),
      );
      const action = makeThoughtAction(
        "intermediate-1",
        "Let me gather accurate information.",
      );

      const result = handleEventForUI(action, merged);

      // The merged content delta is fully streamed and has no reasoning, so it
      // is dropped and only the action remains.
      expect(result).toEqual([mockMessageEvent, action]);
    });

    it("leaves the delta untouched when streamed text does not match the thought", () => {
      const delta = makeStreamingDelta(
        "delta-1",
        "some unrelated streamed text",
      );
      const action = makeThoughtAction(
        "intermediate-1",
        "An unrelated thought.",
      );

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      expect(result).toEqual([mockMessageEvent, delta, action]);
    });

    // Non-native tool call: the delta is `thought` + raw `<function=...>` XML, a
    // superset of the thought, so only the marker signal reconciles it.
    it("clears the delta when streamed text is the thought plus an unstripped <function=...> block", () => {
      const thought = "Coding and executing";
      const delta = makeStreamingDelta(
        "delta-1",
        `${thought}<function=terminal>\n<parameter=command>echo hi</parameter>\n<parameter=security_risk>LOW</parameter>\n</function>`,
      );
      const action = makeThoughtAction("intermediate-1", thought);

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      expect(result).toEqual([mockMessageEvent, action]);
    });

    // The planning and main sockets share this store, so the marker signal must
    // not let one agent's action strip the other's live delta.
    it("leaves a marker-bearing delta from the other agent untouched", () => {
      const delta = {
        ...makeStreamingDelta(
          "delta-1",
          `Planning<function=terminal>\n<parameter=command>echo hi</parameter>\n</function>`,
        ),
        isFromPlanningAgent: true,
      };
      const action = makeThoughtAction(
        "intermediate-1",
        "Coding and executing",
      );

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      expect(result).toEqual([mockMessageEvent, delta, action]);
    });

    it("does not reconcile a ThinkAction (its thought renders separately)", () => {
      const thought = "A reasoning step.";
      const delta = makeStreamingDelta("delta-1", thought);
      const thinkAction: ActionEvent = {
        ...mockActionEvent,
        id: "think-1",
        tool_name: "think",
        tool_call_id: "call_think_1",
        thought: [{ type: "text", text: thought }],
        action: { kind: "ThinkAction", thought },
      };

      const result = handleEventForUI(thinkAction, [mockMessageEvent, delta]);

      expect(result).toEqual([mockMessageEvent, delta, thinkAction]);
    });

    it("only reconciles the current turn's delta (after the last user message)", () => {
      const thought = "Let me gather accurate information.";
      const earlierTurnDelta = makeStreamingDelta("delta-old", thought);
      // The status update on leaving RUNNING ends the earlier turn's run (#1899).
      const executionStatusUpdate = makeExecutionStatusUpdate(
        "execution-status-idle",
        "idle",
      );
      const laterUserMessage: MessageEvent = {
        ...mockMessageEvent,
        id: "user-2",
      };
      const action = makeThoughtAction("intermediate-1", thought);

      const result = handleEventForUI(action, [
        mockMessageEvent,
        earlierTurnDelta,
        executionStatusUpdate,
        laterUserMessage,
      ]);

      // The delta belongs to a turn before the latest user message, so it is
      // left intact and the action is appended normally.
      expect(result).toEqual([
        mockMessageEvent,
        earlierTurnDelta,
        executionStatusUpdate,
        laterUserMessage,
        action,
      ]);
    });

    it("reconciles even when the thought is whitespace-trimmed vs the stream", () => {
      // The SDK strips assistant text, so the action's thought can lack the
      // trailing newline the model streamed before the tool call.
      const delta = makeStreamingDelta(
        "delta-1",
        "Let me gather information.\n",
      );
      const action = makeThoughtAction(
        "intermediate-1",
        "Let me gather information.",
      );

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      // Match succeeds despite the trailing newline, so the delta is dropped.
      expect(result).toEqual([mockMessageEvent, action]);
    });

    it("only folds in the current step's trailing delta, not an earlier step's", () => {
      // An earlier step's delta still carrying content sits before this step's
      // observation; it must NOT be joined into the match.
      const earlierDelta = makeStreamingDelta(
        "delta-early",
        "Earlier step text.",
      );
      const currentDelta = makeStreamingDelta(
        "delta-current",
        "Current step text.",
      );
      const action = makeThoughtAction("intermediate-2", "Current step text.");

      const result = handleEventForUI(action, [
        mockMessageEvent,
        earlierDelta,
        mockObservationEvent,
        currentDelta,
      ]);

      // Only the trailing (current) delta is reconciled and dropped; the
      // earlier delta is untouched.
      expect(result).toEqual([
        mockMessageEvent,
        earlierDelta,
        mockObservationEvent,
        action,
      ]);
    });

    it("drops the delta instead of keeping its reasoning when the action carries reasoning", () => {
      const thought = "Let me gather accurate information.";
      const delta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-1", thought),
        reasoning_content: "streamed reasoning",
      };
      const action: ActionEvent = {
        ...makeThoughtAction("intermediate-1", thought),
        reasoning_content: "finalized reasoning",
      };

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      // The action renders the Thinking section itself, so the delta is fully
      // redundant and dropped — no leftover reasoning-only delta.
      expect(result).toEqual([mockMessageEvent, action]);
    });
  });

  describe("intermediate action / streamed reasoning reconciliation", () => {
    const REASONING = "Let me read the full PRD to understand all of it.";

    const makeReasoningAction = (thought: string[]): ActionEvent => ({
      ...mockActionEvent,
      id: "intermediate-1",
      tool_call_id: "call_intermediate_1",
      thought: thought.map((text) => ({ type: "text", text })),
      reasoning_content: REASONING,
    });

    it("drops a reasoning-only delta when the action has no thought", () => {
      const delta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-1", null),
        reasoning_content: REASONING,
      };
      const action = makeReasoningAction([]);

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      expect(result).toEqual([mockMessageEvent, action]);
    });

    it("drops a reasoning-only delta when the thought does not match it", () => {
      const delta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-1", null),
        reasoning_content: REASONING,
      };
      const action = makeReasoningAction(["Reading the PRD now."]);

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      expect(result).toEqual([mockMessageEvent, action]);
    });

    it("keeps unmatched streamed text while clearing the duplicated reasoning", () => {
      const delta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-1", "some unrelated streamed text"),
        reasoning_content: REASONING,
      };
      const action = makeReasoningAction(["An unrelated thought."]);

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      expect(result).toEqual([
        mockMessageEvent,
        { ...delta, reasoning_content: null },
        action,
      ]);
    });

    it("leaves the delta untouched when the action carries no reasoning", () => {
      const delta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-1", null),
        reasoning_content: REASONING,
      };
      const action: ActionEvent = {
        ...mockActionEvent,
        id: "intermediate-1",
        tool_call_id: "call_intermediate_1",
        thought: [],
      };

      const result = handleEventForUI(action, [mockMessageEvent, delta]);

      // The delta is the sole reasoning carrier, so it must survive.
      expect(result).toEqual([mockMessageEvent, delta, action]);
    });

    it("only reconciles the current step's trailing delta run", () => {
      const earlierDelta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-earlier", null),
        reasoning_content: "an earlier step's reasoning",
      };
      const delta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-1", null),
        reasoning_content: REASONING,
      };
      const action = makeReasoningAction([]);

      const result = handleEventForUI(action, [
        mockMessageEvent,
        earlierDelta,
        mockObservationEvent,
        delta,
      ]);

      expect(result).toEqual([
        mockMessageEvent,
        earlierDelta,
        mockObservationEvent,
        action,
      ]);
    });

    it("preserves a still-live planning-agent delta (#1656)", () => {
      // Main and planning sockets share this event store. A main-agent action
      // supersedes only the main agent's streamed reasoning; the planning
      // agent's live reasoning must survive.
      const planningDelta = {
        ...makeStreamingDelta("delta-planning", null),
        reasoning_content: "Planning agent is still reasoning",
        isFromPlanningAgent: true,
      };
      const mainDelta: StreamingDeltaEvent = {
        ...makeStreamingDelta("delta-main", null),
        reasoning_content: REASONING,
      };
      const action = makeReasoningAction([]);

      const result = handleEventForUI(action, [
        mockMessageEvent,
        planningDelta,
        mainDelta,
      ]);

      expect(result).toEqual([mockMessageEvent, planningDelta, action]);
    });

    it("leaves the planning agent's reasoning alone when only it streamed (#1656)", () => {
      const planningDelta = {
        ...makeStreamingDelta("delta-planning", null),
        reasoning_content: "Planning agent is still reasoning",
        isFromPlanningAgent: true,
      };
      const action = makeReasoningAction([]);

      const result = handleEventForUI(action, [
        mockMessageEvent,
        planningDelta,
      ]);

      expect(result).toEqual([mockMessageEvent, planningDelta, action]);
    });
  });
});
