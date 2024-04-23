# Imports
import jwt
from dotenv import load_dotenv
import os
import datetime
from fastapi import HTTPException, status, Header

# Load Environment Variables
load_dotenv('.env')

###############################################################################
# JWT Authentication Helper Functions
###############################################################################
JWT_ALGORITHM = "HS256"

# Function to Create JWT Token Signing
def create_access_token(exp_mins: int, data: dict):
    # copies data dict
    to_encode = data.copy()
    
    # Creates expiration time
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=exp_mins)
    
    # Adds expiration time to data dict
    to_encode.update({"exp": expire})
    
    # Creates JWT Token
    encoded_jwt = jwt.encode(to_encode, os.environ['JWT_CREATION_SECRET'], algorithm=JWT_ALGORITHM)
    
    # returns JWT Token
    return encoded_jwt

# Function to Decode and Validate JWT Token
def decode_and_validate_token(token: str):
    try:
        # Decodes JWT token
        payload = jwt.decode(token, os.environ['JWT_CREATION_SECRET'], algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

###############################################################################
# JWT Dependency Function
###############################################################################
# Function to secure API endpoints by checking for valid JWT token in Header
# PASS IN THIS TO PARAMS OF ENDPOINT TO SECURE: "email: str = Depends(jwt_dependency)""
def jwt_dependency(authorization: str = Header(...)):
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing..."
        )
    
    try:
        # Splits Authorization Header
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme..."
            )
        
        # Decode and validate JWT token
        payload = decode_and_validate_token(token)
        
        # Return the 'sub' value from the payload
        return payload.get('sub')
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Authorization Header Format. Error: {e}"
        )