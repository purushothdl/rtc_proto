import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from ..core.log_config import logger

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Request to {request.url.path} took {elapsed_time:.4f} seconds.")
        
        return response
