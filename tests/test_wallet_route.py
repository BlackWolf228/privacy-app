import asyncio
import sys
import types
import uuid
from pathlib import Path


def setup_route(monkeypatch):
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

    class Field:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            return (self.name, other)

    wallet_mod = types.ModuleType("app.models.wallet")

    class Wallet:  # pragma: no cover - simple container
        user_id = Field("user_id")
        currency = Field("currency")
        network = Field("network")

        def __init__(self, user_id, vault_id, address, currency, network):
            self.user_id = user_id
            self.vault_id = vault_id
            self.address = address
            self.currency = currency
            self.network = network
            self.id = uuid.uuid4()
            self.created_at = 0

    wallet_mod.Wallet = Wallet
    monkeypatch.setitem(sys.modules, "app.models.wallet", wallet_mod)

    vault_mod = types.ModuleType("app.models.vault")

    class Vault:  # pragma: no cover - simple container
        user_id = Field("user_id")

        def __init__(self, vault_id, user_id):
            self.vault_id = vault_id
            self.user_id = user_id

    vault_mod.Vault = Vault
    monkeypatch.setitem(sys.modules, "app.models.vault", vault_mod)

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
    calls: list[tuple[str, str, str]] = []

    async def create_vault_account(name: str, asset: str):
        calls.append(("create_vault_account", name, asset))
        return {
            "vault_account_id": "V1",
            "address": f"ADDR_{asset}",
            "asset": asset,
        }

    async def generate_address_for_vault(vault_id: str, asset: str):
        calls.append(("generate_address_for_vault", vault_id, asset))
        return f"ADDR_{asset}"

    fireblocks_mod.create_vault_account = create_vault_account
    fireblocks_mod.generate_address_for_vault = generate_address_for_vault
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

    # Reload route module each time to pick up stubs
    sys.modules.pop("app.routes.wallet", None)
    from app.routes.wallet import create_user_wallet
    from app.models.wallet import Wallet as RouteWallet
    from app.models.vault import Vault as RouteVault

    class DummyResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class DummySession:
        def __init__(self):
            self.vault = None
            self.wallets: list[RouteWallet] = []

        async def execute(self, query):
            if query.model is RouteWallet:
                for w in self.wallets:
                    if all(getattr(w, f[0]) == f[1] for f in query.filters):
                        return DummyResult(w)
                return DummyResult(None)
            if query.model is RouteVault:
                if self.vault and all(getattr(self.vault, f[0]) == f[1] for f in query.filters):
                    return DummyResult(self.vault)
                return DummyResult(None)
            return DummyResult(None)

        def add(self, obj):
            if isinstance(obj, RouteWallet):
                self.wallets.append(obj)
            elif isinstance(obj, RouteVault):
                self.vault = obj

        async def commit(self):
            pass

        async def refresh(self, obj):
            pass

    return create_user_wallet, User, DummySession, calls


def test_multiple_wallet_creations_reuse_same_vault(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    session = DummySession()
    user = User(id="user-1", email_verified=True)

    wallet1 = asyncio.run(create_user_wallet("BTC_TEST", current_user=user, db=session))
    wallet2 = asyncio.run(create_user_wallet("ETH_TEST", current_user=user, db=session))

    assert wallet1.vault_id == wallet2.vault_id
    assert calls == [
        ("create_vault_account", "user-1", "BTC_TEST"),
        ("generate_address_for_vault", "V1", "ETH_TEST"),
    ]


def test_creating_wallet_for_existing_asset_returns_existing(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    session = DummySession()
    user = User(id="user-1", email_verified=True)

    wallet1 = asyncio.run(create_user_wallet("BTC_TEST", current_user=user, db=session))
    calls.clear()
    wallet2 = asyncio.run(create_user_wallet("BTC_TEST", current_user=user, db=session))

    assert wallet1 is wallet2
    assert calls == []

