from app.database import engine, Base
from app.models.models import Fund, Holding, Price, SectorExposure, CountryExposure, MarketCapExposure

def init_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    init_db()