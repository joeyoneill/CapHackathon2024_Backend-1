# Imports
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
import os
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, AzureChatOpenAI
import logging

# In-App Dependencies
from dependencies import jwt_dependency
from routers.chat_history import save_msg_to_cosmos

# Load Environment Variables
load_dotenv('.env')

# Configure the root logger to log all messages
logging.basicConfig(level=logging.DEBUG)

###############################################################################
# Initialize Router
###############################################################################
router = APIRouter()

###############################################################################
# Websocket Connection
###############################################################################
# EXAMPLE REQUEST DATA DICT: 
# {
#   "query": "Hello, how are you?",
#   "chatId": "123",
#   "jwt": "<JWT token>",
#   "email": "test@test.com"
# }
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Initialize Needed Variables
    resp = ''
    premature_disconnect = True
    
    try:
        while True:
            # Receive data from the Frontend
            data = await websocket.receive_json()
            
            # Check if the request data contains proper keys
            if 'query' not in data:
                await websocket.send_text('<<E:NO_QUERY>>')
                break
            if 'chatId' not in data:
                await websocket.send_text('<<E:NO_CHAT_ID>>')
                break
            if 'jwt' not in data:
                await websocket.send_text('<<E:INVALID_JWT>>')
                break
            if 'email' not in data:
                await websocket.send_text('<<E:NO_EMAIL>>')
                break
            
            # Ensure the JWT is valid
            try:
                user_email = jwt_dependency(authorization=data['jwt'])
                if not user_email or user_email != data['email']:
                    await websocket.send_text('<<E:INVALID_JWT>>')
                    break
            except Exception as e:
                await websocket.send_text('<<E:INVALID_JWT>>')
                break
            
            # Initialize the LLM
            llm = AzureChatOpenAI(
                openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
                azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
                temperature=0.7
            )
            
            # Message Complete
            premature_disconnect = False
            
            # Stream the response
            for token in llm.stream(str(data['query'])):
                await websocket.send_text(token.content)
                resp += token.content
            
            # Send Successful Completion response to the Frontend
            await websocket.send_text('<<END>>')
    
    # WebSocket Disconnected
    except WebSocketDisconnect:
        logging.info("Websocket Disconnected")
        
        # Save QUERY & Response
        if not premature_disconnect and resp.strip() != '':
            save_msg_to_cosmos(
                chat_id=data['chatId'],
                user_email=user_email,
                user_query=data['query'],
                ai_response=resp
            )
    
    # Any other Error/Exception
    except Exception as e:
        logging.error(f"Error in WebSocket Connection: {e}")