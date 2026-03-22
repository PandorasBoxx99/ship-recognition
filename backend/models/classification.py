"""ORM model for classification results."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from backend.database import Base


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey("items.id"), index=True)
    image_path = Column(Text)
    predicted_type = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    all_predictions = Column(Text)  # JSON
    model_name = Column(String, default="vit-ship-classifier")
    created_at = Column(DateTime, server_default=func.now())

    item = relationship("Item", back_populates="classifications")
