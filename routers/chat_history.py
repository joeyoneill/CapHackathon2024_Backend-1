# Imports
from fastapi import APIRouter, Depends
from azure.cosmos import CosmosClient
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# In-App Dependencies
from dependencies import jwt_dependency

# Load Environment Variables
load_dotenv('.env')

# Configure the root logger to log all messages
logging.basicConfig(level=logging.DEBUG)

###############################################################################
# Initialize Router
###############################################################################
router = APIRouter()

###############################################################################
# Helper Functions
###############################################################################
def save_msg_to_cosmos(chat_id: str, user_email: str, user_query: str,  ai_response: str):
    try:
        # Get Cosmos Client
        client = CosmosClient.from_connection_string(conn_str=os.environ['COSMOS_CONNECTION_STRING'])
        
        # Get Cosmos DB
        database = client.get_database_client(os.environ['COSMOS_DB_NAME'])
        
        # Get Cosmos Container
        container = database.get_container_client(os.environ['COSMOS_CHAT_CONTAINER_NAME'])
        
        # Check if chat history exists
        try:
            # Get Chat History
            chat = container.read_item(
                item=chat_id,
                partition_key=user_email
            )
            
            # Append new msg to history
            chat['history'].append({
                'human': user_query,
                'ai': ai_response,
                'timestamp': datetime.now().isoformat()
            })
            
            # Update Chat History Cosmos Document
            container.replace_item(item=chat, body=chat)
        
        # If chat history does not exist
        except:
            # Create Chat History
            container.upsert_item(body={
                'id': chat_id,
                'UserId': user_email,
                'history': [{
                    'human': user_query,
                    'ai': ai_response,
                    'timestamp': datetime.now().isoformat()
                }]
            })
            
    except Exception as e:
        logging.error(f"Error Saving Chat for <{user_email}> to Cosmos: {e}")

###############################################################################
# Endpoints
###############################################################################

# Returns a user's chat history
@router.get("/all_chat_history", tags=["Chat History"])
def get_all_chat_history(email: str = Depends(jwt_dependency)):
    try:
        # Get Cosmos Client
        client = CosmosClient.from_connection_string(conn_str=os.environ['COSMOS_CONNECTION_STRING'])
        
        # Get Cosmos DB
        database = client.get_database_client(os.environ['COSMOS_DB_NAME'])
        
        # Get Cosmos Container
        container = database.get_container_client(os.environ['COSMOS_CHAT_CONTAINER_NAME'])
        
        # Get Chat History
        chat_history = container.query_items(
            query=f"SELECT * FROM c WHERE c.UserId = '{email}'",
            enable_cross_partition_query=True
        )
        
        # Return Chat History
        return {
            'status': 200,
            'chat_history': list(chat_history)
        }
    
    except Exception as e:
        return {
            'status': 400,
            'detail': f'Error Fetching Chat History. Error: {e}'
        }