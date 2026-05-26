from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class Fund(Base):
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    ticker = Column(String, unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    holdings = relationship("Holding", back_populates="fund")
    prices = relationship("Price", back_populates="fund")
    sector_exposures = relationship("SectorExposure", back_populates="fund")
    country_exposures = relationship("CountryExposure", back_populates="fund")
    market_cap_exposures = relationship("MarketCapExposure", back_populates="fund")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    ticker = Column(String, nullable=False)
    name = Column(String)
    weight = Column(Float)
    sector = Column(String)
    country = Column(String)
    market_cap = Column(Float)
    as_of_date = Column(Date)

    fund = relationship("Fund", back_populates="holdings")


class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    date = Column(Date, nullable=False)
    close_price = Column(Float)
    open_price = Column(Float)
    high = Column(Float)
    low = Column(Float)
    volume = Column(Float)

    fund = relationship("Fund", back_populates="prices")


class SectorExposure(Base):
    __tablename__ = "sector_exposures"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    sector = Column(String, nullable=False)
    weight = Column(Float)
    as_of_date = Column(Date)

    fund = relationship("Fund", back_populates="sector_exposures")


class CountryExposure(Base):
    __tablename__ = "country_exposures"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    country = Column(String, nullable=False)
    weight = Column(Float)
    as_of_date = Column(Date)

    fund = relationship("Fund", back_populates="country_exposures")


class MarketCapExposure(Base):
    __tablename__ = "market_cap_exposures"

    id = Column(Integer, primary_key=True, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id"), nullable=False)
    category = Column(String, nullable=False)
    weight = Column(Float)
    as_of_date = Column(Date)

    fund = relationship("Fund", back_populates="market_cap_exposures")