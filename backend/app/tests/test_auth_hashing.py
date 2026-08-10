from app.auth.hashing import hash_password, verify_password


def test_hash_and_verify_accept_long_credentials_without_bcrypt_byte_error():
    long_password = "x" * 100

    hashed = hash_password(long_password)

    assert verify_password(long_password, hashed) is True
