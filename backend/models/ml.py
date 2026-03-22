"""ORM models for ML model registry, training runs, and inference logs."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import relationship

from backend.database import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    model_type = Column(Text, nullable=False)  # classification, embedding, vlm
    framework = Column(Text)  # pytorch, tensorflow
    task_type = Column(Text)  # ship_classification, embedding, etc.
    path = Column(Text, nullable=False)
    input_size = Column(Text)  # e.g. "224x224"
    label_map_json = Column(Text)  # JSON: {"0": "Container Ship", ...}
    metrics_json = Column(Text)  # JSON: {"accuracy": 0.996, ...}
    is_active = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    training_runs = relationship("TrainingRun", back_populates="model")
    inference_logs = relationship("InferenceLog", back_populates="model")


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("ml_models.id"), index=True)
    dataset_version = Column(Text)
    config_json = Column(Text)
    metrics_json = Column(Text)
    status = Column(Text)  # pending, running, completed, failed
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    log_path = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    model = relationship("MLModel", back_populates="training_runs")


class InferenceLog(Base):
    __tablename__ = "inference_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("ml_models.id"), index=True)
    image_id = Column(Integer, ForeignKey("images.id"), index=True)
    input_path = Column(Text)
    top_prediction = Column(Text)
    confidence = Column(Float)
    topk_json = Column(Text)  # JSON array of top-k predictions
    duration_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    model = relationship("MLModel", back_populates="inference_logs")
    image = relationship("Image", back_populates="inference_logs")


class SyntheticJob(Base):
    __tablename__ = "synthetic_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ship_class = Column(Text)
    source_count = Column(Integer)
    generated_count = Column(Integer)
    method = Column(Text)
    config_json = Column(Text)
    status = Column(Text)
    output_dir = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
