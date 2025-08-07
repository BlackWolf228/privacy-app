"""A minimal stub of the Fireblocks SDK used for testing.

The real package normally provides network connectivity to the Fireblocks
platform.  In this repository we only require the class definition so tests can
mock its behaviour without relying on the external dependency.
"""


class FireblocksSDK:  # pragma: no cover - simple placeholder
    def __init__(self, private_key: str, api_key: str, api_base_url: str | None = None):
        self.private_key = private_key
        self.api_key = api_key
        self.api_base_url = api_base_url

    # The real SDK exposes many methods; for testing we only define the ones
    # our code calls.  They simply return empty structures so tests can mock
    # them without importing the real dependency.

    def create_vault_account(self, name: str):  # type: ignore[override]
        return {"id": "", "name": name}

    def generate_deposit_address(self, vault_account_id: str, asset_id: str):  # type: ignore[override]
        return {"address": ""}

