"""OAuth 2.0 Device Authorization Grant routes (RFC 8628).

These routes implement the device authorization flow for CLI authentication.
"""

import secrets
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from storage.database import get_db
from storage.device_auth_store import DeviceAuthStore

from openhands.core.logger import openhands_logger as logger

router = APIRouter(prefix='/api/v1/auth')
device_page_router = APIRouter()  # No prefix for /device page


class DeviceCodeRequest(BaseModel):
    """Request model for device code generation (not used, endpoint takes no body)."""

    pass


class DeviceCodeResponse(BaseModel):
    """Response model for device code generation."""

    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int


class DeviceTokenRequest(BaseModel):
    """Request model for token polling."""

    device_code: str


class DeviceTokenPendingResponse(BaseModel):
    """Response when authorization is still pending."""

    status: Literal['pending']


class DeviceTokenSuccessResponse(BaseModel):
    """Response when authorization is complete."""

    api_key: str


class DeviceTokenErrorResponse(BaseModel):
    """Response for token request errors."""

    error: str
    error_description: str | None = None


@router.post('/device', response_model=DeviceCodeResponse)
async def request_device_code(
    request: Request,
    db: Session = Depends(get_db),
) -> DeviceCodeResponse:
    """Request a device code for CLI authentication.

    This is the first step in the OAuth 2.0 Device Flow.
    The CLI calls this endpoint to get a device_code and user_code.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Device code, user code, and verification URI

    Raises:
        HTTPException: On internal server error
    """
    try:
        store = DeviceAuthStore(db)

        # Create a new device authorization session
        # Default expiration: 5 minutes (300 seconds)
        device_code, user_code, expires_at = store.create_session(expires_in=300)

        # Calculate expires_in from expires_at
        now = datetime.now(expires_at.tzinfo)
        expires_in = int((expires_at - now).total_seconds())

        # Get the base URL from the request
        base_url = str(request.base_url).rstrip('/')

        logger.info(
            f'Device code requested: user_code={user_code}, '
            f'device_code={device_code[:8]}..., expires_in={expires_in}s'
        )

        return DeviceCodeResponse(
            device_code=device_code,
            user_code=user_code,
            verification_uri=f'{base_url}/device',
            expires_in=expires_in,
            interval=5,  # Poll every 5 seconds
        )

    except Exception as e:
        logger.error(f'Error generating device code: {e}', exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to generate device code',
        )


@router.post(
    '/device/token',
    response_model=DeviceTokenSuccessResponse | DeviceTokenPendingResponse,
    responses={
        200: {
            'description': 'Authorization successful or pending',
            'content': {
                'application/json': {
                    'examples': {
                        'success': {
                            'summary': 'Authorization complete',
                            'value': {'api_key': 'ohsk_...'},
                        },
                        'pending': {
                            'summary': 'Authorization pending',
                            'value': {'status': 'pending'},
                        },
                    }
                }
            },
        },
        400: {
            'description': 'Error (expired, denied, etc.)',
            'model': DeviceTokenErrorResponse,
        },
    },
)
async def poll_device_token(
    token_request: DeviceTokenRequest,
    db: Session = Depends(get_db),
) -> DeviceTokenSuccessResponse | DeviceTokenPendingResponse:
    """Poll for device authorization completion.

    The CLI repeatedly calls this endpoint to check if the user has
    authorized the device.

    Args:
        token_request: Request containing device_code
        db: Database session

    Returns:
        API key if authorized, pending status otherwise

    Raises:
        HTTPException: If device code is invalid, expired, or denied
    """
    store = DeviceAuthStore(db)
    session = store.get_session_by_device_code(token_request.device_code)

    if not session:
        logger.warning(
            f'Invalid device code: {token_request.device_code[:8]}...'
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={'error': 'invalid_grant', 'error_description': 'Invalid device code'},
        )

    # Check if expired
    if store.is_session_expired(token_request.device_code):
        logger.info(
            f'Expired device code: user_code={session.user_code}, '
            f'device_code={token_request.device_code[:8]}...'
        )
        session.status = 'expired'
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                'error': 'expired_token',
                'error_description': 'Device code has expired',
            },
        )

    # Check if denied
    if session.status == 'denied':
        logger.info(
            f'Denied device authorization: user_code={session.user_code}, '
            f'device_code={token_request.device_code[:8]}...'
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                'error': 'access_denied',
                'error_description': 'User denied the authorization request',
            },
        )

    # Check if authorized
    if session.status == 'authorized' and session.api_key:
        logger.info(
            f'Device authorized: user_code={session.user_code}, '
            f'user_id={session.user_id}, device_code={token_request.device_code[:8]}...'
        )
        return DeviceTokenSuccessResponse(api_key=session.api_key)

    # Still pending
    logger.debug(
        f'Device authorization pending: user_code={session.user_code}, '
        f'device_code={token_request.device_code[:8]}...'
    )
    return DeviceTokenPendingResponse(status='pending')


