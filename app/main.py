from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.error_handler import custom_exception_handler
from app.core.exceptions import BaseAPIException

from app.api.auth import router as auth_router
from app.utils.timing_middleware import TimingMiddleware

app = FastAPI()

app.add_exception_handler(BaseAPIException, custom_exception_handler)
app.add_middleware(TimingMiddleware)

app.include_router(auth_router)
