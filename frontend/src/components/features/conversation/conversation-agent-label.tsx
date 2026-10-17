import { Typography } from "#/ui/typography";
import CircuitIcon from "#/icons/u-circuit.svg?react";

interface ConversationAgentLabelProps {
  /** Server-stamped label — ``"Claude Code"`` for known ACP presets,
   *  ``null`` for OpenHands conversations. */
  displayName?: string | null;
  /** LLM model id used by OpenHands conversations. Falls back to this when
   *  ``displayName`` is null so OH chips still render the model. */
  llmModel?: string | null;
  /** Tailwind classes for the outer ``<span>``. Callers control width and
   *  text colour (the chip sits inside different parents). */
  className: string;
  /** Tailwind classes for the inner ``Typography.Text``. */
  textClassName?: string;
  testId?: string;
}

/**
 * Tiny chip rendering the agent for a conversation: ACP brand label (or
 * ``"ACP"`` for unknown / custom commands) for ACP conversations, the raw
 * ``llm_model`` for OpenHands. Hidden entirely when neither is set.
 *
 * The ``display_name`` is stamped server-side via ``acp_display_name`` and
 * already resolves the SDK registry, so this component is presentational —
 * no per-render registry lookup needed.
 */
export function ConversationAgentLabel({
  displayName,
  llmModel,
  className,
  textClassName = "text-xs truncate",
  testId,
}: ConversationAgentLabelProps) {
  const label = displayName ?? llmModel;
  if (!label) return null;

  return (
    <span className={className} title={label} data-testid={testId}>
      <CircuitIcon width={12} height={12} className="shrink-0" />
      <Typography.Text className={textClassName}>{label}</Typography.Text>
    </span>
  );
}
