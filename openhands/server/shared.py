"""Shared server dependencies - DEPRECATED.

This module is deprecated and maintained only for backward compatibility.
New code should use the context system from openhands.server.context instead.

from openhands.core.config import load_app_config
from openhands.server.session import SessionManager
from openhands.storage import get_file_store

print(f'Initializing at {__file__}')
print(f'Module name: {__name__}')

Migration guide:
    # Old way (deprecated)
    from openhands.server.shared import config, server_config

config = load_app_config()
file_store = get_file_store(config.file_store, config.file_store_path)



sio = socketio.AsyncServer(
    async_mode='asgi', cors_allowed_origins='*', client_manager=client_manager
)

session_manager = SessionManager(sio, config, file_store)
