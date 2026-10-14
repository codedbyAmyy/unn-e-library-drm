
from datetime import datetime, timezone

import jwt
import pytest

from app.config import settings
from app.utils.tokens import create_access_token, decode_access_token


def test_create_and_decode_access_token():
    token = create_access_token(user_id=123, role="student")
    payload = decode_access_token(token)

    assert payload["sub"] == "123"
    assert payload["role"] == "student"
    assert "exp" in payload
    assert "iat" in payload


def test_invalid_token_is_rejected():
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("this-is-not-a-valid-token")


def test_token_signed_with_wrong_secret_is_rejected():
    token = jwt.encode(
        {
            "sub": "123",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc).replace(
                year=datetime.now(timezone.utc).year + 1
            ),
        },
        "a-completely-different-secret",
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)
