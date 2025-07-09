# Real-Time Communication (RTC) MVP

![Project: Real-Time Communication](https://img.shields.io/badge/Project-Real--Time%20Communication-blue)
![Python 3.11](https://img.shields.io/badge/Python-3.11-blueviolet)
![Framework: FastAPI](https://img.shields.io/badge/Framework-FastAPI-green)
![Database: PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-orange)
![Cache: Redis](https://img.shields.io/badge/Cache-Redis-red)

This project is a minimal viable product (MVP) for a real-time communication platform built using FastAPI, PostgreSQL, Redis, and WebSockets. The architecture is designed to support real-time messaging, room management, and user authentication.

## Demo

### Login Page
![Login Page](demo/login.png)

### Home Page
![Home Page](demo/home.png)

### Direct Message (DM) Page
![Direct Message Page](demo/dm.png)

### Push Notification
![Push Notification](demo/push_notif.png)

## Architecture Overview

The project follows a modular structure with the following key components:

### Core Components
- **`app/core/`**: Contains configuration, error handling, and security settings.
  - `config.py`: Manages environment variables and application settings.
  - `error_handler.py`: Custom exception handling for the API.
  - `security.py`: Handles JWT token generation and validation.

### API Endpoints
- **`app/api/`**: Defines the API routes for different functionalities.
  - `auth.py`: Handles user authentication and token generation.
  - `rooms.py`: Manages room creation, joining, and listing.
  - `messages.py`: Handles real-time messaging within rooms.
  - `users.py`: Manages user-related operations.
  - `websocket.py`: Handles WebSocket connections for real-time communication.

### Database
- **`app/database/`**: Contains database connection and initialization logic.
  - `postgres.py`: Manages PostgreSQL database connections.
  - `redis.py`: Manages Redis connections for WebSocket message broadcasting.

### Services
- **`app/services/`**: Implements the business logic for different functionalities.
  - `auth_service.py`: Handles user authentication logic.
  - `chat_service.py`: Manages message sending and retrieval.
  - `room_service.py`: Handles room-related operations.
  - `user_service.py`: Manages user-related operations.

### Models and Schemas
- **`app/models/`**: Defines the database models using SQLAlchemy.
  - `user.py`: User model.
  - `room.py`: Room model.
  - `message.py`: Message model.
- **`app/schemas/`**: Defines Pydantic schemas for request/response validation.

### Utilities
- **`app/utils/`**: Contains utility functions and middleware.
  - `websocket_manager.py`: Manages WebSocket connections and message broadcasting.
  - `token.py`: Handles JWT token generation and validation.

## Setup Instructions

### Prerequisites
- Python 3.11
- Docker
- Docker Compose

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/purushothdl/rtc_proto.git
   cd rtc_proto
   ```

2. Create a `.env` file in the root directory with the following variables:
   ```env
   DATABASE_URL=postgresql://user:password@postgres:5432/dbname
   REDIS_URL=redis://redis:6379/0
   JWT_SECRET=your_jwt_secret
   ```

3. Build and start the Docker containers:
   ```bash
   docker-compose up --build
   ```

4. The application will be available at `http://localhost:8000`.

### API Documentation
Once the application is running, you can access the interactive API documentation at `http://localhost:8000/docs`.





