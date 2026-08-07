from fastapi import APIRouter

router = APIRouter(
    prefix = "/auth",
    tags = ["Authentication"]
)

@router.get("/")
def auth_test():
    return{
        "message": "Authentication route is working!"
    }