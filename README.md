# Spring Street — Prisma Global Growth Backend

I built this backend to power the [Prisma Global Growth](https://springstreet.in/products/prisma/global-growth-prisma) factsheet/product experience. The goal of the project is to show how I designed the backend architecture, data model, ETL pipeline, daily refresh automation, and REST APIs that can directly feed a frontend product page.

---

## 1) Assignment Requirements

The assignment asked me to think through:

- database schema design
- backend architecture
- data pipelines / ETL systems
- API design
- data freshness and maintainability

I used Yahoo Finance as the main public data source and built a backend that can update the factsheet data daily, expose it through REST APIs, and keep the system easy to maintain. The assignment also explicitly asks for architecture explanations and a README, so I documented the system design clearly here.

---

## 2) What I Built

I built the backend in four layers:

- **ETL pipeline** to fetch and process data from Yahoo Finance
- **PostgreSQL database** to store normalized fund data
- **FastAPI REST API** to expose the data as JSON
- **APScheduler** to refresh the data automatically every day

This gives me a clean backend flow where the frontend never talks to Yahoo Finance directly. Instead, it reads structured data from my API, which is much more stable and maintainable.

---

## 3) System Overview

```text
Yahoo Finance
    ↓
ETL Pipeline (fetch + transform + enrich)
    ↓
PostgreSQL Database
    ↓
FastAPI REST APIs
    ↓
Frontend Factsheet / Product Page
```

I separated the backend into independent layers so that each part has one responsibility:

- the ETL layer fetches and prepares data
- the database layer stores the data
- the API layer serves the data
- the scheduler keeps the data fresh automatically

This structure makes the project easier to debug, extend, and explain.

---

## 4) Architecture Overview

```text
┌─────────────────────────────────────────────────────────┐
│                     Daily Scheduler                      │
│              APScheduler — runs at 06:00 AM              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    ETL Pipeline                          │
│                                                         │
│  yfinance funds_data  →  top holdings (10)              │
│  yfinance per-ticker  →  sector, country, market cap    │
│  yfinance history     →  5 years OHLCV prices           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                     │
│                                                         │
│  funds │ holdings │ prices │ sector_exposures           │
│  country_exposures │ market_cap_exposures               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI REST API                       │
│                                                         │
│  GET  /api/fund/{ticker}                                │
│  GET  /api/fund/{ticker}/holdings                       │
│  GET  /api/fund/{ticker}/prices                         │
│  GET  /api/fund/{ticker}/sector-exposure                │
│  GET  /api/fund/{ticker}/country-exposure               │
│  GET  /api/fund/{ticker}/market-cap-exposure            │
│  POST /api/run-pipeline                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 5) Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| API Framework | FastAPI |
| Server | Uvicorn |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Data Source | yfinance (Yahoo Finance) |
| Scheduler | APScheduler |
| Infrastructure | Docker + Docker Compose |

---

## 6) What FastAPI Does

I used FastAPI as the HTTP layer of the application.

FastAPI:

- receives requests from the frontend or Swagger UI
- routes requests to the correct endpoint handler
- queries PostgreSQL through SQLAlchemy
- returns structured JSON responses

Example request flow:

```text
Frontend → FastAPI endpoint → SQLAlchemy query → PostgreSQL → JSON response
```

Example endpoint:

```http
GET /api/fund/VT/holdings
```

This endpoint returns holdings data that can directly populate a frontend table, card layout, chart, or summary panel.

FastAPI also auto-generates interactive API documentation at:

```text
http://localhost:8000/docs
```

---

## 7) What APScheduler Does

I used APScheduler to automate the ETL refresh.

In this project, APScheduler:

- starts when FastAPI starts
- stays alive while the server is running
- triggers the ETL pipeline every day at **06:00 AM**
- refreshes holdings, exposures, and price history automatically

### Scheduler behavior

```text
Server starts
↓
APScheduler starts
↓
Waits until scheduled time
↓
Runs `run_pipeline()`
↓
Updates PostgreSQL
```

### Manual trigger vs scheduled trigger

| Trigger | Purpose |
|---|---|
| `POST /api/run-pipeline` | Manual testing / on-demand refresh |
| APScheduler daily job | Automatic daily refresh |

This is important because the frontend always reads from the database. Once the scheduler updates the database, the frontend automatically sees the refreshed values.

---

## 8) Data Sources

| Data | Source | Frequency |
|---|---|---|
| Top 10 holdings | `yfinance.funds_data.top_holdings` | Daily |
| Sector exposure | `yfinance.funds_data.sector_weightings` | Daily |
| Country exposure | Derived from holdings | Daily |
| Market cap exposure | Derived from holdings | Daily |
| Historical prices | `yfinance.history(period="5y")` | Daily |

> **Note:** yfinance exposes only the top 10 ETF holdings in a convenient form. For a production-grade system, I would replace this with a licensed provider or filing-based source such as SEC filings so the full holdings set is available.

---

## 9) Database Schema

```text
funds
  id, name, ticker, description, created_at

holdings
  id, fund_id, ticker, name, weight, sector, country, market_cap, as_of_date

prices
  id, fund_id, date, open_price, high, low, close_price, volume

sector_exposures
  id, fund_id, sector, weight, as_of_date

country_exposures
  id, fund_id, country, weight, as_of_date

market_cap_exposures
  id, fund_id, category, weight, as_of_date
```

I designed the schema in a normalized way so that:

- one fund can have many holdings
- one fund can have many price rows
- one fund can have many sector exposure rows
- one fund can have many country exposure rows
- one fund can have many market cap exposure rows

This structure is ideal for analytics, charting, and future expansion.

---

## 10) API Reference

### Fund Overview
```http
GET /api/fund/VT
```

```json
{
  "id": 1,
  "name": "Prisma Global Growth",
  "ticker": "VT",
  "description": "A globally diversified equity portfolio targeting long-term growth.",
  "created_at": "2026-05-26T00:00:00"
}
```

### Holdings
```http
GET /api/fund/VT/holdings
```

```json
{
  "fund": "VT",
  "count": 10,
  "holdings": [
    {
      "ticker": "NVDA",
      "name": "NVIDIA Corp",
      "weight": 4.17,
      "sector": "Technology",
      "country": "United States",
      "market_cap": "Large Cap",
      "as_of_date": "2026-05-26"
    }
  ]
}
```

### Historical Prices
```http
GET /api/fund/VT/prices?limit=252
```

This returns the most recent `N` trading days of OHLCV data.

### Sector Exposure
```http
GET /api/fund/VT/sector-exposure
```

```json
{
  "fund": "VT",
  "as_of_date": "2026-05-26",
  "sectors": [
    { "sector": "Technology", "weight": 27.8 },
    { "sector": "Financial Services", "weight": 15.94 }
  ]
}
```

### Country Exposure
```http
GET /api/fund/VT/country-exposure
```

### Market Cap Exposure
```http
GET /api/fund/VT/market-cap-exposure
```

```json
{
  "fund": "VT",
  "as_of_date": "2026-05-26",
  "market_cap_breakdown": [
    { "category": "Large Cap", "weight": 100.0 }
  ]
}
```

### Trigger Pipeline Manually
```http
POST /api/run-pipeline
```

This runs the ETL pipeline in the background and is useful for testing or manual refresh.

---

## 11) How the Frontend Uses These APIs

The backend is designed to power a factsheet/product page. The frontend does not need to query the database directly. Instead, it calls the REST APIs and renders the returned JSON.

### Frontend-to-API mapping

| Frontend section | API endpoint | Usage |
|---|---|---|
| Fund header | `/api/fund/VT` | Show title, ticker, and description |
| Holdings table | `/api/fund/VT/holdings` | Populate rows with ticker, name, weight, sector, country |
| Performance chart | `/api/fund/VT/prices` | Draw a historical line chart |
| Sector pie chart | `/api/fund/VT/sector-exposure` | Show allocation by sector |
| Country chart | `/api/fund/VT/country-exposure` | Show allocation by country |
| Market-cap chart | `/api/fund/VT/market-cap-exposure` | Show allocation by cap bucket |

### Example frontend fetch call

```javascript
async function fetchHoldings() {
  const response = await fetch("http://localhost:8000/api/fund/VT/holdings");
  const data = await response.json();
  return data.holdings;
}
```

### Example: populate a table

The frontend can map the holdings response into a table like this:

| API Field | Frontend UI |
|---|---|
| `ticker` | Symbol column |
| `name` | Company name column |
| `weight` | Weight percentage column |
| `sector` | Sector badge |
| `country` | Country label |
| `market_cap` | Market-cap badge |

### Example: chart rendering

```javascript
async function fetchPrices() {
  const response = await fetch("http://localhost:8000/api/fund/VT/prices?limit=252");
  const data = await response.json();
  return data.prices;
}
```

A chart library like Recharts, Chart.js, or ECharts can directly use `data.prices` to render the price trend.

### Why I included this section

For this assignment, the key goal is to show that the backend can power a real product experience. A full frontend implementation is not required, but the API responses are already structured so that a frontend can consume them directly.

---

## 12) Setup Instructions

### Prerequisites
- Docker Desktop
- Python 3.11+
- Git

### 1. Clone the repository

```bash
git clone https://github.com/humayun-987/SpringStreet.git
cd SpringStreet
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
source venv/bin/activate      # Mac/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Example `.env` values:

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret
POSTGRES_DB=springstreet
DATABASE_URL=postgresql://admin:secret@localhost:5433/springstreet
```

### 5. Start Docker containers

```bash
docker-compose up -d
```

This starts:

- PostgreSQL on port `5433`
- pgAdmin on port `5051`

### 6. Run database migrations

```bash
python -m alembic upgrade head
```

### 7. Run the ETL pipeline once

```bash
python -m app.pipelines.etl
```

This performs the initial data load from Yahoo Finance.

### 8. Start the API server

```bash
python -m uvicorn app.main:app --reload
```

API runs at:

- `http://localhost:8000`
- `http://localhost:8000/docs`

---

## 13) Testing Workflow

### A. Test the ETL pipeline
```http
POST /api/run-pipeline
```

### B. Test the API in Swagger
Open `/docs` and verify:

- `GET /api/fund/VT`
- `GET /api/fund/VT/holdings`
- `GET /api/fund/VT/prices`
- `GET /api/fund/VT/sector-exposure`
- `GET /api/fund/VT/country-exposure`
- `GET /api/fund/VT/market-cap-exposure`

### C. Test the database in pgAdmin
Use the Query Tool and run SQL queries to confirm that tables are populated.

---

## 14) Useful SQL Queries for pgAdmin

### View all tables
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';
```

### View funds
```sql
SELECT * FROM funds;
```

### View holdings
```sql
SELECT ticker, name, weight, sector, country
FROM holdings
ORDER BY weight DESC;
```

### Join holdings with fund
```sql
SELECT
    f.name AS fund_name,
    h.ticker,
    h.name,
    h.weight,
    h.sector
FROM holdings h
JOIN funds f ON h.fund_id = f.id
ORDER BY h.weight DESC;
```

### View prices
```sql
SELECT date, open_price, high, low, close_price, volume
FROM prices
ORDER BY date DESC
LIMIT 20;
```

### View sector exposure
```sql
SELECT sector, weight
FROM sector_exposures
ORDER BY weight DESC;
```

### View country exposure
```sql
SELECT country, weight
FROM country_exposures
ORDER BY weight DESC;
```

### View market cap exposure
```sql
SELECT category, weight
FROM market_cap_exposures
ORDER BY weight DESC;
```

### Count rows
```sql
SELECT COUNT(*) FROM funds;
SELECT COUNT(*) FROM holdings;
SELECT COUNT(*) FROM prices;
SELECT COUNT(*) FROM sector_exposures;
SELECT COUNT(*) FROM country_exposures;
SELECT COUNT(*) FROM market_cap_exposures;
```

---

## 15) Project Structure

```text
SpringStreet/
├── app/
│   ├── api/
│   │   ├── fund.py
│   │   └── pipeline.py
│   ├── models/
│   │   └── models.py
│   ├── pipelines/
│   │   └── etl.py
│   ├── scheduler/
│   │   └── scheduler.py
│   ├── database.py
│   └── main.py
├── alembic/
├── db/
├── docker-compose.yml
├── requirements.txt
├── .env
└── README.md
```

---

## 16) Design Decisions

### Why PostgreSQL?
I chose PostgreSQL because the data is highly structured and relational. Funds, holdings, prices, and exposures all fit naturally into a relational model. PostgreSQL is also strong for time-series queries on historical price data.

### Why FastAPI?
I used FastAPI because it is lightweight, modern, and well suited for exposing clean REST APIs. It also gives automatic docs, which made testing and review easier.

### Why APScheduler?
I used APScheduler because this project only needs one scheduled daily job. It is simple, reliable, and avoids the extra complexity of a distributed queue system.

### Why yfinance?
I used yfinance because it is free, easy to integrate, and sufficient for this internship assignment. It provided a fast way to build a realistic financial data pipeline.

---

## 17) Limitations and Future Improvements

- yfinance only gives limited public ETF holding data
- a production version should use a licensed provider or filing-based source for full holdings
- authentication is not included because the assignment focuses on backend data infrastructure
- a frontend is not built here; this backend is designed to power one

---

## 18) pgAdmin Access

- URL: `http://localhost:5051`
- Email: `admin@springstreet.com`
- Password: `secret`
- Server connection: host=`springstreet_db`, port=`5432`

---

## 19) Summary

I designed this backend to provide a complete factsheet data layer for the Prisma Global Growth product experience.

It includes:

- a normalized PostgreSQL schema
- FastAPI REST endpoints
- an ETL pipeline using Yahoo Finance
- APScheduler for daily refresh
- frontend-ready JSON responses
- SQL queries for validation and inspection

This gives the project a clean, maintainable backend architecture that matches the assignment requirements and can directly support a product page frontend.
