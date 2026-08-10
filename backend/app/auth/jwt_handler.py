#import nessesary libraries
from jose import jwt
from datetime import datetime, timedelta

from app.config import (
    Secret_Key,
    Algorithm,
    Access_Token_Expire_Minutes
)

def create_access_token(data: dict):
    # Create a copy of the data to avoid modifying the original dictionary
    to_encode = data.copy()
    
    # Calculate the expiration time for the token
    expire = datetime.utcnow() + timedelta(minutes=Access_Token_Expire_Minutes)
    
    # Add the expiration time to the data to be encoded in the token
    to_encode.update({"exp": expire})
    
    # Encode the data into a JWT using the secret key and algorithm specified in the config
    encoded_jwt = jwt.encode(to_encode, Secret_Key, algorithm=Algorithm)
    
    return encoded_jwt
