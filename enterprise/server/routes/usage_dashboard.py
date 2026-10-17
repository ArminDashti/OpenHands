"""API routes for usage dashboard."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from server.auth.authorization import Permission, require_permission
from server.routes.usage_dashboard_models import UsageDashboardData, UsageDashboardError
from server.services.usage_dashboard_service import UsageDashboardService
from sqlalchemy.ext.asyncio import AsyncSession
from storage.database import get_async_saas_db_session

from openhands.core.logger import openhands_logger as logger

# Initialize API router
usage_dashboard_router = APIRouter(
    prefix='/api/organizations', tags=['Usage Dashboard']
)


async def get_usage_dashboard_service(
    db_session: Annotated[AsyncSession, Depends(get_async_saas_db_session)],
) -> UsageDashboardService:
    """Dependency injection for UsageDashboardService.

    Args:
        db_session: Async database session

    Returns:
        UsageDashboardService instance
    """
    return UsageDashboardService(db_session)


def _check_view_analytics_permission(org_id: UUID):
    """Helper to create permission check dependency."""
    return require_permission(Permission.VIEW_ANALYTICS)(org_id)


@usage_dashboard_router.get(
    '/{org_id}/usage-dashboard',
    response_model=UsageDashboardData,
    responses={
        200: {'description': 'Usage dashboard data retrieved successfully'},
        403: {
            'model': UsageDashboardError,
            'description': 'Insufficient permissions to view usage dashboard',
        },
        404: {
            'model': UsageDashboardError,
            'description': 'Organization not found',
        },
        500: {
            'model': UsageDashboardError,
            'description': 'Database error occurred',
        },
    },
)
async def get_usage_dashboard(
    org_id: UUID,
    service: Annotated[UsageDashboardService, Depends(get_usage_dashboard_service)],
    _permission_check: str = Depends(_check_view_analytics_permission),
) -> UsageDashboardData:
    """Get usage dashboard data for an organization.

    This endpoint returns comprehensive usage statistics including:
    - Total number of conversations
    - Average cost per conversation
    - Top 5 most popular LLM models
    - Last 30 days of conversation activity (grouped by date)
    - Top users by conversation count

    Args:
        org_id: Organization ID
        service: UsageDashboardService dependency
        _permission_check: Permission check dependency (VIEW_ANALYTICS required)

    Returns:
        UsageDashboardData: Complete usage dashboard metrics

    Raises:
        HTTPException: 403 if user lacks VIEW_ANALYTICS permission
        HTTPException: 404 if organization not found
        HTTPException: 500 if database error occurs
    """
    logger.info(
        'Getting usage dashboard data',
        extra={'org_id': str(org_id)},
    )

    try:
        dashboard_data = await service.get_dashboard_data(org_id)
        logger.info(
            'Successfully retrieved usage dashboard data',
            extra={
                'org_id': str(org_id),
                'total_conversations': dashboard_data.total_conversations,
            },
        )
        return dashboard_data

    except Exception as e:
        logger.error(
            'Error retrieving usage dashboard data',
            extra={'org_id': str(org_id), 'error': str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                'error': 'database_error',
                'message': f'Failed to retrieve usage dashboard data: {str(e)}',
            },
        ) from e


__all__ = ['usage_dashboard_router']
