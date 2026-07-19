import uuid
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base
from app.core.time_utils import shanghai_now

class Model(Base):
    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    path = Column(String, nullable=False)
    type = Column(String, nullable=False)  # yolov8*, yolo11*, yolov13*
    task = Column(String, nullable=False, default="detect")  # detect, segment, classify, pose
    created_at = Column(DateTime, default=shanghai_now)
    updated_at = Column(DateTime, default=shanghai_now, onupdate=shanghai_now)
    source = Column(String, default="upload")  # upload, training
