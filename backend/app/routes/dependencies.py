# Import necessary modules and dependencies
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import Secret_Key, Algorithm
from app.database import get_db
from app.models.user import User


# Define the OAuth2PasswordBearer instance for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

# Define a function to get the current authenticated user based on the provided token
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try to decode the JWT token and extract the user ID from the payload
    try:
        payload = jwt.decode(
            token,
            Secret_Key,
            algorithms=[Algorithm]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

# Query the database for the user with the extracted user ID
    user = (
        db.query(User)
        .filter(User.id == int(user_id))
        .first()
    )

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

# Return the authenticated user object
    return user