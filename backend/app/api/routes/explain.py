from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.api.dependencies import existing_user
from core.database import get_db
from services import llm_explainer, user_service

router = APIRouter(prefix="/scoring", tags=["explainability"])


@router.get("/{user_id}/explain")
def explain(user: models.User = Depends(existing_user), db: Session = Depends(get_db)):
    """LLM-written plain-language explanation of the user's current score."""
    scored = user_service.score_user(db, user)
    try:
        narrative = llm_explainer.explain_score(scored)
    except llm_explainer.LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return {"user_id": user.user_id, "credit_score": scored["credit_score"], **narrative}
