from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from src.config import DATABASE_URL

Base = declarative_base()

class StockList(Base):
    __tablename__ = "stock_list"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)

class RSI_4H(Base):
    __tablename__ = "rsi_4h"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    rsi_value = Column(Float)
    variation = Column(Float)
    rvol_1 = Column(Float)
    rvol_2 = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    current_value = Column(Float, default=0.0)
    alert_value = Column(Float, default=-1.0)
    alert_direction = Column(String, default="debajo") # "encima" o "debajo"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
