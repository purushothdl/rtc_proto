
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.exceptions import BaseAPIException

# Custom exception handler for BaseAPIException and its subclasses
async def custom_exception_handler(request: Request, exc: BaseAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )
