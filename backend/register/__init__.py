import json
import logging
import os
import bcrypt
from datetime import datetime
import azure.functions as func
from azure.data.tables import TableServiceClient, UpdateMode
from azure.core.exceptions import ResourceExistsError

def get_table_client():
    connection_string = os.environ["AzureWebJobsStorage"]
    table_service_client = TableServiceClient.from_connection_string(connection_string)
    return table_service_client.get_table_client("Users")

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

    # Hash password
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)

    # Create user entity
    user = {
        "PartitionKey": "user",
        "RowKey": username,
        "passwordHash": password_hash.decode('utf-8'),
        "createdAt": datetime.utcnow().isoformat()
    }

    try:
        table_client = get_table_client()
        table_client.create_entity(entity=user, mode=UpdateMode.FAIL)
        
        return func.HttpResponse(
            json.dumps({"message": "User registered successfully"}),
            mimetype="application/json",
            status_code=201
        )
    except ResourceExistsError:
        return func.HttpResponse(
            json.dumps({"error": "Username already exists"}),
            mimetype="application/json",
            status_code=409
        )
    except Exception as e:
        logging.error(f"Error creating user: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json",
            status_code=500
        ) 