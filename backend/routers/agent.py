"""Agent API endpoints — designed for programmatic/AI agent access."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.services.agent_service import execute_action, get_capabilities, get_system_context

router = APIRouter(prefix="/api/agent", tags=["agent"])


def _verify_api_key(x_api_key: str | None = Header(None)):
    """Simple API key verification. Skipped if SECRET_KEY is default."""
    if settings.SECRET_KEY != "change_me_in_production":
        if not x_api_key or x_api_key != settings.SECRET_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---- System Context ----

@router.get("/context", dependencies=[Depends(_verify_api_key)])
def agent_context(db: Session = Depends(get_db)):
    """Full system state for agent decision-making.

    Returns data counts, active model, running jobs, type distribution, data gaps.
    """
    ctx = get_system_context(db)
    return {"status": "success", "data": ctx}


@router.get("/capabilities", dependencies=[Depends(_verify_api_key)])
def agent_capabilities():
    """List all available agent actions and their parameters."""
    caps = get_capabilities()
    return {"status": "success", "data": caps}


# ---- Action Execution ----

class ActionRequest(BaseModel):
    action: str
    params: dict[str, Any] = {}


@router.post("/action", dependencies=[Depends(_verify_api_key)])
def agent_action(req: ActionRequest, db: Session = Depends(get_db)):
    """Execute a registered agent action.

    Example: `{"action": "predict", "params": {"image_path": "/path/to/img.jpg"}}`
    """
    return execute_action(req.action, req.params, db)


# ---- Training Control ----

class TrainingRequest(BaseModel):
    dataset_dir: str
    epochs: int = 5
    batch_size: int = 8
    learning_rate: float = 5e-5


@router.post("/training/start", dependencies=[Depends(_verify_api_key)])
def agent_training_start(req: TrainingRequest, db: Session = Depends(get_db)):
    """Start model training via agent API."""
    result = execute_action("train_model", req.model_dump(), db)
    return result


@router.get("/training/status", dependencies=[Depends(_verify_api_key)])
def agent_training_status():
    """Get training status."""
    from backend.services.ml_service import get_training_status
    status = get_training_status()
    return {"status": "success", "data": status}


# ---- Dataset Management ----

@router.post("/dataset/build", dependencies=[Depends(_verify_api_key)])
def agent_dataset_build(db: Session = Depends(get_db)):
    """Get dataset statistics for building/rebuilding."""
    result = execute_action("rebuild_dataset", {}, db)
    return result


@router.post("/dataset/augment", dependencies=[Depends(_verify_api_key)])
def agent_dataset_augment(
    source_dir: str,
    num_per_image: int = 5,
    db: Session = Depends(get_db),
):
    """Generate synthetic data via agent API."""
    result = execute_action("generate_synthetic", {
        "source_dir": source_dir,
        "num_per_image": num_per_image,
    }, db)
    return result


# ---- Inference ----

class InferenceRequest(BaseModel):
    image_path: str


@router.post("/inference", dependencies=[Depends(_verify_api_key)])
def agent_inference(req: InferenceRequest, db: Session = Depends(get_db)):
    """Run inference on a single image."""
    return execute_action("predict", {"image_path": req.image_path}, db)


# ---- Self-Improvement ----

class ImproveRequest(BaseModel):
    goal: str = "improve_accuracy"
    constraints: dict[str, Any] = {}


@router.post("/improve", dependencies=[Depends(_verify_api_key)])
def agent_improve(req: ImproveRequest, db: Session = Depends(get_db)):
    """Analyze system and suggest improvements.

    Returns data gaps, training suggestions, and recommended actions.
    """
    ctx = get_system_context(db)

    suggestions = []

    # Check data gaps
    if ctx["data_gaps"]:
        gap_types = [g["type"] for g in ctx["data_gaps"]]
        suggestions.append({
            "type": "data_collection",
            "message": f"Klassen mit wenigen Bildern: {', '.join(gap_types)}",
            "action": "generate_synthetic",
        })

    # Check if model is active
    if not ctx["model"]["is_active"]:
        suggestions.append({
            "type": "model_setup",
            "message": "Kein aktives Modell gefunden",
            "action": "train_model",
        })

    # Check unclassified images
    unclassified = ctx["data"]["downloaded"] - ctx["data"]["classified"]
    if unclassified > 0:
        suggestions.append({
            "type": "classification",
            "message": f"{unclassified} Bilder noch nicht klassifiziert",
            "action": "predict",
        })

    return {
        "status": "success",
        "data": {
            "goal": req.goal,
            "current_state": {
                "ships": ctx["data"]["ships"],
                "images": ctx["data"]["images"],
                "classified": ctx["data"]["classified"],
                "model": ctx["model"]["name"],
            },
            "suggestions": suggestions,
            "data_gaps": ctx["data_gaps"],
        },
    }
