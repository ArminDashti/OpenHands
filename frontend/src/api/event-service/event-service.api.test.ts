import { beforeEach, describe, expect, it, vi } from "vitest";

import EventService from "./event-service.api";
import { openHands } from "../open-hands-axios";
import type { OpenHandsEvent } from "#/types/v1/core";

vi.mock("../open-hands-axios", () => ({
  openHands: {
    get: vi.fn(),
  },
}));

const completedPreviousActionObservation = {
  id: "observation-previous-action",
  timestamp: "2026-05-05T00:45:10.200000",
  source: "environment",
  tool_name: "file_editor",
  tool_call_id: "call_previous",
  action_id: "action-previous",
  observation: {
    kind: "FileEditorObservation",
    command: "str_replace",
    path: "/workspace/project/src/components/product-feature-page.tsx",
  },
  kind: "ObservationEvent",
} as unknown as OpenHandsEvent;

const runningLongAction = {
  id: "action-running-parity",
  timestamp: "2026-05-05T00:45:14.765343",
  source: "agent",
  tool_name: "terminal",
  tool_call_id: "call_running",
  summary: "Run parity after product image matching",
  action: {
    kind: "TerminalAction",
    command:
      "npm run typecheck && PARITY_OUTPUT_DIR=.agent_tmp/parity-after-product-images npm run parity:checklist",
  },
  kind: "ActionEvent",
} as unknown as OpenHandsEvent;

describe("EventService.searchEventsV1", () => {
  const mockGet = vi.mocked(openHands.get);

  beforeEach(() => {
    mockGet.mockReset();
  });

  it("loads the next history page so reloads do not stop on a completed action before a running action", async () => {
    mockGet
      .mockResolvedValueOnce({
        data: {
          items: [completedPreviousActionObservation],
          next_page_id: "page-containing-running-action",
        },
      } as never)
      .mockResolvedValueOnce({
        data: {
          items: [runningLongAction],
          next_page_id: null,
        },
      } as never);

    const events = await EventService.searchEventsV1("conversation-id", 1);

    expect(mockGet).toHaveBeenNthCalledWith(
      1,
      "/api/v1/conversation/conversation-id/events/search",
      { params: { limit: 1 } },
    );
    expect(mockGet).toHaveBeenNthCalledWith(
      2,
      "/api/v1/conversation/conversation-id/events/search",
      {
        params: {
          limit: 1,
          page_id: "page-containing-running-action",
        },
      },
    );
    expect(events).toEqual([
      completedPreviousActionObservation,
      runningLongAction,
    ]);
  });
});
