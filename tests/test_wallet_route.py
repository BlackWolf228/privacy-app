import asyncio
import sys
import types
import uuid
from pathlib import Path


def test_create_wallet_skips_existing_other_currency(monkeypatch):
    # Stub FastAPI components
    fastapi_stub = types.ModuleType("fastapi")

    class APIRouter:  # pragma: no cover - simple stub
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

        def get(self, *args, **kwargs):
            def decorator(fn):
                return fn

            return decorator

    class Depends:  # pragma: no cover - simple stub
        def __init__(self, dependency):
            self.dependency = dependency

    class HTTPException(Exception):  # pragma: no cover - simple stub
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail

    fastapi_stub.APIRouter = APIRouter
    fastapi_stub.Depends = Depends
    fastapi_stub.HTTPException = HTTPException
    monkeypatch.setitem(sys.modules, "fastapi", fastapi_stub)

    # Stub SQLAlchemy pieces used for query construction
    sqlalchemy_stub = types.ModuleType("sqlalchemy")
    sqlalchemy_future_stub = types.ModuleType("sqlalchemy.future")
    sqlalchemy_ext_stub = types.ModuleType("sqlalchemy.ext")
    sqlalchemy_ext_asyncio_stub = types.ModuleType("sqlalchemy.ext.asyncio")

    class DummyQuery:
        def __init__(self, model):
            self.model = model
            self.filters: list[tuple[str, str]] = []

        def where(self, *conds):
            self.filters.extend(conds)
            return self

    def select(model):
        return DummyQuery(model)

    class AsyncSession:  # pragma: no cover - simple placeholder
        pass

    sqlalchemy_future_stub.select = select
    sqlalchemy_ext_asyncio_stub.AsyncSession = AsyncSession
    monkeypatch.setitem(sys.modules, "sqlalchemy", sqlalchemy_stub)
    monkeypatch.setitem(sys.modules, "sqlalchemy.future", sqlalchemy_future_stub)
    monkeypatch.setitem(sys.modules, "sqlalchemy.ext", sqlalchemy_ext_stub)
    monkeypatch.setitem(sys.modules, "sqlalchemy.ext.asyncio", sqlalchemy_ext_asyncio_stub)

    # Stub models
    user_mod = types.ModuleType("app.models.user")

    class User:  # pragma: no cover - simple data container
        def __init__(self, id, email_verified=True):
            self.id = id
            self.email_verified = email_verified

    user_mod.User = User
    monkeypatch.setitem(sys.modules, "app.models.user", user_mod)

    class WalletField:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            return (self.name, other)

    wallet_mod = types.ModuleType("app.models.wallet")

    class Wallet:  # pragma: no cover - simple container
        user_id = WalletField("user_id")
        currency = WalletField("currency")
        network = WalletField("network")

        def __init__(self, user_id, wallet_id, address, currency, network):
            self.user_id = user_id
            self.wallet_id = wallet_id
            self.address = address
            self.currency = currency
            self.network = network
            self.id = uuid.uuid4()
            self.created_at = 0

    wallet_mod.Wallet = Wallet
    monkeypatch.setitem(sys.modules, "app.models.wallet", wallet_mod)

    wallet_log_mod = types.ModuleType("app.models.wallet_log")

    class WalletLog:  # pragma: no cover - placeholder
        def __init__(self, *args, **kwargs):
            pass

    wallet_log_mod.WalletLog = WalletLog
    monkeypatch.setitem(sys.modules, "app.models.wallet_log", wallet_log_mod)

    # Stub Pydantic schemas
    schemas_wallet_mod = types.ModuleType("app.schemas.wallet")
    for name in ["WalletOut", "WalletBalance", "WithdrawalRequest", "WithdrawalResponse"]:
        setattr(schemas_wallet_mod, name, type(name, (), {}))
    monkeypatch.setitem(sys.modules, "app.schemas.wallet", schemas_wallet_mod)

    # Stub Fireblocks service
    fireblocks_mod = types.ModuleType("app.services.fireblocks")

    async def create_vault_account(name: str, asset: str):
        return {
            "vault_account_id": "2",
            "address": "ADDR123",
            "asset": asset,
        }

    fireblocks_mod.create_vault_account = create_vault_account
    monkeypatch.setitem(sys.modules, "app.services.fireblocks", fireblocks_mod)

    # Stub database dependency
    database_mod = types.ModuleType("app.database")

    async def get_db():  # pragma: no cover - placeholder generator
        yield None

    database_mod.get_db = get_db
    monkeypatch.setitem(sys.modules, "app.database", database_mod)

    # Stub auth utilities
    auth_mod = types.ModuleType("app.utils.auth")

    def get_current_user():  # pragma: no cover - placeholder
        pass

    auth_mod.get_current_user = get_current_user
    monkeypatch.setitem(sys.modules, "app.utils.auth", auth_mod)

    # Ensure repository root is on sys.path for imports
    sys.path.append(str(Path(__file__).resolve().parents[1]))

    # Import the function under test
    from app.routes.wallet import create_user_wallet, Wallet as RouteWallet

    class DummyResult:
        def __init__(self, wallet):
            self._wallet = wallet

        def scalar_one_or_none(self):
            return self._wallet

    class DummySession:
        def __init__(self, wallet):
            self.wallet = wallet

        async def execute(self, query):
            # Ensure query filters by user, currency and network
            assert ("currency", "BTC_TEST") in query.filters
            assert ("network", "FIREBLOCKS") in query.filters
            assert ("user_id", self.wallet.user_id) in query.filters

            if self.wallet and all(getattr(self.wallet, f[0]) == f[1] for f in query.filters):
                return DummyResult(self.wallet)
            return DummyResult(None)

        def add(self, obj):
            if isinstance(obj, RouteWallet):
                self.wallet = obj

        async def commit(self):
            pass

        async def refresh(self, obj):
            pass

    user = User(id="user-1", email_verified=True)
    existing = RouteWallet(
        user_id=user.id,
        wallet_id="1",
        address="",
        currency="VAULT",
        network="FIREBLOCKS",
    )
    session = DummySession(existing)

    result = asyncio.run(create_user_wallet(current_user=user, db=session))

    assert result.wallet_id == "2"
    assert result.address == "ADDR123"
    assert result.currency == "BTC_TEST"

