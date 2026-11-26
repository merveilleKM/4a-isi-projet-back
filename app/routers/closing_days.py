import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.database import get_session
from app.models import ClosingDay
from app.schemas import ClosingDayCreate, ClosingDayRead
from app.security import get_current_admin

router = APIRouter(prefix="/closing-days", tags=["closing-days"])


@router.get("/", response_model=list[ClosingDayRead], summary="Calendrier des jours fermés")
def list_closing_days(
    date_from: Optional[datetime.date] = None,
    date_to: Optional[datetime.date] = None,
    session: Session = Depends(get_session),
):
    query = select(ClosingDay).order_by(ClosingDay.date)
    if date_from:
        query = query.where(ClosingDay.date >= date_from)
    if date_to:
        query = query.where(ClosingDay.date <= date_to)
    return session.exec(query).all()


@router.get("/upcoming", response_model=list[ClosingDayRead], summary="Annonce des prochains jours fermés")
def upcoming_closing_days(session: Session = Depends(get_session)):
    query = (
        select(ClosingDay)
        .where(ClosingDay.date >= datetime.date.today())
        .order_by(ClosingDay.date)
    )
    return session.exec(query).all()


@router.post("/", response_model=ClosingDayRead, status_code=201, summary="Ajouter un jour fermé")
def create_closing_day(
    data: ClosingDayCreate,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),  # TODO security
):
    existing = session.exec(select(ClosingDay).where(ClosingDay.date == data.date)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ce jour est déjà marqué comme fermé")
    closing_day = ClosingDay.model_validate(data)
    session.add(closing_day)
    session.commit()
    session.refresh(closing_day)
    return closing_day


@router.delete("/{closing_day_id}", status_code=204, summary="Supprimer un jour fermé")
def delete_closing_day(
    closing_day_id: int,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),  # TODO security
):
    closing_day = session.get(ClosingDay, closing_day_id)
    if closing_day is None:
        raise HTTPException(status_code=404, detail="Jour fermé introuvable")
    session.delete(closing_day)
    session.commit()
    return Response(status_code=204)