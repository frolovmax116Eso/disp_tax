"""Pytest configuration and fixtures."""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from src.database.base import Base
from src.database.models import *


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    """Create test database session."""
    # In-memory SQLite database for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def sample_dispatcher(db_session: AsyncSession):
    """Create sample dispatcher for tests."""
    dispatcher = Dispatcher(
        telegram_id=123456789,
        username="test_dispatcher",
        first_name="Test",
        last_name="Dispatcher",
        session_file="test.session",
        session_active=True
    )
    db_session.add(dispatcher)
    await db_session.commit()
    await db_session.refresh(dispatcher)
    return dispatcher


@pytest.fixture
async def sample_order(db_session: AsyncSession, sample_dispatcher):
    """Create sample order for tests."""
    from src.database.models import Order, OrderState
    
    order = Order(
        dispatcher_id=sample_dispatcher.id,
        state=OrderState.DRAFT,
        content="Test order content",
        normalized_content="Test order content",
        is_vip=False
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order

