from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.models import (
    Fund,
    Holding,
    Price,
    SectorExposure,
    CountryExposure,
    MarketCapExposure,
)

router = APIRouter(tags=["Fund"])


def get_fund_or_404(ticker: str, db: Session):
    fund = (
        db.query(Fund)
        .filter(Fund.ticker == ticker.upper())
        .first()
    )

    if not fund:
        raise HTTPException(
            status_code=404,
            detail=f"Fund '{ticker}' not found"
        )

    return fund


@router.get("/fund/{ticker}")
def get_fund(
    ticker: str,
    db: Session = Depends(get_db)
):
    fund = get_fund_or_404(ticker, db)

    return {
        "id": fund.id,
        "name": fund.name,
        "ticker": fund.ticker,
        "description": fund.description,
        "created_at": fund.created_at,
    }


@router.get("/fund/{ticker}/holdings")
def get_holdings(
    ticker: str,
    db: Session = Depends(get_db)
):
    fund = get_fund_or_404(ticker, db)

    holdings = (
        db.query(Holding)
        .filter(Holding.fund_id == fund.id)
        .order_by(Holding.weight.desc())
        .all()
    )

    return {
        "fund": ticker.upper(),
        "count": len(holdings),
        "holdings": [
            {
                "ticker": h.ticker,
                "name": h.name,
                "weight": h.weight,
                "sector": h.sector,
                "country": h.country,
                "market_cap": h.market_cap,
                "as_of_date": h.as_of_date,
            }
            for h in holdings
        ],
    }


@router.get("/fund/{ticker}/prices")
def get_prices(
    ticker: str,
    limit: int = 252,
    db: Session = Depends(get_db)
):
    fund = get_fund_or_404(ticker, db)

    prices = (
        db.query(Price)
        .filter(Price.fund_id == fund.id)
        .order_by(Price.date.desc())
        .limit(limit)
        .all()
    )

    return {
        "fund": ticker.upper(),
        "count": len(prices),
        "prices": [
            {
                "date": p.date,
                "open": p.open_price,
                "high": p.high,
                "low": p.low,
                "close": p.close_price,
                "volume": p.volume,
            }
            for p in prices
        ],
    }


@router.get("/fund/{ticker}/sector-exposure")
def get_sector_exposure(
    ticker: str,
    db: Session = Depends(get_db)
):
    fund = get_fund_or_404(ticker, db)

    exposures = (
        db.query(SectorExposure)
        .filter(SectorExposure.fund_id == fund.id)
        .order_by(SectorExposure.weight.desc())
        .all()
    )

    return {
        "fund": ticker.upper(),
        "as_of_date": exposures[0].as_of_date if exposures else None,
        "sectors": [
            {
                "sector": e.sector,
                "weight": e.weight
            }
            for e in exposures
        ],
    }


@router.get("/fund/{ticker}/country-exposure")
def get_country_exposure(
    ticker: str,
    db: Session = Depends(get_db)
):
    fund = get_fund_or_404(ticker, db)

    exposures = (
        db.query(CountryExposure)
        .filter(CountryExposure.fund_id == fund.id)
        .order_by(CountryExposure.weight.desc())
        .all()
    )

    return {
        "fund": ticker.upper(),
        "as_of_date": exposures[0].as_of_date if exposures else None,
        "countries": [
            {
                "country": e.country,
                "weight": e.weight
            }
            for e in exposures
        ],
    }


@router.get("/fund/{ticker}/market-cap-exposure")
def get_market_cap_exposure(
    ticker: str,
    db: Session = Depends(get_db)
):
    fund = get_fund_or_404(ticker, db)

    exposures = (
        db.query(MarketCapExposure)
        .filter(MarketCapExposure.fund_id == fund.id)
        .order_by(MarketCapExposure.weight.desc())
        .all()
    )

    return {
        "fund": ticker.upper(),
        "as_of_date": exposures[0].as_of_date if exposures else None,
        "market_cap_breakdown": [
            {
                "category": e.category,
                "weight": e.weight
            }
            for e in exposures
        ],
    }