# Imports
from fastapi import APIRouter, HTTPException, status
from langchain_openai import AzureChatOpenAI
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
                    "CREATE (c:Content {data: $content, chunk: $chunk}) "
                    "CREATE (d)-[:CONTAINS]->(c)"
                )
                tx.run(
                    query,
                    email=user_email,
                    name=file_name,
                    container=container_name,
                    chunk=chunk
                )
            
            # Execute Transaction with Session
            with driver.session() as session:
                session.execute_write(add_content)
                print(f"CONTENT node <'{user_email} -> {file_name} -> {chunk}'> created successfully.")
        
        # Return Success
        return True
    
    # Failure
    except:
        print(f"CONTENT node <'{user_email} -> {file_name} -> {chunk}'> creation failed.")
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
    prompt = f"The text you return to me will be DIRECTLY used in python code. PLEASE ONLY RETURN A COMMA SEPERATED STRING of themes, schemas, characters, figures, events, etc. THAT ARE CONTAINED in the following content. PLEASE ONLY CREATE 3-5 ITEMS IN THE LIST. INCLUDE THE ONLY THE ITEMS THAT SEEMS IMPORTANT. THESE ITEMS WILL BE USED DIRECTLY IN A KNOWLEDGE GRAPH as ENTITY nodes to EXPLAIN the content:\n```\n{content}\n```"
    
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
# TODO: ADD THE CREATE DOC & CREATE CONTENT FUNCTION TO FILE UPLOAD ROUTE
# TODO: DELETE -> FOR MAIN RUN TESTING ONLY
@router.get('/graphdb_display_test', tags=['GraphDB'])
def graphdb_display_test(user_email: str):
    # ensure it is lowercase
    user_email = user_email.lower()
    
    # Connect to DB Driver
    with GraphDatabase.driver(os.environ['NEO4J_URI'], auth=neo4j_auth) as driver:
        
        # def get_nodes(tx):
        #     query = (
        #         "MATCH (u:User {email: $email})-[:OWNS]->(d:Document)"
        #         "OPTIONAL MATCH (d)-[*]->(c)"
        #         "RETURN d as document, collect(c) as children"
        #     )
        #     tx.run(query, email=user_email)
        
        # with driver.session() as session:
        #     result = session.read_transaction(get_nodes)
        #     return [{"document": record["document"]._properties, "children": [node._properties for node in record["children"]]} for record in result]
        
        with driver.session() as session:
            result = session.run("""
                MATCH (u:User {email: $email})-[:OWNS]->(d:Document)
                OPTIONAL MATCH (d)-[*]->(c)
                RETURN d as document, collect(c) as children
                """,
                email=user_email
            )
            return [
                {
                    "document": record["document"]._properties,
                    "children": [node._properties for node in record["children"]]
                } for record in result
            ]


@router.get('/graphdb_test', tags=['GraphDB'])
def graphdb_test(user_email: str):
    
    content = """President Biden's State of the Union Address
(The President presents his prepared remarks to Speaker Johnson.) Your bedtime reading.

Tony! Thank you. Looking for Jill.

Good evening. Good evening. If I were smart, I'd go home now.

Mr. Speaker, Madam Vice President, members of Congress, my fellow Americans.

In January 1941, Franklin Roosevelt came to this chamber to speak to the nation. And he said, “I address you at a moment unprecedented in the history of the Union”. Hitler was on the march. War was raging in Europe.

President Roosevelt's purpose was to wake up Congress and alert the American people that this was no ordinary time. Freedom and democracy were under assault in the world.

Tonight, I come to the same chamber to address the nation. Now it's we who face an unprecedented moment in the history of the Union.

And, yes, my purpose tonight is to wake up the Congress and alert the American people that this is no ordinary moment either. Not since President Lincoln and the Civil War have freedom and democracy been under assault at home as they are today.

What makes our moment rare is that freedom and democracy are under attack at — both at home and overseas at the very same time.

Overseas, Putin of Russia is on the march, invading Ukraine and sowing chaos throughout Europe and beyond.

If anybody in this room thinks Putin will stop at Ukraine, I assure you: He will not.

But Ukraine — Ukraine can stop Putin. Ukraine can stop Putin if we stand with Ukraine and provide the weapons that it needs to defend itself.

That is all — that is all Ukraine is asking. They're not asking for American soldiers. In fact, there are no American soldiers at war in Ukraine, and I'm determined to keep it that way.

But now assistance to Ukraine is being blocked by those who want to walk away from our world leadership.

It wasn't long ago when a Republican president named Ronald Reagan thundered, “Mr. Gorbachev, tear down this wall.”

Now — now my predecessor, a former Republican president, tells Putin, quote, “Do whatever the hell you want.”

That's a quote.

A former president actually said that — bowing down to a Russian leader. I think it's outrageous, it's dangerous, and it's unacceptable.

America is a founding member of NATO, the military alliance of democratic nations created after World War Two prevent — to prevent war and keep the peace.

And today, we've made NATO stronger than ever. We welcomed Finland to the Alliance last year. And just this morning, Sweden officially joined, and their minister is here tonight. Stand up. Welcome. Welcome, welcome, welcome. And they know how to fight.

Mr. Prime Minister, welcome to NATO, the strongest military alliance the world has ever seen.

I say this to Congress: We have to stand up to Putin. Send me a bipartisan national security bill. History is literally watching. History is watching.

If the United States walks away, it will put Ukraine
at risk. Europe is at risk. The free world will be at risk, emboldening others to do what they wish to do us harm.

My message to President Putin, who I've known for a long time, is simple: We will not walk away. We will not bow down. I will not bow down.
"""
    
    return generate_entities_from_llm(content)