from sqlalchemy import Column
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid

@as_declarative()
class Base:
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)