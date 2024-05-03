# Imports
from fastapi import APIRouter, HTTPException, status, Depends
from langchain_openai import AzureChatOpenAI
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

from pydantic import BaseModel

# In-App Dependencies
from dependencies import jwt_dependency, get_user_uuid

# Load Environment Variables
load_dotenv('.env')

# Create Neo4j Auth Tuple
neo4j_auth = (os.environ['NEO4J_USERNAME'], os.environ['NEO4J_PASSWORD'])

###############################################################################
# Initialize Router
###############################################################################
router = APIRouter()

###############################################################################
# User Node Helper Functions
###############################################################################

# Creates a User Node in Neo4J Instance
def create_user_node(user_email: str):
    # ensure it is lowercase
    user_email = user_email.lower()
    
    try:
        # Connect to DB Driver
        with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=neo4j_auth) as driver:
            
            # Create User's Database in Neo4j Instance
            def add_user(tx):
                tx.run("CREATE (u:User {email: $email})", email=user_email)
            
            # Execute Transaction with Session
            with driver.session() as session:
                session.execute_write(add_user)
                print(f"USER node <'{user_email}'> created successfully.")
        
        return True
    except:
        return False

# Deletes a User Node in Neo4J Instance
def delete_user_node(user_email: str):
    # ensure it is lowercase
    user_email = user_email.lower()
    
    try:
        # Connect to DB Driver
        with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=neo4j_auth) as driver:
            
            # Delete User's Database in Neo4j Instance
            def delete_user(tx):
                tx.run("MATCH (u:User {email: $email}) DETACH DELETE u", email=user_email)
            
            # Execute Transaction with Session
            with driver.session() as session:
                session.execute_write(delete_user)
                print(f"USER node <'{user_email}'> deleted successfully.")
        
        return True
    except:
        return False

###############################################################################
# Document Node Helper Functions
###############################################################################

# Creates a Document Node in Neo4J Instance
def create_document_node(user_email: str, file_name: str, container_name: str):
    # ensure it is lowercase
    user_email = user_email.lower()
    
    try:
        # Connect to DB Driver
        with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=neo4j_auth) as driver:
            
            # Create Document's Database in Neo4j Instance
            def add_document(tx):
                query = (
                    "MATCH (u:User {email: $email}) "
                    "CREATE (d:Document {name: $name, container: $container}) "
                    "CREATE (u)-[:OWNS]->(d)"
                )
                tx.run(query, email=user_email, name=file_name, container=container_name)
            
            # Execute Transaction with Session
            with driver.session() as session:
                session.execute_write(add_document)
                print(f"DOCUMENT node <'{user_email} -> {file_name}'> created successfully.")
        
        # Return Success
        return True
    
    # Failure
    except:
        print(f"DOCUMENT node <'{user_email} -> {file_name}'> creation failed.")
        return False
    
# Creates a Document Node in Neo4J Instance
def delete_document_node(user_email: str, file_name: str, container_name: str):
    # ensure it is lowercase
    user_email = user_email.lower()
    
    try:
        # Connect to DB Driver
        with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=neo4j_auth) as driver:
            
            # Create Document's Database in Neo4j Instance
            def delete_document(tx):
                query = (
                    "MATCH (u:User {email: $email})-[:OWNS]->(d:Document {name: $name, container: $container})"
                    "OPTIONAL MATCH (d)-[*0..]->(connected)"
                    "DETACH DELETE d, connected"
                )
                tx.run(query, email=user_email, name=file_name, container=container_name)
            
            # Execute Transaction with Session
            with driver.session() as session:
                session.execute_write(delete_document)
                print(f"DOCUMENT node and all connected entities <'{user_email} -> {file_name}'> deleted successfully.")
        
        # Return Success
        return True
    
    # Failure
    except:
        print(f"DOCUMENT node <'{user_email} -> {file_name}'> creation failed.")
        return False

###############################################################################
# Content Node Helper Functions
###############################################################################

