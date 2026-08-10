#import the necessary libraries
from passlib.context import CryptContext

#create a CryptContext object to handle password hashing and verification
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# define a function to hash a password using the CryptContext object
def hash_password(password: str):
    return pwd_context.hash(password)

# define a function to verify a password against a hashed password using the CryptContext object
def verify_password(
        plain_password: str,
        hashed_password: str
):
    return pwd_context.verify(plain_password, hashed_password)