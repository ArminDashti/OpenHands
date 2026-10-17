from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from openhands.core.logger import openhands_logger as logger
from openhands.runtime.base import Runtime

app = APIRouter(prefix='/api')


@app.get('/conversation')
async def get_remote_runtime_config(request: Request):
    """Retrieve the runtime configuration.

    Currently, this is the session ID and runtime ID (if available).
    """
    runtime = request.state.conversation.runtime
    runtime_id = runtime.runtime_id if hasattr(runtime, 'runtime_id') else None
    session_id = runtime.sid if hasattr(runtime, 'sid') else None
    return JSONResponse(
        content={
            'runtime_id': runtime_id,
            'session_id': session_id,
        }
    )


class ConversationMetrics(BaseModel):
    """Model for conversation metrics."""

    model: str
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    total_cache_hit_tokens: int


@app.get('/metrics', response_model=ConversationMetrics)
async def get_conversation_metrics(request: Request):
    """Get metrics for the current conversation.

    Returns:
        JSONResponse: A JSON response containing:
            - model: The LLM model being used
            - total_cost: The total cost for the conversation so far
            - total_input_tokens: The total number of input tokens used
            - total_output_tokens: The total number of output tokens used
            - total_cache_hit_tokens: The total number of cache hit tokens
    """
    try:
        # Get the agent controller from the conversation
        controller = request.state.conversation.runtime.agent_session.controller
        if not controller or not controller.agent or not controller.agent.llm:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={'error': 'LLM not found for this conversation'},
            )

        # Get the metrics from the LLM
        llm = controller.agent.llm
        metrics = llm.metrics

        # Get the accumulated token usage
        token_usage = metrics._accumulated_token_usage

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                'model': metrics.model_name,
                'total_cost': metrics.accumulated_cost,
                'total_input_tokens': token_usage.prompt_tokens,
                'total_output_tokens': token_usage.completion_tokens,
                'total_cache_hit_tokens': token_usage.cache_read_tokens,
            },
        )
    except Exception as e:
        logger.error(f'Error getting conversation metrics: {e}')
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': f'Error getting conversation metrics: {e}'},
        )


@app.get('/vscode-url')
async def get_vscode_url(request: Request):
    """Get the VSCode URL.

    This endpoint allows getting the VSCode URL.

    Args:
        request (Request): The incoming FastAPI request object.

    Returns:
        JSONResponse: A JSON response indicating the success of the operation.
    """
    try:
        runtime: Runtime = request.state.conversation.runtime
        logger.debug(f'Runtime type: {type(runtime)}')
        logger.debug(f'Runtime VSCode URL: {runtime.vscode_url}')
        return JSONResponse(status_code=200, content={'vscode_url': runtime.vscode_url})
    except Exception as e:
        logger.error(f'Error getting VSCode URL: {e}', exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                'vscode_url': None,
                'error': f'Error getting VSCode URL: {e}',
            },
        )


@app.get('/costs')
async def get_costs(request: Request):
    """Get the accumulated costs and cost history for the current session."""
    if not request.state.conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found'
        )
    metrics = request.state.conversation.runtime.metrics
    return JSONResponse(content=metrics.get())


@app.get('/events/search')
async def search_events(
    request: Request,
    query: str | None = None,
    start_id: int = 0,
    limit: int = 20,
    event_type: str | None = None,
    source: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """Search through the event stream with filtering and pagination.
    Args:
        request (Request): The incoming request object
        query (str, optional): Text to search for in event content
        start_id (int): Starting ID in the event stream. Defaults to 0
        limit (int): Maximum number of events to return. Must be between 1 and 100. Defaults to 20
        event_type (str, optional): Filter by event type (e.g., "FileReadAction")
        source (str, optional): Filter by event source
        start_date (str, optional): Filter events after this date (ISO format)
        end_date (str, optional): Filter events before this date (ISO format)
    Returns:
        dict: Dictionary containing:
            - events: List of matching events
            - has_more: Whether there are more matching events after this batch
    Raises:
        HTTPException: If conversation is not found
        ValueError: If limit is less than 1 or greater than 100
    """
    if not request.state.conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found'
        )
    # Get matching events from the stream
    event_stream = request.state.conversation.event_stream
    matching_events = event_stream.get_matching_events(
        query=query,
        event_type=event_type,
        source=source,
        start_date=start_date,
        end_date=end_date,
        start_id=start_id,
        limit=limit + 1,  # Get one extra to check if there are more
    )
    # Check if there are more events
    has_more = len(matching_events) > limit
    if has_more:
        matching_events = matching_events[:limit]  # Remove the extra event
    return {
        'events': matching_events,
        'has_more': has_more,
    }
