from app.database import engine, Base
from app.models.models import Fund, Holding, Price, SectorExposure, CountryExposure, MarketCapExposure

def init_db():
    print("Use 'python -m alembic upgrade head' to create/update tables.")
    print("init_db.py is no longer used for table creation.")

if __name__ == "__main__":
    init_db()