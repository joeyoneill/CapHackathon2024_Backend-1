# Imports
from fastapi import APIRouter, status, Depends
from pydantic import BaseModel
from azure.cosmos import CosmosClient
import os
from dotenv import load_dotenv

# In-App Dependencies
from dependencies import create_access_token, jwt_dependency

# Load Environment Variables
load_dotenv('.env')

###############################################################################
# Initialize Router
###############################################################################
router = APIRouter()

###############################################################################
# Endpoints
###############################################################################
# Register Request Body Class
class RegisterRequest(BaseModel):
    email: str
    password_hash: str

# Adds User to Database
@router.post("/auth/register", tags=["Authentication"])
def register(request: RegisterRequest):
    try:
        # Get Cosmos Client
        client = CosmosClient.from_connection_string(conn_str=os.environ['COSMOS_CONNECTION_STRING'])
        
        # Get Cosmos DB
        database = client.get_database_client(os.environ['COSMOS_DB_NAME'])
        
        # Get Cosmos Container
        container = database.get_container_client(os.environ['COSMOS_USERS_CONTAINER_NAME'])
        
        # Check if Unique
        try:
            user = container.read_item(
                item=f'id-{request.email}',
                partition_key=request.email
            )
            return {
                'status': status.HTTP_400_BAD_REQUEST,
                'detail': 'User Already Exists!'
            }
        except Exception as e:
            pass
        
        # Create User
        container.upsert_item(body={
            'id': f'id-{request.email}',
            'UserId': request.email,
            'password': request.password_hash
        })
        
        # return Success
        return {
            'status': status.HTTP_201_CREATED,
            'detail': 'User Created Successfully!'
        }
    
    except Exception as e:
        # return Failure
        return {
            'status': status.HTTP_400_BAD_REQUEST,
            'detail': f'User Creation Failed. Error: {e}'
        }

# Login Request Body Class
class LoginRequest(BaseModel):
    email: str
    password_hash: str

# Checks if User is Valid
@router.post("/auth/login", tags=["Authentication"])
def login(request: LoginRequest):
    try:
        # Get Cosmos Client
        client = CosmosClient.from_connection_string(conn_str=os.environ['COSMOS_CONNECTION_STRING'])
        
        # Get Cosmos DB
        database = client.get_database_client(os.environ['COSMOS_DB_NAME'])
        
        # Get Cosmos Container
        container = database.get_container_client(os.environ['COSMOS_USERS_CONTAINER_NAME'])
        
        # Find User
        user = container.read_item(
            item=f'id-{request.email}',
            partition_key=request.email
        )
        
        # Check Password
        if user['password'] == request.password_hash:
            
            # Create JWT Access Token
            jwt_token = create_access_token(60, {'sub': request.email})
            
            # Return Successful Login
            return {
                'status': status.HTTP_200_OK,
                'detail': 'User Login Successful!',
                'jwt': jwt_token
            }
        else:
            return {
                'status': status.HTTP_400_BAD_REQUEST,
                'detail': 'User Login Failed. Password Incorrect.'
            }
    
    except Exception as e:
        return {
            'status': status.HTTP_400_BAD_REQUEST,
            'detail': f'User Login Failed. Error: {e}'
        }