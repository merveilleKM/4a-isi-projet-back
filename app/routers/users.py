from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/{uid}", summary="Update specific information for current user")
def modify(uid: int, session: Session = Depends(get_session)):
    # Version mock : on remplira avec la vraie logique plus tard
    return {"uid": uid, "message": "not implemented"}