# Creates a Content Node in Neo4J Instance
def create_content_node(user_email: str, file_name: str, container_name: str, content: str, chunk: int):
    # ensure it is lowercase
    user_email = user_email.lower()
    
    try:
        # Connect to DB Driver
        with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=neo4j_auth) as driver:
            
            # Cypher to Create Content in Neo4j Instance
            def add_content(tx):
                query = (
                    "MATCH (u:User {email: $email})-[:OWNS]->(d:Document {name: $name, container: $container})"
                    "CREATE (c:Content {chunk: $chunk, data: $content}) "
                    "CREATE (d)-[:CONTAINS]->(c)"
                )
                tx.run(
                    query,
                    email=user_email,
                    name=file_name,
                    container=container_name,
                    chunk=chunk,
                    content=content
                )
            
            # Execute Transaction with Session
            with driver.session() as session:
                session.execute_write(add_content)
                print(f"CONTENT node <'{user_email} -> {file_name} -> {chunk}'> created successfully.")
        
        # Return Success
        return True
    
    # Failure
    except Exception as e:
        print(f"CONTENT node <'{user_email} -> {file_name} -> {chunk}'> creation failed.  Exception: {e}")
        return False

###############################################################################
# Entity Node Helper Functions
###############################################################################

# Creates an Entity Node in Neo4J Instance
def create_entity_node(user_email: str, file_name: str, container_name: str, chunk: int, entity: str):
    # ensure it is lowercase
    user_email = user_email.lower()
    
    try:
        # Connect to DB Driver
        with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=neo4j_auth) as driver:
            
            # Cypher to Create Content in Neo4j Instance
            def add_entity(tx):
                query = (
                    "MATCH (u:User {email: $email})-[:OWNS]->(d:Document {name: $name, container: $container})-[:CONTAINS]->(c:Content {chunk: $chunk})"
                    "CREATE (e:Entity {name: $entity}) "
                    "CREATE (c)-[:MENTIONS]->(e)"
                )
                tx.run(
                    query,
                    email=user_email,
                    name=file_name,
                    container=container_name,
                    chunk=chunk,
                    entity=entity
                )
            
            # Execute Transaction with Session
            with driver.session() as session:
                session.execute_write(add_entity)
                print(f"ENTITY node <'{user_email} -> {file_name} -> {chunk} -> {entity}'> created successfully.")
        
        # Return Success
        return True
    
    # Return Failure
    except:
        print(f"ENTITY node <'{user_email} -> {file_name} -> {chunk} -> {entity}'> creation failed.")
        return False
    
###############################################################################
# LLM Interaction 
###############################################################################

# Uses LLM to return a list of entities from a given content
def generate_entities_from_llm(content: str):
    
    # Initialize the LLM
    llm = AzureChatOpenAI(
        openai_api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"],
        temperature=0.7
    )
    
    # Create the Prompt
    prompt = f"The text you return to me will be DIRECTLY used in python code. PLEASE ONLY RETURN A COMMA SEPARATED STRING of themes, schemas, characters, figures, events, etc. THAT ARE CONTAINED in the following content. Please ONLY generate me between two and five entities in the comma separated string. Make sure the entities are the MOST important items based on the content. THESE ITEMS WILL BE USED DIRECTLY IN A KNOWLEDGE GRAPH as ENTITY nodes to EXPLAIN the content:\n```\n{content}\n```"
    
    # Call the LLM for response
    response = llm.invoke([prompt])
    
    # Print csl entities
    entities = []
    for entity in response.content.split(','):
        entities.append(entity.strip())
    
    # Return the response
    return entities

###############################################################################
# Endpoints
###############################################################################
# Request Object for document graph
class DocumentGraphRequest(BaseModel):
    file_name: str

# Returns Document Node and its descendants for frontend display
@router.post("/document_graph", tags=["GraphDB"])
def document_graph(request: DocumentGraphRequest, user_email: str = Depends(jwt_dependency)):
    try:
        # Connect to DB Driver
        with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=neo4j_auth) as driver:
            with driver.session() as session:
                query = (
                    "MATCH (user:User {email: $email})-[:OWNS]->(d:Document {name: $file_name})"
                    "MATCH path = (d)-[*]->(descendant)"
                    "RETURN nodes(path) AS Nodes, relationships(path) AS Relationships"
                )
                result = session.run(query, email=user_email, file_name=request.file_name)
                nodes = []
                links = []
                seen_nodes = set()
                
                for record in result:
                    for node in record["Nodes"]:
                        if node.id not in seen_nodes:
                            nodes.append({"id": node.id, **node._properties})
                            seen_nodes.add(node.id)
                    for rel in record["Relationships"]:
                        links.append({"source": rel.start_node.id, "target": rel.end_node.id})

                return {"nodes": nodes, "links": links}
        
    except Exception as e:
        print(f"Failed to retrieve document graph: {e}")
        return {
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'detail': f"Failed to retrieve document graph: {e}"
        }