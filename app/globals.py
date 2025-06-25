from .utils.websocket_manager import WebsocketManager
from .core.config import settings

# This is the single, shared instance of the WebsocketManager.
# It is created once when the module is first imported.
websocket_manager = WebsocketManager(settings.redis_url)