# HTML page for device verification
# This is a simple page where users enter their user code

DEVICE_VERIFICATION_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Authorization - OpenHands Cloud</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 500px;
            width: 100%;
            padding: 40px;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo h1 {
            font-size: 28px;
            color: #333;
            margin-bottom: 8px;
        }
        .logo p {
            color: #666;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 24px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            font-size: 18px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            text-transform: uppercase;
            letter-spacing: 2px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            width: 100%;
            padding: 14px;
            font-size: 16px;
            font-weight: 600;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .btn:active {
            transform: translateY(0);
        }
        .help-text {
            margin-top: 20px;
            padding: 16px;
            background: #f5f5f5;
            border-radius: 8px;
            font-size: 14px;
            color: #666;
        }
        .help-text strong {
            color: #333;
        }
        .error {
            background: #fee;
            border: 1px solid #fcc;
            color: #c33;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
        }
        .success {
            background: #efe;
            border: 1px solid #cfc;
            color: #3c3;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>🔐 Device Authorization</h1>
            <p>OpenHands Cloud</p>
        </div>

        <form id="deviceForm" method="POST" action="/api/v1/auth/device/authorize">
            <div class="form-group">
                <label for="userCode">Enter your code:</label>
                <input 
                    type="text" 
                    id="userCode" 
                    name="user_code" 
                    placeholder="XXXX-XXXX" 
                    maxlength="9"
                    pattern="[A-Z0-9]{4}-[A-Z0-9]{4}"
                    required
                    autofocus
                />
            </div>

            <button type="submit" class="btn">Authorize Device</button>
        </form>

        <div class="help-text">
            <strong>What is this?</strong><br>
            You're seeing this because you ran <code>openhands login</code> in your terminal. 
            Enter the code displayed in your terminal to authorize this device.
        </div>
    </div>

    <script>
        // Auto-format input with dash
        const input = document.getElementById('userCode');
        input.addEventListener('input', (e) => {
            let value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
            if (value.length > 4) {
                value = value.slice(0, 4) + '-' + value.slice(4, 8);
            }
            e.target.value = value;
        });
    </script>
</body>
</html>
"""


@device_page_router.get('/device', response_class=HTMLResponse, include_in_schema=False)
async def device_verification_page() -> HTMLResponse:
    """Serve the device verification page.

    This page is where users enter their user code to authorize the device.

    Returns:
        HTML page for device verification
    """
    return HTMLResponse(content=DEVICE_VERIFICATION_HTML)


class DeviceAuthorizeRequest(BaseModel):
    """Request model for device authorization."""

    user_code: str


@router.post('/device/authorize')
async def authorize_device(
    request: DeviceAuthorizeRequest,
    db: Session = Depends(get_db),
    # TODO: Add authentication dependency here
    # current_user: User = Depends(get_current_user),
) -> dict:
    """Authorize a device (called from the web page).

    This endpoint is called when a user enters their code and clicks "Authorize"
    on the device verification page.

    Args:
        request: Request containing user_code
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If user code is invalid or expired
    """
    store = DeviceAuthStore(db)
    session = store.get_session_by_user_code(request.user_code)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid code',
        )

    # Check if expired
    if store.is_session_expired(session.device_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Code has expired',
        )

    # TODO: Get actual user ID from authentication
    # user_id = current_user.id
    user_id = 'temporary_user_id'  # Placeholder

    # TODO: Generate actual API key
    # api_key = generate_api_key_for_user(user_id)
    api_key = f'ohsk_demo_{secrets.token_urlsafe(32)}'  # Placeholder

    # Authorize the session
    success = store.authorize_session(request.user_code, user_id, api_key)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Failed to authorize device',
        )

    logger.info(
        f'Device authorized via web: user_code={request.user_code}, '
        f'user_id={user_id}'
    )

    return {
        'status': 'success',
        'message': 'Device authorized successfully! You can now return to your terminal.',
    }
