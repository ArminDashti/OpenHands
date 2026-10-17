import { openHands } from "./open-hands-axios";

export interface ConversationActivityDay {
  date: string;
  count: number;
}

export interface LLMModelUsage {
  model_name: string;
  count: number;
}

export interface UserUsageStats {
  user_id: string;
  user_email: string | null;
  conversation_count: number;
}

export interface UsageDashboardData {
  total_conversations: number;
  average_cost_per_conversation: number;
  top_llm_models: LLMModelUsage[];
  conversation_activity_30_days: ConversationActivityDay[];
  top_users: UserUsageStats[];
}

export const usageDashboardService = {
  getDashboardData: async (orgId: string): Promise<UsageDashboardData> => {
    const { data } = await openHands.get<UsageDashboardData>(
      `/api/organizations/${orgId}/usage-dashboard`,
    );
    return data;
  },
};
