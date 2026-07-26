from datetime import timedelta

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_verify():
    password_hash = hash_password("Doctor@123")
    assert verify_password("Doctor@123", password_hash)
    assert not verify_password("wrong", password_hash)


def test_access_token_roundtrip():
    token = create_access_token("42", "doctor", timedelta(minutes=5))
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "doctor"
