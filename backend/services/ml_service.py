"""ML service — thin wrapper around ml_engine.py.

Preserves all existing ML logic without rewriting it.
"""

import os
import sys

# Add project root to path so ml_engine can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def classify_image(image_data):
    """Classify an image. Accepts bytes, file path, or PIL Image."""
    from ml_engine import classify_image as _classify
    return _classify(image_data)


def get_model_info() -> dict:
    """Get model information."""
    from ml_engine import get_model_info as _get_info
    return _get_info()


def get_training_status() -> dict:
    """Get current training status."""
    from ml_engine import get_training_status as _get_status
    return _get_status()


def start_training(dataset_dir: str, epochs: int = 5, batch_size: int = 8,
                   learning_rate: float = 5e-5) -> dict:
    """Start model training."""
    from ml_engine import start_training as _start
    return _start(dataset_dir, epochs=epochs, batch_size=batch_size, learning_rate=learning_rate)


def get_available_datasets() -> dict:
    """List available datasets for training."""
    from ml_engine import get_available_datasets as _get_datasets
    return _get_datasets()


def get_augment_status() -> dict:
    """Get current augmentation status."""
    from ml_engine import get_augment_status as _get_status
    return _get_status()


def augment_images(source_dir: str, num_per_image: int = 5,
                   transforms_config: dict | None = None) -> dict:
    """Start image augmentation."""
    from ml_engine import augment_images as _augment
    return _augment(source_dir, num_per_image=num_per_image, transforms_config=transforms_config)
