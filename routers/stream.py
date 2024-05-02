# Imports
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
import os
from langchain_openai import AzureChatOpenAI
import logging

# In-App Dependencies
from dependencies import jwt_dependency, get_user_uuid
from routers.chat_history import save_msg_to_cosmos
from routers.ai_search import search_vector_index
from routers.chat_history import get_chat_history_by_id

# Load Environment Variables
load_dotenv('.env')

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
                if not user_email or user_email.lower() != data['email'].lower():
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
            
            # Get Chat History using data["chatId"]
            chat_history_list = get_chat_history_by_id(
                chat_id=data["chatId"],
                user_email=user_email.lower()
            )
            chat_history_str = ''
            if chat_history_list:
                for obj in chat_history_list:
                    chat_history_str += f'Human: {obj.get("human")}\nai: {obj.get("ai")}\n'
            
            # Get Container/Index name
            index_name = get_user_uuid(user_email.lower())
            
            # Get Context from AI Search
            similar_docs = search_vector_index(
                query=data['query'],
                index_name=index_name
            )
            
            # Create Context String
            context_str = ''
            if similar_docs:
                for doc in similar_docs:
                    context_str += f'File name: {str(doc.metadata["file_name"])}\nContent:\n```{doc.page_content}```\n'
            
            # CREATE PROMPT FOR LLM STREAM
            prompt = f'You are "Capgemin.AI", a helpful, friendly chatbot. You are here to help the user with any questions they may have. You are knowledgeable and can provide information on a wide range of topics. You are patient and understanding. You are here to help the user and make their experience as positive as possible. Use the chat history and context to help answer questions, if applicable - but do not rely soley on them. Do not mention anything about the context to the user, just use the information it provides if it is relevant to answering the query.\n====\nContext:\n====\n{context_str}\n====\nChat History:\n====\n{chat_history_str}\n====\nCurrent Human Query:\n{str(data["query"])}\n====\nai: '
            
            # print(prompt)
            
            # Message Complete
            premature_disconnect = False
            
            # Stream the response
            for token in llm.stream(prompt):
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