from fastapi import APIRouter

# Router dedicated to authentication-related endpoints.
# The prefix '/auth' is applied to all routes in this module.
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# Health-check endpoint for the auth router.
# Use this to confirm auth routes are mounted correctly.
@router.get("/")
def auth_test():
    return {
        "message": "Authentication route is working!"
    }