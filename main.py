import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Literal

from sqlalchemy import create_engine, Column, Integer, String, Float, Enum
from sqlalchemy.orm import declarative_base, sessionmaker, Session

load_dotenv()

app = FastAPI()

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Bet(Base):
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String, index=True)
    bet_name = Column(String, index=True)
    prediction = Column(Enum("YES", "NO", name="prediction_type"))
    tokens = Column(Float)


Base.metadata.create_all(bind=engine)


class BetCreate(BaseModel):
    wallet_address: str
    bet_name: str
    prediction: Literal["YES", "NO"]
    tokens: float = Field(gt=0)


class BetResponse(BetCreate):
    id: int

    class Config:
        from_attributes = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/bets/", response_model=BetResponse)
async def create_bet(bet: BetCreate, db: Session = Depends(get_db)):
    db_bet = Bet(**bet.dict())

    try:
        db.add(db_bet)
        db.commit()
        db.refresh(db_bet)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while saving the bet: {str(e)}")

    return db_bet


@app.get("/bets/", response_model=List[BetResponse])
async def get_all_bets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    bets = db.query(Bet).offset(skip).limit(limit).all()
    return bets


@app.get("/bets/{wallet_address}", response_model=List[BetResponse])
async def get_bets_by_wallet(wallet_address: str, db: Session = Depends(get_db)):
    bets = db.query(Bet).filter(Bet.wallet_address == wallet_address).all()
    if not bets:
        raise HTTPException(status_code=404, detail="No bets found for this wallet address")
    return bets


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
