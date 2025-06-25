import asyncio
import sys
from pathlib import Path
from uuid import UUID
import logging

# Add the project root directory to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from app.database.postgres import get_db_session
from app.services.notification_service import NotificationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    user_id = UUID("41ddceb4-cbf9-4fa7-bb4a-437c5471d30b")

    async for session in get_db_session():
        notification_service = NotificationService(session)
        
        try:
            await notification_service.send_notification_to_user(
                user_id,
                title="Test Notification",
                body="This is a test notification from the server."
            )
            logger.info("Notification sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        loop.close()