"""Initialize database without migrations."""
import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.base import Base
# Import all models to register them with Base.metadata
from src.database import models  # noqa: F401


async def init_db():
    """Initialize database tables."""
    # Use direct database URL
    db_url = "sqlite+aiosqlite:///./dispatcher.db"
    engine = create_async_engine(db_url, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database initialized successfully!")
    print(f"Created tables: {list(Base.metadata.tables.keys())}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())

