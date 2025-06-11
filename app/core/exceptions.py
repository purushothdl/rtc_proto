# app/core/exceptions.py

from fastapi import HTTPException, status

# Base Exception
class BaseAPIException(HTTPException):
    """Base class for all custom API exceptions."""
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


# Authentication & Authorization Exceptions
class InvalidCredentialsException(BaseAPIException):
    """Exception raised when credentials are invalid."""
    def __init__(self, detail="Invalid username or password"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class UserAlreadyExistsException(BaseAPIException):
    """Exception raised when a user already exists."""
    def __init__(self, detail="Username or email already exists"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class UnauthorizedAccessException(BaseAPIException):
    """Exception raised for unauthorized access attempts."""
    def __init__(self, detail="Access denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class TokenExpiredException(BaseAPIException):
    """Exception raised when a token has expired."""
    def __init__(self, detail="Token has expired"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class InvalidTokenException(BaseAPIException):
    """Exception raised when a token is invalid."""
    def __init__(self, detail="Invalid token"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


# User & Profile Exceptions
class UserNotFoundException(BaseAPIException):
    """Exception raised when a user is not found."""
    def __init__(self, detail="User not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ProfileUpdateFailedException(BaseAPIException):
    """Exception raised when updating a user profile fails."""
    def __init__(self, detail="Failed to update profile"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


# Room & Chat Exceptions
class RoomNotFoundException(BaseAPIException):
    """Exception raised when a room is not found."""
    def __init__(self, detail="Room not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class RoomFullException(BaseAPIException):
    """Exception raised when a room has reached its maximum capacity."""
    def __init__(self, detail="Room is full"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class RoomAlreadyExistsException(BaseAPIException):
    """Exception raised when a room with the same name already exists."""
    def __init__(self, detail="Room already exists"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class MessageNotFoundException(BaseAPIException):
    """Exception raised when a message is not found."""
    def __init__(self, detail="Message not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class MessageNotSentException(BaseAPIException):
    """Exception raised when a message fails to send."""
    def __init__(self, detail="Message could not be sent"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


# Notification & WebSocket Exceptions
class NotificationFailedException(BaseAPIException):
    """Exception raised when a notification fails to send."""
    def __init__(self, detail="Notification could not be sent"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class WebSocketConnectionException(BaseAPIException):
    """Exception raised when a WebSocket connection fails."""
    def __init__(self, detail="WebSocket connection failed"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


# Validation & Input Exceptions
class ValidationException(BaseAPIException):
    """Exception raised for validation errors."""
    def __init__(self, detail="Input data validation failed"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class InvalidInputException(BaseAPIException):
    """Exception raised when input data is invalid."""
    def __init__(self, detail="Invalid input data"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


# Database & System Exceptions
class DatabaseConnectionException(BaseAPIException):
    """Exception raised when a database connection fails."""
    def __init__(self, detail="Database connection failed"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class InternalServerErrorException(BaseAPIException):
    """Exception raised for internal server errors."""
    def __init__(self, detail="Internal server error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
