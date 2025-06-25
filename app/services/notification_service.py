import asyncio
import json
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2 import service_account
import google.auth.transport.requests
from uuid import UUID

from app.schemas.user import DeviceType

from ..models.fcm_token import FCMToken

SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']
SERVICE_ACCOUNT_FILE = 'service_account_key.json'

class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_id = self._get_project_id()
        self.fcm_url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        self._access_token = None
        self._credentials = None

    def _get_project_id(self):
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            return json.load(f).get('project_id')

    def _get_access_token(self):
        if not self._credentials:
            self._credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        request = google.auth.transport.requests.Request()
        self._credentials.refresh(request)
        return self._credentials.token

    async def register_fcm_token(self, user_id: UUID, token: str, device_type: DeviceType):
        """
        Registers an FCM token, handling device type and user re-assignment.
        """
        stmt = select(FCMToken).where(FCMToken.token == token)
        result = await self.db.execute(stmt)
        existing_token_record = result.scalar_one_or_none()

        if existing_token_record:
            # Token exists. Update its user_id and device_type if they have changed.
            needs_update = False
            if existing_token_record.user_id != user_id:
                existing_token_record.user_id = user_id
                needs_update = True
            if existing_token_record.device_type != device_type.value:
                existing_token_record.device_type = device_type.value
                needs_update = True
            
            if needs_update:
                print(f"FCM token updated for user {user_id} and device {device_type.value}")

        else:
            print(f"Registering new FCM token for user {user_id} and device {device_type.value}")
            new_token = FCMToken(
                user_id=user_id, 
                token=token, 
                device_type=device_type.value
            )
            self.db.add(new_token)
        
        await self.db.commit()

    async def send_notification_to_user(self, user_id: UUID, title: str, body: str, data: dict = None):
        stmt = select(FCMToken.token, FCMToken.device_type).filter(FCMToken.user_id == user_id)
        result = await self.db.execute(stmt)
        user_devices = result.all()

        if not user_devices:
            return

        headers = {
            'Authorization': f'Bearer {self._get_access_token()}',
            'Content-Type': 'application/json; UTF-8',
        }
        
        async with httpx.AsyncClient() as client:
            tasks = []
            for token, device_type in user_devices:
                
                # Construct a payload specific to the device type
                if device_type == 'web':
                    payload = {
                        "message": {
                            "token": token,
                            "notification": {"title": title, "body": body},
                            "data": data or {}
                        }
                    }
                elif device_type in ['android', 'ios']:
                    # For mobile, you might send a silent data-only push with a badge count
                    payload = {
                        "message": {
                            "token": token,
                            "data": {
                                **(data or {}),
                                "title": title, # Custom data keys
                                "body": body,
                                "badge": "1",
                                "sound": "default"
                            }
                        }
                    }
                else:
                    continue

                # Add the request to a list of tasks to be run concurrently
                tasks.append(client.post(self.fcm_url, headers=headers, json=payload))

            if tasks:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for i, response in enumerate(responses):
                    if isinstance(response, Exception):
                        print(f"Failed to send notification to token {user_devices[i][0][:15]}...: {response}")