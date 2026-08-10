# Import necessary modules and dependencies
from fastapi import APIRouter, Depends

from app.routes.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

# Define the users router with a prefix and tags
router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# Define the endpoint to get the current authenticated user's information
@router.get(
    "/me",
    response_model=UserResponse
)

# Define the get_me function to retrieve the current authenticated user's information
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user