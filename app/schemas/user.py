from pydantic import BaseModel, Field
from enum import Enum
class DeviceType(str, Enum):
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"

class FCMTokenCreate(BaseModel):
    token: str
    device_type: DeviceType = Field(default=DeviceType.WEB, description="The type of the client device")