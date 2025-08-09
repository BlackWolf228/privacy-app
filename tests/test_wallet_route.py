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

    class Field:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            return (self.name, other)

    class User:  # pragma: no cover - simple data container
        id = Field("id")
        privacy_id = Field("privacy_id")
        username = Field("username")

        def __init__(self, id, email_verified=True, has_vault=False, privacy_id="", username=None):
            self.id = id
            self.email_verified = email_verified
            self.has_vault = has_vault
            self.privacy_id = privacy_id
            self.username = username

    user_mod.User = User
    monkeypatch.setitem(sys.modules, "app.models.user", user_mod)


    wallet_mod = types.ModuleType("app.models.wallet")

    class Wallet:  # pragma: no cover - simple container
        id = Field("id")
        user_id = Field("user_id")
        address = Field("address")
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

    transaction_mod = types.ModuleType("app.models.transaction")

    class TxType:  # pragma: no cover - simple enum placeholder
        crypto_out = "crypto_out"
        internal_out = "internal_out"
        internal_in = "internal_in"

    class TxStatus:  # pragma: no cover - simple enum placeholder
        pending = "pending"

    class Transaction:  # pragma: no cover - lightweight stand-in
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    transaction_mod.Transaction = Transaction
    transaction_mod.TxType = TxType
    transaction_mod.TxStatus = TxStatus
    monkeypatch.setitem(sys.modules, "app.models.transaction", transaction_mod)
    RouteTransaction = Transaction

    # Stub Pydantic schemas
    schemas_wallet_mod = types.ModuleType("app.schemas.wallet")
    def _model_factory(name):
        class Model:  # pragma: no cover - lightweight stand-in
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        Model.__name__ = name
        return Model

    for name in [
        "WalletOut",
        "WalletBalance",
        "WithdrawalRequest",
        "WithdrawalResponse",
        "InternalTransferRequest",
        "DonationRequest",
        "FeeEstimateRequest",
        "FeeEstimateResponse",
    ]:
        setattr(schemas_wallet_mod, name, _model_factory(name))
    monkeypatch.setitem(sys.modules, "app.schemas.wallet", schemas_wallet_mod)

    # Stub Fireblocks service
    fireblocks_mod = types.ModuleType("app.services.fireblocks")
    calls: list[tuple] = []

    class AssetAlreadyExistsError(Exception):  # pragma: no cover - simple stub
        pass

    async def create_vault_account(name: str):
        calls.append(("create_vault_account", name))
        return {
            "vault_account_id": "V1",
        }

    async def create_asset_for_vault(vault_id: str, asset: str):
        calls.append(("create_asset_for_vault", vault_id, asset))
        return f"ADDR_{asset}"

    async def generate_address_for_vault(vault_id: str, asset: str):
        calls.append(("generate_address_for_vault", vault_id, asset))
        return f"ADDR_{asset}"

    async def get_wallet_balance(vault_id: str, asset: str):
        calls.append(("get_wallet_balance", vault_id, asset))
        return {
            "balance": "0",
            "asset": asset,
            "pending_balance": "0",
            "available_balance": "0",
        }

    async def create_transfer(vault_id: str, asset: str, amount: str, address: str):
        calls.append(("create_transfer", vault_id, asset, amount, address))
        return {"id": "T1", "status": "COMPLETED"}

    async def estimate_transaction_fee(asset: str, amount: str):
        calls.append(("estimate_transaction_fee", asset, amount))
        return {"low": "0.1", "medium": "0.2", "high": "0.3"}

    async def transfer_between_vault_accounts(
        source_vault_id: str, dest_vault_id: str, asset: str, amount: str
    ):
        calls.append(
            (
                "transfer_between_vault_accounts",
                source_vault_id,
                dest_vault_id,
                asset,
                amount,
            )
        )
        return {"id": "T2", "status": "COMPLETED"}

    fireblocks_mod.create_vault_account = create_vault_account
    fireblocks_mod.create_asset_for_vault = create_asset_for_vault
    fireblocks_mod.generate_address_for_vault = generate_address_for_vault
    fireblocks_mod.get_wallet_balance = get_wallet_balance
    fireblocks_mod.create_transfer = create_transfer
    fireblocks_mod.estimate_transaction_fee = estimate_transaction_fee
    fireblocks_mod.transfer_between_vault_accounts = transfer_between_vault_accounts
    fireblocks_mod.AssetAlreadyExistsError = AssetAlreadyExistsError
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
    from app.models.user import User as RouteUser

    class DummyResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class DummySession:
        def __init__(self):
            self.vault = None
            self.wallets: list[RouteWallet] = []
            self.users: list[RouteUser] = []
            self.transactions: list[RouteTransaction] = []

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
            if query.model is RouteUser:
                for u in self.users:
                    if all(getattr(u, f[0]) == f[1] for f in query.filters):
                        return DummyResult(u)
                return DummyResult(None)
            return DummyResult(None)

        def add(self, obj):
            if isinstance(obj, RouteWallet):
                self.wallets.append(obj)
            elif isinstance(obj, RouteVault):
                self.vault = obj
            elif isinstance(obj, RouteUser):
                self.users.append(obj)
            elif isinstance(obj, RouteTransaction):
                self.transactions.append(obj)

        def add_all(self, objs):
            for obj in objs:
                self.add(obj)

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
        ("create_vault_account", "user-1"),
        ("create_asset_for_vault", "V1", "BTC_TEST"),
        ("create_asset_for_vault", "V1", "ETH_TEST"),
    ]


