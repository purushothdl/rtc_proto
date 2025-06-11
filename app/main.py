from fastapi import FastAPI
from app.core.error_handler import custom_exception_handler
from app.core.exceptions import BaseAPIException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router

app = FastAPI()

app.add_exception_handler(BaseAPIException, custom_exception_handler)

app.include_router(auth_router)
