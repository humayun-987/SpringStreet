import requests
import pandas as pd
import yfinance as yf
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.models.models import Fund, Holding, Price, SectorExposure, CountryExposure, MarketCapExposure

# ── Constants ──────────────────────────────────────────────
FUND_TICKER = "VT"
FUND_NAME = "Prisma Global Growth"
FUND_DESCRIPTION = "A globally diversified equity portfolio targeting long-term growth."

VT_HOLDINGS_URL = "https://advisors.vanguard.com/web/c1/fas-investproduct/fund/0968/csv?type=holdings"


# ── Step 1: Create fund in DB if it doesn't exist ──────────
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

# ── Step 2: Fetch holdings CSV from Vanguard ───────────────
def fetch_holdings_csv() -> pd.DataFrame:
    print("Fetching VT holdings from Vanguard...")
    
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    response = requests.get(VT_HOLDINGS_URL, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch holdings: {response.status_code}")
    
    lines = response.text.splitlines()
    
    # Find where the actual table starts
    start_index = 0
    for i, line in enumerate(lines):
        if line.startswith('"Ticker"') or line.startswith('Ticker'):
            start_index = i
            break
    
    csv_data = "\n".join(lines[start_index:])
    
    df = pd.read_csv(pd.io.common.StringIO(csv_data))
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df = df.dropna(subset=["ticker"])
    df = df[df["ticker"].str.strip() != ""]
    
    print(f"Fetched {len(df)} holdings")
    return df

# ── Step 3: Enrich each holding with yfinance data ─────────
def enrich_holding(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            "sector": info.get("sector", "Unknown"),
            "country": info.get("country", "Unknown"),
            "market_cap": info.get("marketCap", None)
        }
    except Exception as e:
        print(f"Could not enrich {ticker}: {e}")
        return {
            "sector": "Unknown",
            "country": "Unknown",
            "market_cap": None
        }

# ── Step 4: Save holdings to DB ────────────────────────────
def save_holdings(db: Session, fund: Fund, df: pd.DataFrame):
    print("Saving holdings to DB...")
    
    # Delete existing holdings for today to avoid duplicates
    db.query(Holding).filter(Holding.fund_id == fund.id).delete()
    db.commit()
    
    # Take top 50 holdings by weight
    top50 = df.head(50)
    
    today = date.today()
    
    for _, row in top50.iterrows():
        ticker = str(row.get("ticker", "")).strip()
        if not ticker:
            continue
        
        # Get weight value
        weight_raw = row.get("% of funds", row.get("weight", 0))
        try:
            weight = float(str(weight_raw).replace("%", "").strip())
        except:
            weight = 0.0
        
        # Enrich with yfinance
        enriched = enrich_holding(ticker)
        
        holding = Holding(
            fund_id=fund.id,
            ticker=ticker,
            name=str(row.get("holding name", ticker)),
            weight=weight,
            sector=enriched["sector"],
            country=enriched["country"],
            market_cap=enriched["market_cap"],
            as_of_date=today
        )
        db.add(holding)
    
    db.commit()
    print("Holdings saved.")     
    
# ── Step 5: Fetch and save prices from yfinance ────────────
def save_prices(db: Session, fund: Fund):
    print("Fetching historical prices...")
    
    ticker = yf.Ticker(FUND_TICKER)
    history = ticker.history(period="5y")
    
    if history.empty:
        print("No price data found.")
        return
    
    print(f"Saving {len(history)} price records...")
    
    for price_date, row in history.iterrows():
        # Convert to python date
        price_date = price_date.date()
        
        # Skip if already exists
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
    
# ── Step 6: Calculate and save exposures ───────────────────
def save_sector_exposure(db: Session, fund: Fund):
    print("Calculating sector exposure...")
    
    today = date.today()
    
    # Delete existing sector exposures
    db.query(SectorExposure).filter(SectorExposure.fund_id == fund.id).delete()
    db.commit()
    
    # Get all holdings from DB
    holdings = db.query(Holding).filter(Holding.fund_id == fund.id).all()
    
    # Group by sector and sum weights
    sector_weights = {}
    for holding in holdings:
        sector = holding.sector or "Unknown"
        weight = holding.weight or 0.0
        sector_weights[sector] = sector_weights.get(sector, 0.0) + weight
    
    # Save to DB
    for sector, weight in sector_weights.items():
        exposure = SectorExposure(
            fund_id=fund.id,
            sector=sector,
            weight=round(weight, 4),
            as_of_date=today
        )
        db.add(exposure)
    
    db.commit()
    print("Sector exposure saved.")


def save_country_exposure(db: Session, fund: Fund):
    print("Calculating country exposure...")
    
    today = date.today()
    
    db.query(CountryExposure).filter(CountryExposure.fund_id == fund.id).delete()
    db.commit()
    
    holdings = db.query(Holding).filter(Holding.fund_id == fund.id).all()
    
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


def save_market_cap_exposure(db: Session, fund: Fund):
    print("Calculating market cap exposure...")
    
    today = date.today()
    
    db.query(MarketCapExposure).filter(MarketCapExposure.fund_id == fund.id).delete()
    db.commit()
    
    holdings = db.query(Holding).filter(Holding.fund_id == fund.id).all()
    
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
    
# ── Main pipeline runner ───────────────────────────────────
def run_pipeline():
    print(f"\n{'='*50}")
    print(f"Pipeline started at {datetime.now()}")
    print(f"{'='*50}\n")
    
    from app.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Step 1: Get or create fund
        fund = get_or_create_fund(db)
        
        # Step 2: Fetch holdings CSV
        df = fetch_holdings_csv()
        
        # Step 3: Save holdings (enriched with yfinance)
        save_holdings(db, fund, df)
        
        # Step 4: Save exposures (derived from holdings)
        save_sector_exposure(db, fund)
        save_country_exposure(db, fund)
        save_market_cap_exposure(db, fund)
        
        # Step 5: Save historical prices
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