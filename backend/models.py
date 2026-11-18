"""
LabelIntel — Database ORM Models
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text
from backend.database import Base


class InspectionModel(Base):
    """Stores full audit records of packaged commodity label inspections."""
    __tablename__ = "inspections"

    id = Column(String(64), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    category = Column(String(64), nullable=True)
    status = Column(String(32), default="COMPLETED")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Dimensional metadata
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)

    # File identification & hash caching
    file_hash = Column(String(64), index=True, nullable=True)

    # File storage paths
    image_path = Column(String(512), nullable=False)
    annotated_path = Column(String(512), nullable=True)

    # Serialized JSON reports
    quality_json = Column(Text, nullable=True)
    ocr_blocks_json = Column(Text, nullable=True)
    fused_declarations_json = Column(Text, nullable=True)
    compliance_json = Column(Text, nullable=True)
