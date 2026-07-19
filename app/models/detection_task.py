import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.core.time_utils import shanghai_now

class DetectionTask(Base):
    __tablename__ = "detection_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    input_path = Column(String, nullable=True)
    output_path = Column(String, nullable=True)
    parameters = Column(JSON, nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed
    created_at = Column(DateTime, default=shanghai_now)

    # Relationships
    model = relationship("Model")
