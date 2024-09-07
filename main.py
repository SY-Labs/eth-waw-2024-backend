import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
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
    func,
    case,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.exc import IntegrityError

from models.bet import BetCreate, BetResponse
from models.event import EventCreate, EventResponse, ContractsUpdate

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Event(Base):
    __tablename__ = "events"

    request_id = Column(String, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    due_date = Column(BigInteger)
    predict = Column(JSON, nullable=True)
    contracts = Column(JSON, nullable=True)
    bets = relationship("Bet", back_populates="event")


class Bet(Base):
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    event_request_id = Column(String, ForeignKey("events.request_id"))
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


@app.post("/events", tags=["events"],  response_model=EventResponse)
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


@app.put("/events/{request_id}", tags=["events"], response_model=EventResponse)
async def update_event_contracts(
    request_id: str, contracts: ContractsUpdate, db: Session = Depends(get_db)
):
    db_event = db.query(Event).filter(Event.request_id == request_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    db_event.contracts = contracts.contracts
    db.commit()
    db.refresh(db_event)
    return db_event


@app.get("/events", tags=["events"], response_model=List[EventResponse])
async def get_all_events(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    events = db.query(Event).offset(skip).limit(limit).all()
    return events


@app.get("/events/{request_id}", tags=["events"], response_model=EventResponse)
async def get_event(request_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.request_id == request_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.post("/bets", tags=["bets"], response_model=BetResponse)
async def create_bet(bet: BetCreate, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.request_id == bet.event_request_id).first()
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


@app.get("/events/{request_id}/bets", tags=["bets"], response_model=List[BetResponse])
async def get_bets_for_event(request_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.request_id == request_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    bets = db.query(Bet).filter(Bet.event_request_id == request_id).all()
    return bets

@app.get("/top-betters", tags=["stats"])
async def get_top_betters(limit: int = 10, db: Session = Depends(get_db)):
    top_betters = db.query(
        Bet.wallet_address,
        func.sum(Bet.tokens).label('total_tokens')
    ).group_by(Bet.wallet_address).order_by(func.sum(Bet.tokens).desc()).limit(limit).all()

    return [{"wallet_address": better[0], "total_tokens": better[1]} for better in top_betters]


@app.get("/largest-bet", tags=["stats"])
async def get_largest_bet(db: Session = Depends(get_db)):
    largest_bet = db.query(Bet).order_by(Bet.tokens.desc()).first()
    if not largest_bet:
        raise HTTPException(status_code=404, detail="No bets found")

    return {
        "event_request_id": largest_bet.event_request_id,
        "wallet_address": largest_bet.wallet_address,
        "prediction": largest_bet.prediction,
        "tokens": largest_bet.tokens
    }


@app.get("/events/{request_id}", tags=["stats"])
async def get_event_statistics(request_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.request_id == request_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    stats = db.query(
        func.count().label('total_bets'),
        func.sum(Bet.tokens).label('total_tokens'),
        func.sum(case((Bet.prediction == 'YES', 1), else_=0)).label('yes_bets'),
        func.sum(case((Bet.prediction == 'NO', 1), else_=0)).label('no_bets')
    ).filter(Bet.event_request_id == request_id).first()

    return {
        "request_id": request_id,
        "title": event.title,
        "total_bets": stats.total_bets or 0,
        "total_tokens": float(stats.total_tokens or 0),
        "yes_bets": stats.yes_bets or 0,
        "no_bets": stats.no_bets or 0
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
