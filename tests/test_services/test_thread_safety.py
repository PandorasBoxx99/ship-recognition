"""Thread-safety guards: a second start must be rejected while one is running.

These verify the atomic check-and-set in the start functions — the guard returns
before any heavy work, so no real ML/DB is needed.
"""

import ml_engine
from backend.services import detection_service


def test_training_rejects_concurrent_start():
    ml_engine._training_status["running"] = True
    try:
        result = ml_engine.start_training("/does/not/exist")
        assert isinstance(result, dict) and "error" in result
    finally:
        ml_engine._training_status["running"] = False


def test_augmentation_rejects_concurrent_start():
    ml_engine._augment_status["running"] = True
    try:
        result = ml_engine.augment_images("/does/not/exist")
        assert isinstance(result, dict) and "error" in result
    finally:
        ml_engine._augment_status["running"] = False


def test_batch_detection_rejects_concurrent_start():
    detection_service._detection_status["running"] = True
    try:
        assert detection_service.start_batch_detection() is False
    finally:
        detection_service._detection_status["running"] = False
