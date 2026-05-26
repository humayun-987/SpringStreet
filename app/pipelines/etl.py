import os
import pandas as pd
import yfinance as yf
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.models.models import Fund, Holding, Price, SectorExposure, CountryExposure, MarketCapExposure

# ── Constants ──────────────────────────────────────────────
FUND_TICKER = "VT"
FUND_NAME = "Prisma Global Growth"
FUND_DESCRIPTION = "A globally diversified equity portfolio targeting long-term growth."


# ── Step 1: Get or create fund ─────────────────────────────
def get_or_create_fund(db: Session) -> Fund:
    fund = db.query(Fund).filter(Fund.ticker == FUND_TICKER).first()
    if not fund:
        print(f"Creating fund: {FUND_NAME}")
        fund = Fund(
            name=FUND_NAME,
            ticker=FUND_TICKER,
            description=FUND_DESCRIPTION
        )
        db.add(fund)
        db.commit()
        db.refresh(fund)
    else:
        print(f"Fund already exists: {FUND_NAME}")
    return fund


# ── Step 2: Fetch and save top holdings ───────────────────
def save_holdings(db: Session, fund: Fund):
    print("Fetching top holdings from yfinance...")

    vt = yf.Ticker(FUND_TICKER)
    top_holdings = vt.funds_data.top_holdings
    today = date.today()

    # Delete existing holdings
    db.query(Holding).filter(Holding.fund_id == fund.id).delete()
    db.commit()

    for symbol, row in top_holdings.iterrows():
        print(f"  Enriching {symbol}...")
        try:
            info = yf.Ticker(symbol).info
            sector = info.get("sector", "Unknown")
            country = info.get("country", "Unknown")
            market_cap = info.get("marketCap", None)
        except:
            sector, country, market_cap = "Unknown", "Unknown", None

        holding = Holding(
            fund_id=fund.id,
            ticker=symbol,
            name=str(row.get("Name", symbol)),
            weight=round(float(row.get("Holding Percent", 0)) * 100, 4),
            sector=sector,
            country=country,
            market_cap=market_cap,
            as_of_date=today
        )
        db.add(holding)

    db.commit()
    print("Holdings saved.")


# ── Step 3: Save sector exposure ──────────────────────────
def save_sector_exposure(db: Session, fund: Fund):
    print("Saving sector exposure...")

    vt = yf.Ticker(FUND_TICKER)
    sector_data = vt.funds_data.sector_weightings
    today = date.today()

    db.query(SectorExposure).filter(SectorExposure.fund_id == fund.id).delete()
    db.commit()

    for sector, weight in sector_data.items():
        exposure = SectorExposure(
            fund_id=fund.id,
            sector=sector.replace("_", " ").title(),
            weight=round(float(weight) * 100, 4),
            as_of_date=today
        )
        db.add(exposure)

    db.commit()
    print("Sector exposure saved.")


# ── Step 4: Save country exposure ─────────────────────────
def save_country_exposure(db: Session, fund: Fund):
    print("Deriving country exposure from holdings...")

    holdings = db.query(Holding).filter(Holding.fund_id == fund.id).all()
    today = date.today()

    db.query(CountryExposure).filter(CountryExposure.fund_id == fund.id).delete()
    db.commit()

    country_weights = {}
    for holding in holdings:
        country = holding.country or "Unknown"
        weight = holding.weight or 0.0
        country_weights[country] = country_weights.get(country, 0.0) + weight

    for country, weight in country_weights.items():
        exposure = CountryExposure(
            fund_id=fund.id,
            country=country,
            weight=round(weight, 4),
            as_of_date=today
        )
        db.add(exposure)

    db.commit()
    print("Country exposure saved.")


# ── Step 5: Save market cap exposure ──────────────────────
def save_market_cap_exposure(db: Session, fund: Fund):
    print("Deriving market cap exposure from holdings...")

    holdings = db.query(Holding).filter(Holding.fund_id == fund.id).all()
    today = date.today()

    db.query(MarketCapExposure).filter(MarketCapExposure.fund_id == fund.id).delete()
    db.commit()

    cap_weights = {"Large Cap": 0.0, "Mid Cap": 0.0, "Small Cap": 0.0, "Unknown": 0.0}

    for holding in holdings:
        weight = holding.weight or 0.0
        market_cap = holding.market_cap

        if market_cap is None:
            cap_weights["Unknown"] += weight
        elif market_cap >= 10_000_000_000:
            cap_weights["Large Cap"] += weight
        elif market_cap >= 2_000_000_000:
            cap_weights["Mid Cap"] += weight
        else:
            cap_weights["Small Cap"] += weight

    for category, weight in cap_weights.items():
        exposure = MarketCapExposure(
            fund_id=fund.id,
            category=category,
            weight=round(weight, 4),
            as_of_date=today
        )
        db.add(exposure)

    db.commit()
    print("Market cap exposure saved.")


# ── Step 6: Save historical prices ────────────────────────
def save_prices(db: Session, fund: Fund):
    print("Fetching historical prices...")

    ticker = yf.Ticker(FUND_TICKER)
    history = ticker.history(period="5y")

    if history.empty:
        print("No price data found.")
        return

    print(f"Saving {len(history)} price records...")

    for price_date, row in history.iterrows():
        price_date = price_date.date()

        exists = db.query(Price).filter(
            Price.fund_id == fund.id,
            Price.date == price_date
        ).first()

        if exists:
            continue

        price = Price(
            fund_id=fund.id,
            date=price_date,
            close_price=round(float(row["Close"]), 4),
            open_price=round(float(row["Open"]), 4),
            high=round(float(row["High"]), 4),
            low=round(float(row["Low"]), 4),
            volume=float(row["Volume"])
        )
        db.add(price)

    db.commit()
    print("Prices saved.")


# ── Main pipeline runner ───────────────────────────────────
def run_pipeline():
    print(f"\n{'='*50}")
    print(f"Pipeline started at {datetime.now()}")
    print(f"{'='*50}\n")

    from app.database import SessionLocal
    db = SessionLocal()

    try:
        fund = get_or_create_fund(db)
        save_holdings(db, fund)
        save_sector_exposure(db, fund)
        save_country_exposure(db, fund)
        save_market_cap_exposure(db, fund)
        save_prices(db, fund)

        print(f"\n{'='*50}")
        print(f"Pipeline completed at {datetime.now()}")
        print(f"{'='*50}\n")

    except Exception as e:
        print(f"Pipeline failed: {e}")
        raise e

    finally:
        db.close()


if __name__ == "__main__":
    run_pipeline()