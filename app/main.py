from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.error_handler import custom_exception_handler
from app.core.exceptions import BaseAPIException

from app.api.auth import router as auth_router
from app.api.rooms import router as room_router
from app.api.messages import router as message_router
from app.database.postgres import initialize_db
from app.utils.timing_middleware import TimingMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_exception_handler(BaseAPIException, custom_exception_handler)
app.add_middleware(TimingMiddleware)

app.include_router(auth_router)
app.include_router(room_router)
app.include_router(message_router)
