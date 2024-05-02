# Imports
from azure.storage.blob import BlobServiceClient
from fastapi import APIRouter, status, Depends, File, UploadFile, HTTPException
from dotenv import load_dotenv
import os
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from docx import Document
from io import BytesIO
from PyPDF2 import PdfReader


# In-App Dependencies
from dependencies import get_user_uuid, jwt_dependency
from routers.graphdb import (
    create_document_node,
    delete_document_node,
    create_content_node,
    generate_entities_from_llm,
    create_entity_node
)

# Load Environment Variables
load_dotenv('.env')

###############################################################################
# Initialize Router
###############################################################################
router = APIRouter()


###############################################################################
# Helper Functions
###############################################################################
# Extracts Text from .docx Files
def extract_text_from_docx(file_data):
    file_stream = BytesIO(file_data)
    doc = Document(file_stream)
    return "\n".join([para.text for para in doc.paragraphs])

# Extracts Text from .pdf Files
def extract_text_from_pdf(file_data):
    # init ret var
    text = ''
    
    # init file stream
    file_stream = BytesIO(file_data)
    
    # init pdf reader
    reader = PdfReader(file_stream)
    
    # Iterate through each page and concatenate its text
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:  # Check if text was extracted
            text += page_text + '\n'
    
    # Return pdf text
    return text

# Extracts Text from .txt Files
def extract_text_from_txt(file_data):
    return file_data.decode('utf-8')  # Assuming UTF-8 encoded text file

# Chunks and Embeds Text from Files and uploads to vector index store
# Stores chunks in Content Nodes and generates entities
def save_text_to_vector_index_and_content_nodes(text: str, file_name: str, index_name: str, user_email: str):
    
    # Use AzureOpenAIEmbeddings with an Azure account
    embeddings: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.environ['AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME'],
        openai_api_version=os.environ['AZURE_OPENAI_API_VERSION'],
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
        api_key=os.environ['AZURE_OPENAI_API_KEY'],
    )
    
    # Get Azure AI Search Vector Store Index Instance
    vector_store: AzureSearch = AzureSearch(
        azure_search_endpoint=os.environ['AZURE_SEARCH_SERVICE_ENDPOINT'],
        azure_search_key=os.environ['AZURE_SEARCH_ADMIN_KEY'],
        index_name=index_name,
        embedding_function=embeddings.embed_query,
    )
    
    # Load Recursive Text Splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=50,
        length_function=len,
        is_separator_regex=False,
    )
    
    # Get Documents from Text
    docs = text_splitter.create_documents([text])
    
    # Update Document Metadata
    updated_metadata = {
        "source": f'/{index_name}/{file_name}',
        "container": index_name,
        "file_name": file_name,
    }
    for i, doc in enumerate(docs, start=1):
        # Update Document Metadata
        doc.metadata = updated_metadata.copy()
        
        # Create Content Nodes
        create_content_node(
            user_email = user_email,
            file_name = file_name,
            container_name = index_name,
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
                container_name = index_name,
                chunk = i,
                entity = str(entity)
            )
    
    # Embed & Store Docs in Vector Store
    vector_store.add_documents(documents=docs)
    
    # Return Success
    return True

# Returns the n most similar documents to a given query
def search_vector_index(query: str, index_name: str, n: int = 3):
    
    # Use AzureOpenAIEmbeddings with an Azure account
    embeddings: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings(
        azure_deployment=os.environ['AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME'],
        openai_api_version=os.environ['AZURE_OPENAI_API_VERSION'],
        azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
        api_key=os.environ['AZURE_OPENAI_API_KEY'],
    )
    
    # Get Azure AI Search Vector Store Index Instance
    vector_store: AzureSearch = AzureSearch(
        azure_search_endpoint=os.environ['AZURE_SEARCH_SERVICE_ENDPOINT'],
        azure_search_key=os.environ['AZURE_SEARCH_ADMIN_KEY'],
        index_name=index_name,
        embedding_function=embeddings.embed_query,
    )
    
    # Perform a similarity search
    return vector_store.similarity_search(
        query=query,
        k=n,
        search_type="similarity",
    )

###############################################################################
# Endpoints
###############################################################################
@router.post('/upload_files', tags=['AI Search'])
async def upload_files(
    files: list[UploadFile] = File(...),
    user_email: str = Depends(jwt_dependency)
):  
    # Azure Blob Storage Connection Client
    blob_service_client = BlobServiceClient.from_connection_string(os.getenv('AZURE_BLOB_CONN_STR'))
    
    # Get Container Name
    user_continer_name = get_user_uuid(user_email)
    
    # Connect to Container Client
    container_client = blob_service_client.get_container_client(user_continer_name)
    
    # Allowed File Extension Types
    allowed_file_extensions = ['.docx', '.pdf', '.txt']
    
    # Upload Files
    for file in files:
        # Check File Type
        extension = os.path.splitext(file.filename)[1].lower()
        if extension not in allowed_file_extensions:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")
        
        # Read File Data
        file_data = await file.read()
        
        # extract text from file
        if extension == '.txt':
            file_text = extract_text_from_txt(file_data)
        elif extension == '.docx':
            file_text = extract_text_from_docx(file_data)
        elif extension == '.pdf':
            file_text = extract_text_from_pdf(file_data)
        
        # Create Neo4j Document Node
        doc_node_created = create_document_node(
            user_email = user_email,
            file_name = file.filename,
            container_name = user_continer_name
        )
        
        # Check if Document Node was Created
        if doc_node_created:
            try:
                # Save Text to Vector Index
                txt_saved_to_index = save_text_to_vector_index_and_content_nodes(
                    text = file_text,
                    file_name = file.filename,
                    index_name = user_continer_name,
                    user_email = user_email
                )
            except:
                delete_document_node(
                    user_email = user_email,
                    file_name = file.filename,
                    container_name = user_continer_name
                )
                raise HTTPException(status_code=500, detail='Failed to save text to vector index.')
        else:
            raise HTTPException(status_code=500, detail='Failed to create document node in graph database.')
        
        # Check if text was saved to index
        if txt_saved_to_index:
            # Try and Upload File to Azure Blob
            try:
                blob_client = container_client.get_blob_client(file.filename)
                blob_client.upload_blob(file_data, overwrite=True)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        else:
            if doc_node_created:
                delete_document_node(
                    user_email = user_email,
                    file_name = file.filename,
                    container_name = user_continer_name
                )
            raise HTTPException(status_code=500, detail='Failed to save text to vector index.')
    
    # Return Success
    return {'status_code': status.HTTP_200_OK, 'detail': 'Files Uploaded Successfully'}