def test_user_with_existing_vault_uses_existing_id(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    from app.models.vault import Vault as RouteVault

    session = DummySession()
    user = User(id="user-1", email_verified=True, has_vault=True)
    session.vault = RouteVault(vault_id="V1", user_id=user.id)

    wallet = asyncio.run(create_user_wallet("BTC_TEST", current_user=user, db=session))

    assert wallet.vault_id == "V1"
    assert calls == [("create_asset_for_vault", "V1", "BTC_TEST")]


def test_creating_wallet_for_existing_asset_returns_existing(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    session = DummySession()
    user = User(id="user-1", email_verified=True)

    wallet1 = asyncio.run(create_user_wallet("BTC_TEST", current_user=user, db=session))
    calls.clear()
    wallet2 = asyncio.run(create_user_wallet("BTC_TEST", current_user=user, db=session))

    assert wallet1 is wallet2
    assert calls == []


def test_create_vault(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    from app.routes.wallet import create_user_vault

    session = DummySession()
    user = User(id="user-1", email_verified=True)

    vault = asyncio.run(create_user_vault(current_user=user, db=session))

    assert vault.vault_id == "V1"
    assert user.has_vault is True
    assert calls == [("create_vault_account", "user-1")]

    try:
        asyncio.run(create_user_vault(current_user=user, db=session))
        assert False, "Expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    assert calls == [("create_vault_account", "user-1")]


def test_adding_existing_asset_returns_409(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    from app.routes import wallet as wallet_route
    from app.services.fireblocks import AssetAlreadyExistsError
    from app.models.vault import Vault as RouteVault

    async def raise_exists(vault_id: str, asset: str):
        calls.append(("create_asset_for_vault", vault_id, asset))
        raise AssetAlreadyExistsError("exists")

    wallet_route.create_asset_for_vault = raise_exists

    session = DummySession()
    user = User(id="user-1", email_verified=True, has_vault=True)
    session.vault = RouteVault(vault_id="V1", user_id=user.id)

    try:
        asyncio.run(create_user_wallet("BTC_TEST", current_user=user, db=session))
        assert False, "Expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
        assert getattr(exc, "detail", None) == "asset already provisioned for this vault"

    assert calls == [("create_asset_for_vault", "V1", "BTC_TEST")]


def test_external_transfer_internal_when_address_matches(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    from app.routes.wallet import external_transfer
    from app.models.wallet import Wallet as RouteWallet
    from app.schemas.wallet import WithdrawalRequest

    session = DummySession()
    user = User(id="user-1", email_verified=True, has_vault=True)

    wallet = RouteWallet(
        user_id=user.id,
        vault_id="V1",
        address="SRCADDR",
        currency="BTC_TEST",
        network="FIREBLOCKS",
    )
    session.add(wallet)

    dest_wallet = RouteWallet(
        user_id="user-2",
        vault_id="V2",
        address="DESTADDR",
        currency="BTC_TEST",
        network="FIREBLOCKS",
    )
    session.add(dest_wallet)

    payload = WithdrawalRequest(address="DESTADDR", amount="1", asset="BTC_TEST")

    result = asyncio.run(
        external_transfer(wallet.id, payload, current_user=user, db=session)
    )

    assert result.transfer_id == "T2"
    assert calls == [
        ("get_wallet_balance", "V1", "BTC_TEST"),
        ("get_wallet_balance", "V2", "BTC_TEST"),
        ("transfer_between_vault_accounts", "V1", "V2", "BTC_TEST", "1"),
    ]
    assert len(session.transactions) == 2
    assert session.transactions[0].type == "internal_out"
    assert session.transactions[1].type == "internal_in"
    assert session.transactions[0].counterparty_user == "user-2"
    assert session.transactions[1].counterparty_user == "user-1"
    assert session.transactions[0].group_id == session.transactions[1].group_id


def test_external_transfer_external_when_unknown_address(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    from app.routes.wallet import external_transfer
    from app.models.wallet import Wallet as RouteWallet
    from app.schemas.wallet import WithdrawalRequest

    session = DummySession()
    user = User(id="user-1", email_verified=True, has_vault=True)

    wallet = RouteWallet(
        user_id=user.id,
        vault_id="V1",
        address="SRCADDR",
        currency="BTC_TEST",
        network="FIREBLOCKS",
    )
    session.add(wallet)

    payload = WithdrawalRequest(address="UNKNOWN", amount="1", asset="BTC_TEST")

    result = asyncio.run(
        external_transfer(wallet.id, payload, current_user=user, db=session)
    )

    assert result.transfer_id == "T1"
    assert calls == [
        ("get_wallet_balance", "V1", "BTC_TEST"),
        ("create_transfer", "V1", "BTC_TEST", "1", "UNKNOWN"),
    ]
    assert len(session.transactions) == 1
    assert session.transactions[0].type == "crypto_out"
    assert session.transactions[0].address_to == "UNKNOWN"


def test_internal_transfer_between_users(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    from app.routes.wallet import internal_transfer
    from app.models.wallet import Wallet as RouteWallet
    from app.schemas.wallet import InternalTransferRequest

    session = DummySession()
    user = User(id="user-1", email_verified=True, has_vault=True)
    dest_user = User(
        id="user-2",
        email_verified=True,
        has_vault=True,
        privacy_id="DESTID",
        username="destuser",
    )
    session.add(dest_user)

    wallet = RouteWallet(
        user_id=user.id,
        vault_id="V1",
        address="SRCADDR",
        currency="BTC_TEST",
        network="FIREBLOCKS",
    )
    session.add(wallet)
    dest_wallet = RouteWallet(
        user_id=dest_user.id,
        vault_id="V2",
        address="DESTADDR",
        currency="BTC_TEST",
        network="FIREBLOCKS",
    )
    session.add(dest_wallet)

    payload = InternalTransferRequest(
        destination_user_id="DESTID", amount="1", asset="BTC_TEST"
    )
    result = asyncio.run(
        internal_transfer(wallet.id, payload, current_user=user, db=session)
    )

    assert result.transfer_id == "T2"
    assert calls == [
        ("get_wallet_balance", "V1", "BTC_TEST"),
        ("get_wallet_balance", "V2", "BTC_TEST"),
        ("transfer_between_vault_accounts", "V1", "V2", "BTC_TEST", "1"),
    ]
    assert len(session.transactions) == 2
    assert session.transactions[0].type == "internal_out"
    assert session.transactions[1].type == "internal_in"
    assert session.transactions[0].counterparty_user == dest_user.id
    assert session.transactions[1].counterparty_user == user.id
    assert session.transactions[0].group_id == session.transactions[1].group_id


def test_donation_transfers_to_configured_privacy_id(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    from app.routes.wallet import donate
    from app.models.wallet import Wallet as RouteWallet
    from app.schemas.wallet import DonationRequest
    from app.config import settings

    settings.DONATION_PRIVACY_ID = "DONATE"

    session = DummySession()
    user = User(id="user-1", email_verified=True, has_vault=True)

    wallet = RouteWallet(
        user_id=user.id,
        vault_id="V1",
        address="SRCADDR",
        currency="BTC_TEST",
        network="FIREBLOCKS",
    )
    session.add(wallet)

    dest_user = User(id="user-2", email_verified=True, has_vault=True, privacy_id="DONATE")
    session.add(dest_user)
    dest_wallet = RouteWallet(
        user_id=dest_user.id,
        vault_id="V2",
        address="DONADDR",
        currency="BTC_TEST",
        network="FIREBLOCKS",
    )
    session.add(dest_wallet)

    payload = DonationRequest(amount="1", asset="BTC_TEST")

    result = asyncio.run(donate(wallet.id, payload, current_user=user, db=session))

    assert result.transfer_id == "T2"
    assert calls == [
        ("get_wallet_balance", "V1", "BTC_TEST"),
        ("get_wallet_balance", "V2", "BTC_TEST"),
        ("transfer_between_vault_accounts", "V1", "V2", "BTC_TEST", "1"),
    ]
    assert len(session.transactions) == 2
    assert session.transactions[0].type == "internal_out"
    assert session.transactions[1].type == "internal_in"
    assert session.transactions[0].counterparty_user == dest_user.id
    assert session.transactions[1].counterparty_user == user.id
    assert session.transactions[0].group_id == session.transactions[1].group_id


def test_donation_asset_mismatch_raises(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    from app.routes.wallet import donate
    from app.models.wallet import Wallet as RouteWallet
    from app.schemas.wallet import DonationRequest
    from app.config import settings

    settings.DONATION_PRIVACY_ID = "DONATE"

    session = DummySession()
    user = User(id="user-1", email_verified=True, has_vault=True)

    wallet = RouteWallet(
        user_id=user.id,
        vault_id="V1",
        address="SRCADDR",
        currency="BTC_TEST",
        network="FIREBLOCKS",
    )
    session.add(wallet)

    try:
        asyncio.run(
            donate(
                wallet.id,
                DonationRequest(amount="1", asset="ETH_TEST"),
                current_user=user,
                db=session,
            )
        )
        assert False, "Expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400


def test_estimate_fee_route(monkeypatch):
    create_user_wallet, User, DummySession, calls = setup_route(monkeypatch)
    from app.routes.wallet import estimate_fee
    from app.schemas.wallet import FeeEstimateRequest

    user = User(id="user-1", email_verified=True)
    payload = FeeEstimateRequest(asset="BTC_TEST", amount="0.5")

    result = asyncio.run(estimate_fee(payload, current_user=user))

    assert result == {"low": "0.1", "medium": "0.2", "high": "0.3"}
    assert calls[-1] == ("estimate_transaction_fee", "BTC_TEST", "0.5")

