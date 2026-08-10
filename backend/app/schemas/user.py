from pydantic import BaseModel, EmailStr


class UserRegistration(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class token(BaseModel):
    access_token: str
    token_type: str