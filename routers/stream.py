# Imports
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
import os
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, AzureChatOpenAI
import logging

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
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive data from the Frontend
            data = await websocket.receive_json()
            
            # Check if the request data contains a query
            if 'query' not in data:
                await websocket.send_text('<<E:NO_QUERY>>')
            
            # Initialize the LLM
            llm = AzureChatOpenAI(
                openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
                azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
                temperature=0.7
            )
            
            # Stream the response
            # TODO: Save QUERY & Response
            resp = ''
            for token in llm.stream(str(data['query'])):
                await websocket.send_text(token.content)
                resp += token.content
            
            # Send Successful Completion response to the Frontend
            await websocket.send_text('<<END>>')
    
    # WebSocket Disconnected
    except WebSocketDisconnect:
        logging.info("Websocket Disconnected")
    
    # Any other Error/Exception
    except Exception as e:
        logging.error(f"Error in WebSocket Connection: {e}")