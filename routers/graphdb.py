# Imports
from fastapi import APIRouter, HTTPException
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

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

# Creates a User's DB in Neo4J Instance
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

# Deletes a User's DB in Neo4J Instance
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

# Creates a Document's DB in Neo4J Instance
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
    
# Creates a Document's DB in Neo4J Instance
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
#
###############################################################################

# TODO: ADD THE CREATE DOC FUNCTION TO FILE UPLOAD ROUTE
# TODO: DELETE -> FOR MAIN RUN TESTING ONLY
@router.get('/graphdb_test', tags=['General'])
def graphdb_test():
    
    create_document_node(
        user_email = 'test@test.com',
        file_name = '2024_State_of_the_union.txt',
        container_name = '06b89462719a440997659e66d59792c1'
    )
    
    return {'message': 'Success!.'}