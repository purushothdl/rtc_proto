from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.error_handler import custom_exception_handler
from app.core.exceptions import BaseAPIException

from app.api.auth import router as auth_router
from app.api.rooms import router as room_router
from app.api.messages import router as message_router
from app.api.users import router as user_router
from app.api.websocket import router as websocket_router 
from app.globals import websocket_manager
from app.database.postgres import initialize_db
from app.utils.timing_middleware import TimingMiddleware
from app.utils.websocket_manager import WebsocketManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_db()
    await websocket_manager.init_redis()
    yield
    await websocket_manager.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.add_exception_handler(BaseAPIException, custom_exception_handler)
app.add_middleware(TimingMiddleware)

app.include_router(auth_router)
app.include_router(room_router)
app.include_router(message_router)
app.include_router(user_router)
app.include_router(websocket_router)