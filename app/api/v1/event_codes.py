from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.event_code import EventCodeCreate, EventCodeRead
from app.services.event_code_service import EventCodeService

router = APIRouter(prefix="/v1/event-codes", tags=["Event Codes"])


@router.post("", response_model=EventCodeRead, status_code=status.HTTP_201_CREATED)
def create_event_code(
    payload: EventCodeCreate,
    db: Session = Depends(get_db),
):
    return EventCodeService(db).create(payload)


@router.get("", response_model=list[EventCodeRead])
def list_event_codes(db: Session = Depends(get_db)):
    return EventCodeService(db).list_all()

@router.delete("/{event_code}", status_code=status.HTTP_200_OK)
def delete_event_code(event_code: str, db: Session = Depends(get_db)):
    return EventCodeService(db).delete(event_code)