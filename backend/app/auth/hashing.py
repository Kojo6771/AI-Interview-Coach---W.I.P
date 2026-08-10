#import the necessary libraries
from passlib.context import CryptContext

# bcrypt is limited to a 72-byte input on the underlying implementation.
# Truncate the credential to that boundary before hashing / verification.
MAX_BCRYPT_PASSWORD_BYTES = 72

#create a CryptContext object to handle password hashing and verification
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def _normalise_bcrypt_password(password: str) -> str:
    if password is None:
        return password

    # The hash backend sees the bytes of the UTF-8 encoding when using passlib.
    # A Python str may contain multi-byte characters, so we compute the encoded length
    # and trim the logical string to the maximum byte size that bcrypt accepts.
    bytes_to_cut = len(password.encode("utf-8"))
    if bytes_to_cut <= MAX_BCRYPT_PASSWORD_BYTES:
        return password

    safe_password = password.encode("utf-8")[:MAX_BCRYPT_PASSWORD_BYTES].decode("utf-8", errors="ignore")
    return safe_password

# define a function to hash a password using the CryptContext object
def hash_password(password: str):
    password = _normalise_bcrypt_password(password)
    return pwd_context.hash(password)

# define a function to verify a password against a hashed password using the CryptContext object
def verify_password(
        plain_password: str,
        hashed_password: str
):
    plain_password = _normalise_bcrypt_password(plain_password)
    return pwd_context.verify(plain_password, hashed_password)