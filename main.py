import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from typing import List

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Enum,
    ForeignKey,
    JSON,
    BigInteger,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.exc import IntegrityError

from models.bet import BetCreate, BetResponse
from models.event import EventCreate, EventResponse, ContractsUpdate

load_dotenv()

app = FastAPI()

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(String)
    due_date = Column(BigInteger)
    predict = Column(JSON, nullable=True)
    contracts = Column(JSON, nullable=True)
    bets = relationship("Bet", back_populates="event")


class Bet(Base):
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    wallet_address = Column(String, index=True)
    prediction = Column(Enum("YES", "NO", name="prediction_type"))
    tokens = Column(Float)
    event = relationship("Event", back_populates="bets")


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/event", response_model=EventResponse)
async def create_event(event: EventCreate, db: Session = Depends(get_db)):
    db_event = Event(
        request_id=event.request_id,
        title=event.title,
        description=event.description,
        due_date=event.due_date,
        predict=event.predict.model_dump() if event.predict else None,
    )
    try:
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="An event with this request ID already exists"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while saving the event: {str(e)}",
        )
    return db_event


@app.put("/event/{event_id}", response_model=EventResponse)
async def update_event_contracts(
    event_id: int, contracts: ContractsUpdate, db: Session = Depends(get_db)
):
    db_event = db.query(Event).filter(Event.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    db_event.contracts = contracts.contracts
    db.commit()
    db.refresh(db_event)
    return db_event


@app.get("/events/", response_model=List[EventResponse])
async def get_all_events(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    events = db.query(Event).offset(skip).limit(limit).all()
    return events


@app.post("/bets/", response_model=BetResponse)
async def create_bet(bet: BetCreate, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == bet.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db_bet = Bet(**bet.dict())
    try:
        db.add(db_bet)
        db.commit()
        db.refresh(db_bet)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"An error occurred while saving the bet: {str(e)}"
        )

    return db_bet


@app.get("/events/{event_id}/bets", response_model=List[BetResponse])
async def get_bets_for_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    bets = db.query(Bet).filter(Bet.event_id == event_id).all()
    return bets


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
