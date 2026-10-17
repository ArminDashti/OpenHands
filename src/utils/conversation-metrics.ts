import type {
  MetricsSnapshot,
  RuntimeConversationInfo,
  RuntimeConversationStats,
  TokenUsage,
} from "#/api/conversation-service/agent-server-conversation-service.types";

interface CombinableTokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  context_window: number;
  per_turn_token: number;
}

interface CombinableMetrics {
  accumulated_cost: number;
  max_budget_per_task: number | null;
  accumulated_token_usage?: CombinableTokenUsage | null;
}

/**
 * TypeScript equivalent of the get_combined_metrics method from the Python SDK
 * Combines metrics from all LLM usage IDs in a conversation's stats
 */
export function combineUsageMetrics(
  stats: RuntimeConversationStats | null | undefined,
): MetricsSnapshot {
  if (!stats?.usage_to_metrics) {
    return {
      accumulated_cost: 0,
      max_budget_per_task: null,
      accumulated_token_usage: null,
    };
  }

  let totalCost = 0;
  let maxBudgetPerTask: number | null = null;
  let combinedTokenUsage: TokenUsage | null = null;

  for (const metrics of Object.values(usageToMetrics)) {
    // Add up costs
    totalCost += metrics.accumulated_cost;

    // Keep the max budget per task if any is set
    if (maxBudgetPerTask === null && metrics.max_budget_per_task !== null) {
      maxBudgetPerTask = metrics.max_budget_per_task;
    }

    // Combine token usage
    if (metrics.accumulated_token_usage) {
      if (combinedTokenUsage === null) {
        combinedTokenUsage = { ...metrics.accumulated_token_usage };
      } else {
        combinedTokenUsage = {
          prompt_tokens:
            combinedTokenUsage.prompt_tokens +
            metrics.accumulated_token_usage.prompt_tokens,
          completion_tokens:
            combinedTokenUsage.completion_tokens +
            metrics.accumulated_token_usage.completion_tokens,
          cache_read_tokens:
            combinedTokenUsage.cache_read_tokens +
            metrics.accumulated_token_usage.cache_read_tokens,
          cache_write_tokens:
            combinedTokenUsage.cache_write_tokens +
            metrics.accumulated_token_usage.cache_write_tokens,
          context_window: Math.max(
            combinedTokenUsage.context_window,
            metrics.accumulated_token_usage.context_window,
          ),
          per_turn_token: Math.max(
            combinedTokenUsage.per_turn_token,
            metrics.accumulated_token_usage.per_turn_token,
          ),
        };
      }
    }
  }

  return {
    accumulated_cost: totalCost,
    max_budget_per_task: maxBudgetPerTask,
    accumulated_token_usage: combinedTokenUsage,
  };
}

export function getCombinedMetrics(
  conversationInfo: RuntimeConversationInfo,
): MetricsSnapshot {
  return combineUsageMetrics(conversationInfo.stats);
}
