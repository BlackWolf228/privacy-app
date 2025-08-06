import secrets


def generate_code():
    return f"{secrets.randbelow(900000) + 100000:06d}"


def test_generate_code(monkeypatch):
    def fake_randbelow(n):
        assert n == 900000
        return 123

    monkeypatch.setattr(secrets, "randbelow", fake_randbelow)
    code = generate_code()
    assert code == "100123"
    assert len(code) == 6
