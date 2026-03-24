"""Ship detection service — detect and crop ships from images using Faster R-CNN.

Uses torchvision's Faster R-CNN pre-trained on COCO (class 9 = "boat").
Crops the largest detected ship as primary, secondary ships as additional crops.
"""

import json
import os
import threading
from pathlib import Path

import structlog
from PIL import Image as PILImage

from backend.database import SessionLocal
from backend.models.image import Image, ImageAnnotation
from backend.models.ship import Ship

log = structlog.get_logger()

# COCO class 9 = "boat" (1-indexed in torchvision COCO)
BOAT_CLASS_ID = 9

# Global state
_detection_model = None
_detection_status = {"running": False, "progress": 0, "total": 0, "message": "Idle"}


def load_detection_model():
    """Lazy-load Faster R-CNN with COCO weights."""
    global _detection_model
    if _detection_model is not None:
        return True
    try:
        import torch  # noqa: F811 — lazy import to avoid DLL issues at startup
        from torchvision.models.detection import fasterrcnn_resnet50_fpn, FasterRCNN_ResNet50_FPN_Weights
        log.info("loading_detection_model", model="fasterrcnn_resnet50_fpn")
        _detection_model = fasterrcnn_resnet50_fpn(weights=FasterRCNN_ResNet50_FPN_Weights.DEFAULT)
        _detection_model.eval()
        log.info("detection_model_loaded")
        return True
    except Exception as e:
        log.error("detection_model_load_failed", error=str(e))
        return False


def detect_ships_in_image(
    image_path: str,
    confidence_threshold: float = 0.5,
) -> list[dict]:
    """Detect ships/boats in an image.

    Returns list of detections sorted by area (largest first):
    [{"bbox": [x1, y1, x2, y2], "confidence": float, "area": int, "rank": int}]
    """
    if not load_detection_model():
        return []

    try:
        img = PILImage.open(image_path).convert("RGB")
    except Exception as e:
        log.error("image_open_failed", path=image_path, error=str(e))
        return []

    import torch
    from torchvision.transforms.functional import to_tensor
    tensor = to_tensor(img)

    with torch.no_grad():
        predictions = _detection_model([tensor])[0]

    detections = []
    boxes = predictions["boxes"]
    labels = predictions["labels"]
    scores = predictions["scores"]

    for i in range(len(labels)):
        if labels[i].item() == BOAT_CLASS_ID and scores[i].item() >= confidence_threshold:
            box = boxes[i].tolist()  # [x1, y1, x2, y2]
            area = (box[2] - box[0]) * (box[3] - box[1])
            detections.append({
                "bbox": [round(v, 1) for v in box],
                "confidence": round(scores[i].item(), 4),
                "area": round(area),
            })

    # Sort by area descending, assign rank
    detections.sort(key=lambda d: d["area"], reverse=True)
    for rank, det in enumerate(detections, 1):
        det["rank"] = rank

    return detections


def crop_detections(
    image_path: str,
    detections: list[dict],
    output_dir: str,
    padding_pct: float = 0.05,
) -> list[dict]:
    """Crop each detection from the image with padding.

    Returns list of crop metadata:
    [{"crop_path": str, "rank": int, "bbox": list, "width": int, "height": int, "file_size": int}]
    """
    try:
        img = PILImage.open(image_path).convert("RGB")
    except Exception as e:
        log.error("crop_image_open_failed", path=image_path, error=str(e))
        return []

    img_w, img_h = img.size
    os.makedirs(output_dir, exist_ok=True)
    stem = Path(image_path).stem

    crops = []
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        bw = x2 - x1
        bh = y2 - y1
        pad_x = bw * padding_pct
        pad_y = bh * padding_pct

        # Apply padding, clamp to image bounds
        cx1 = max(0, x1 - pad_x)
        cy1 = max(0, y1 - pad_y)
        cx2 = min(img_w, x2 + pad_x)
        cy2 = min(img_h, y2 + pad_y)

        cropped = img.crop((cx1, cy1, cx2, cy2))
        crop_name = f"{stem}_crop{det['rank']}.jpg"
        crop_path = os.path.join(output_dir, crop_name)
        cropped.save(crop_path, "JPEG", quality=95)

        file_size = os.path.getsize(crop_path)
        crops.append({
            "crop_path": crop_path,
            "rank": det["rank"],
            "confidence": det["confidence"],
            "bbox": det["bbox"],
            "width": int(cx2 - cx1),
            "height": int(cy2 - cy1),
            "file_size": file_size,
        })

        log.info("crop_saved", path=crop_path, rank=det["rank"],
                 size=f"{file_size // 1024}KB", confidence=det["confidence"])

    return crops


