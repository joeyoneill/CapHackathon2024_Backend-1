# Imports
from celery import Celery
import os
from dotenv import load_dotenv
import logging
from celery.utils.log import get_task_logger
from langchain_text_splitters import RecursiveCharacterTextSplitter

from routers.graphdb import create_content_node, generate_entities_from_llm, create_entity_node

# set up logger
logger = get_task_logger(__name__)

# Load environment variables
load_dotenv('.env')

# Create Celery App
celery = Celery(
    'worker',
    broker = os.environ['REDIS_URL'],
    # backend= os.environ['REDIS_URL']
)

# Tasks
@celery.task
def example_task(x, y):
    return x + y

@celery.task
def process_documents_into_neo4j(text: str, user_email: str, file_name: str, container_name: str):
    
    try:
        # Load Recursive Text Splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=50,
            length_function=len,
            is_separator_regex=False,
        )
        
        # Get Documents from Text
        docs = text_splitter.create_documents([text])
        
        # iterate through each document
        for i, doc in enumerate(docs):

            # Create Content Nodes
            create_content_node(
                user_email = user_email,
                file_name = file_name,
                container_name = container_name,
                content = doc.page_content.strip(),
                chunk = i
            )

            # Get entity list
            entity_list = generate_entities_from_llm(doc.page_content.strip())

            # Create Entity Nodes
            for entity in entity_list:
                create_entity_node(
                    user_email = user_email,
                    file_name = file_name,
                    container_name = container_name,
                    chunk = i,
                    entity = str(entity).strip()
                )
        
        # Return Success
        return True
    except:
        # Return Failure
        return False