"""Data models for the usage dashboard."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ConversationActivityDay(BaseModel):
    """Represents conversation activity for a single day."""

    date: date = Field(..., description='Date of the activity')
    count: int = Field(..., description='Number of conversations on this date', ge=0)


class LLMModelUsage(BaseModel):
    """Represents usage statistics for a specific LLM model."""

    model_name: str = Field(..., description='Name of the LLM model')
    count: int = Field(..., description='Number of times this model was used', ge=0)


class UserUsageStats(BaseModel):
    """Represents usage statistics for a specific user."""

    user_id: str = Field(..., description='User ID')
    user_email: str | None = Field(None, description='User email address')
    conversation_count: int = Field(
        ..., description='Number of conversations by this user', ge=0
    )


class UsageDashboardData(BaseModel):
    """Complete usage dashboard data for an organization."""

    total_conversations: int = Field(
        ..., description='Total number of conversations in the organization', ge=0
    )
    average_cost_per_conversation: float = Field(
        ..., description='Average cost per conversation', ge=0
    )
    top_llm_models: list[LLMModelUsage] = Field(
        ..., description='Top 5 most popular LLM models', max_length=5
    )
    conversation_activity_30_days: list[ConversationActivityDay] = Field(
        ..., description='Last 30 days of conversation activity', max_length=30
    )
    top_users: list[UserUsageStats] = Field(
        ..., description='Top users by conversation count', max_length=10
    )


class UsageDashboardError(BaseModel):
    """Error response for usage dashboard endpoints."""

    error: Literal['org_not_found', 'insufficient_permissions', 'database_error']
    message: str


__all__ = [
    'ConversationActivityDay',
    'LLMModelUsage',
    'UserUsageStats',
    'UsageDashboardData',
    'UsageDashboardError',
]
