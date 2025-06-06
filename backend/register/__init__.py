import json
import logging
import os
import bcrypt
from datetime import datetime
import azure.functions as func
from azure.data.tables import TableServiceClient, UpdateMode
from azure.core.exceptions import ResourceExistsError

def get_table_client():
    try:
        connection_string = os.environ["AzureWebJobsStorage"]
        logging.info("Initializing table service client...")
        table_service_client = TableServiceClient.from_connection_string(connection_string)
        
        # Ensure the table exists
        table_name = "Users"
        try:
            table_service_client.create_table_if_not_exists(table_name)
            logging.info(f"Table '{table_name}' is ready")
        except Exception as table_error:
            logging.error(f"Error ensuring table exists: {str(table_error)}")
            raise
            
        return table_service_client.get_table_client(table_name)
    except KeyError:
        logging.error("Missing AzureWebJobsStorage connection string in environment variables")
        raise
    except Exception as e:
        logging.error(f"Error initializing table client: {str(e)}")
        raise

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing register request')

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid request body"}),
            mimetype="application/json",
            status_code=400
        )

    # Validate input
    username = req_body.get('username')
    password = req_body.get('password')

    if not username or not password:
        return func.HttpResponse(
            json.dumps({"error": "Username and password are required"}),
            mimetype="application/json",
            status_code=400
        )

    if len(password) < 8:
        return func.HttpResponse(
            json.dumps({"error": "Password must be at least 8 characters long"}),
            mimetype="application/json",
            status_code=400
        )

    try:
        # Hash password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)

        # Create user entity with all required fields
        timestamp = datetime.utcnow().isoformat()
        user = {
            "PartitionKey": "User",
            "RowKey": username,
            "passwordHash": password_hash.decode('utf-8'),
            "createdAt": timestamp,
            "FirstName": "",  # Required by schema but can be empty initially
            "LastName": "",   # Required by schema but can be empty initially
            "Role": "Runner", # Default role
            "Timestamp": timestamp
        }

        # Log the entity we're trying to create (excluding sensitive data)
        safe_log_entity = {k:v for k,v in user.items() if k != 'passwordHash'}
        logging.info(f"Attempting to create user entity: {json.dumps(safe_log_entity)}")
        
        # Get table client and create entity
        table_client = get_table_client()
        logging.info("Got table client, attempting to create entity...")
        
        result = table_client.create_entity(entity=user)
        logging.info("Entity created successfully")
        
        return func.HttpResponse(
            json.dumps({"message": "User registered successfully"}),
            mimetype="application/json",
            status_code=201
        )
    except ResourceExistsError:
        logging.warning(f"Registration failed: Username '{username}' already exists")
        return func.HttpResponse(
            json.dumps({"error": "Username already exists"}),
            mimetype="application/json",
            status_code=409
        )
    except Exception as e:
        logging.error(f"Error creating user: {str(e)}")
        logging.error(f"User entity data: {json.dumps({k:str(v) for k,v in user.items() if k != 'passwordHash'})}")
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error", 
                "details": str(e),
                "type": type(e).__name__
            }),
            mimetype="application/json",
            status_code=500
        ) 