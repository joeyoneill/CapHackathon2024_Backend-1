# Imports
import jwt
from dotenv import load_dotenv
import os
import datetime
from fastapi import HTTPException, status, Header
import uuid
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)

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
        return str(payload.get('sub')).lower()
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Authorization Header Format. Error: {e}"
        )

###############################################################################
# Azure Helper Functions
###############################################################################
# Creates UUID for Azure Blob Container Name
def get_uuid_for_blob_container():
    # Generate UUID for Container Name
    unique_id = str(uuid.uuid4())
    
    # Remove hyphens from UUID
    unique_id = unique_id.replace('-', '').lower()[:63]
    
    # Get Cosmos Container
    client = CosmosClient.from_connection_string(conn_str=os.environ['COSMOS_CONNECTION_STRING'])
    database = client.get_database_client(os.environ['COSMOS_DB_NAME'])
    container = database.get_container_client(os.environ['COSMOS_USERCONTAINERNAME_CONTAINER_NAME'])
    
    while True:
        # Check if UUID Container Already Exists in Cosmos
        try:
            query = "SELECT * FROM c WHERE c.id = @id"
            params = [
                {'name': '@id', 'value': str(unique_id)}
            ]
            query_iterable = container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True
            )
            items = list(query_iterable)
            if not items:
                return unique_id
        except:
            return False


# Creates a User's Azure AI Search Index
def create_user_search_index(unique_id: str):
    try:
        # Get Azure Search Client
        search_client = SearchIndexClient(
            endpoint=os.environ['AZURE_SEARCH_SERVICE_ENDPOINT'],
            credential=AzureKeyCredential(os.environ['AZURE_SEARCH_ADMIN_KEY'])
        )

        # Initialize AI Search Index w/ vector search
        index = SearchIndex(
            name=unique_id,
            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="content", type=SearchFieldDataType.String, searchable=True),
                SimpleField(name="metadata", type=SearchFieldDataType.String, searchable=True),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name=f'{unique_id}-vector-config'
                )
            ],
            vector_search = VectorSearch(
                profiles=[VectorSearchProfile(
                    name=f'{unique_id}-vector-config',
                    algorithm_configuration_name=f'{unique_id}-algorithms-config'
                )],
                algorithms=[HnswAlgorithmConfiguration(name=f'{unique_id}-algorithms-config')],
            )
        )

        # Create AI Search Index
        search_client.create_index(index)
        
        # Return Success
        return True
    except:
        return False
    

# Creates a User's Azure Blob Container & AI Search Index
def create_user_blob_container_and_index(user_email: str):
    # save to lower
    user_email = user_email.lower()
    
    # To check if container was created or not
    container_created = False
    cosmos_item_saved = False
    
    # Generate UUID for Container Name
    unique_id = get_uuid_for_blob_container()
    if not unique_id:
        return False
    
    # Try to create the Blob Container
    try:
        # Create Blob Container
        blob_service_client = BlobServiceClient.from_connection_string(os.environ['AZURE_BLOB_CONN_STR'])
        container_client = blob_service_client.create_container(unique_id)
        container_created = True
    except Exception as e:
        print(f'ERROR IN CONTAINER CREATION FOR {user_email}: {e}')
        return False
    
    # Try to save the Blob Container Name to Cosmos
    try:
        # Get Cosmos Container
        client = CosmosClient.from_connection_string(conn_str=os.environ['COSMOS_CONNECTION_STRING'])
        database = client.get_database_client(os.environ['COSMOS_DB_NAME'])
        container = database.get_container_client(os.environ['COSMOS_USERCONTAINERNAME_CONTAINER_NAME'])
        
        # Create User Container Item for Cosmos
        container.upsert_item(body={
            'id': unique_id,
            'UserId': user_email
        })
        cosmos_item_saved = True
        
    except:
        # Delete Blob Container if Cosmos Save Fails
        if container_created:
            blob_service_client.delete_container(unique_id)        
        return False
    
    # Try to create the Azure AI Search Index
    if create_user_search_index(unique_id):
        
        # return success
        return True
    else:
        try:
            # Rollback Creations if failure
            if container_created:
                blob_service_client.delete_container(unique_id)
            if cosmos_item_saved:
                container.delete_item(unique_id, user_email)
        except:
            pass
        
        # Return Fail
        return False

###############################################################################
# Cosmos Helper Functions
###############################################################################
# Return's the Container/Search Index Name for a user
# Container Names and Search Index Names are the same
def get_user_uuid(user_email: str):
    # Get Cosmos Container
    client = CosmosClient.from_connection_string(conn_str=os.environ['COSMOS_CONNECTION_STRING'])
    database = client.get_database_client(os.environ['COSMOS_DB_NAME'])
    container = database.get_container_client(os.environ['COSMOS_USERCONTAINERNAME_CONTAINER_NAME'])
    
    try:
        query = "SELECT * FROM c WHERE c.UserId = @user_email"
        params = [
            {'name': '@user_email', 'value': user_email}
        ]
        query_iterable = container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        )
        items = list(query_iterable)
        if items:
            return items[0]['id']
        else:
            return False
    except:
        return False