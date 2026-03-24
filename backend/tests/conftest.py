import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.services.auth_service import create_access_token

TEST_DB_URL = "postgresql+asyncpg://pmai:pmai@localhost:5432/pmai_test"


@pytest_asyncio.fixture(scope="function")
async def setup_db():
    # Import all models so Base.metadata knows about them
    import app.models.user  # noqa: F401
    import app.models.organization  # noqa: F401
    import app.models.project  # noqa: F401
    import app.models.task  # noqa: F401
    import app.models.calendar  # noqa: F401
    import app.models.notion  # noqa: F401
    import app.models.slack  # noqa: F401
    import app.models.activity_log  # noqa: F401
    import app.models.pull_request  # noqa: F401
    import app.models.ai_job_queue  # noqa: F401
    import app.models.ai_review  # noqa: F401
    import app.models.weekly_briefing  # noqa: F401

    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(setup_db):
    engine = setup_db
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(setup_db):
    engine = setup_db
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession):
    user = User(
        github_id=12345,
        github_username="testuser",
        name="Test User",
        email="testuser@example.com",
        avatar_url="https://avatars.githubusercontent.com/u/12345",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user: User):
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}
