from core.database import get_db
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models


def existing_user(user_id: str, db: Session = Depends(get_db)) -> models.User:
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    return user


def existing_lender(lender_id: int, db: Session = Depends(get_db)) -> models.Lender:
    lender = db.get(models.Lender, lender_id)
    if lender is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "lender not found")
    return lender