def detect_and_crop_for_ship(
    ship_id: int,
    confidence_threshold: float = 0.5,
    padding_pct: float = 0.05,
) -> dict:
    """Process all images of a ship: detect, annotate, crop.

    Returns stats dict.
    """
    db = SessionLocal()
    stats = {"images_processed": 0, "detections_found": 0, "crops_created": 0}

    try:
        # Only process original images (not crops)
        images = (
            db.query(Image)
            .filter(Image.ship_id == ship_id, Image.parent_image_id.is_(None))
            .all()
        )

        if not images:
            log.warning("no_images_for_ship", ship_id=ship_id)
            return stats

        for img_record in images:
            if not img_record.file_path or not os.path.exists(img_record.file_path):
                log.warning("image_file_missing", image_id=img_record.id, path=img_record.file_path)
                continue

            # Delete previous crops and annotations for this image
            old_crops = db.query(Image).filter(Image.parent_image_id == img_record.id).all()
            for oc in old_crops:
                if oc.file_path and os.path.exists(oc.file_path):
                    try:
                        os.remove(oc.file_path)
                    except OSError:
                        pass
                db.delete(oc)
            db.query(ImageAnnotation).filter(
                ImageAnnotation.image_id == img_record.id,
                ImageAnnotation.annotation_type == "ship_detection",
            ).delete()
            db.flush()

            # Run detection
            detections = detect_ships_in_image(img_record.file_path, confidence_threshold)
            stats["images_processed"] += 1
            stats["detections_found"] += len(detections)

            if not detections:
                log.info("no_ships_detected", image_id=img_record.id)
                continue

            # Store annotations
            for det in detections:
                db.add(ImageAnnotation(
                    image_id=img_record.id,
                    annotation_type="ship_detection",
                    bbox_json=json.dumps(det["bbox"]),
                    confidence=det["confidence"],
                ))

            # Determine crop output directory
            parent_dir = os.path.dirname(img_record.file_path)
            crop_dir = os.path.join(parent_dir, "crops")

            # Crop
            crops = crop_detections(img_record.file_path, detections, crop_dir, padding_pct)

            # Create Image records for crops
            for crop_info in crops:
                crop_image = Image(
                    ship_id=ship_id,
                    file_path=crop_info["crop_path"],
                    file_name=os.path.basename(crop_info["crop_path"]),
                    source_name="detection_crop",
                    source_url=img_record.source_url,
                    width=crop_info["width"],
                    height=crop_info["height"],
                    file_size=crop_info["file_size"],
                    parent_image_id=img_record.id,
                    is_primary_crop=1 if crop_info["rank"] == 1 else 0,
                    crop_rank=crop_info["rank"],
                )
                db.add(crop_image)
                stats["crops_created"] += 1

            db.commit()

        log.info("ship_detection_complete", ship_id=ship_id, **stats)
        return stats

    except Exception as e:
        log.error("ship_detection_failed", ship_id=ship_id, error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


def run_batch_detection(
    ship_ids: list[int] | None = None,
    confidence_threshold: float = 0.5,
):
    """Background thread: detect ships in all or selected ship entities."""
    global _detection_status
    db = SessionLocal()

    try:
        if ship_ids:
            ships = db.query(Ship).filter(Ship.id.in_(ship_ids)).all()
        else:
            ships = db.query(Ship).all()

        total = len(ships)
        _detection_status = {"running": True, "progress": 0, "total": total, "message": "Starte Erkennung..."}

        total_stats = {"images_processed": 0, "detections_found": 0, "crops_created": 0}

        for i, ship in enumerate(ships):
            _detection_status["progress"] = i
            _detection_status["message"] = f"Verarbeite {ship.name} ({i + 1}/{total})"

            try:
                stats = detect_and_crop_for_ship(ship.id, confidence_threshold)
                for k in total_stats:
                    total_stats[k] += stats[k]
            except Exception as e:
                log.error("batch_detection_ship_failed", ship_id=ship.id, error=str(e))

        _detection_status = {
            "running": False,
            "progress": total,
            "total": total,
            "message": (
                f"Fertig: {total_stats['images_processed']} Bilder, "
                f"{total_stats['detections_found']} Schiffe erkannt, "
                f"{total_stats['crops_created']} Crops erstellt"
            ),
        }
        log.info("batch_detection_complete", **total_stats)

    except Exception as e:
        _detection_status = {"running": False, "progress": 0, "total": 0, "message": f"Fehler: {e}"}
        log.error("batch_detection_failed", error=str(e))
    finally:
        db.close()


def start_batch_detection(
    ship_ids: list[int] | None = None,
    confidence_threshold: float = 0.5,
):
    """Launch batch detection in a background thread."""
    thread = threading.Thread(
        target=run_batch_detection,
        args=(ship_ids, confidence_threshold),
        daemon=True,
    )
    thread.start()


def get_detection_status() -> dict:
    return dict(_detection_status)
