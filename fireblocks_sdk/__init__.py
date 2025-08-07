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

