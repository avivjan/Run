import json
import logging
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
import azure.functions as func
from azure.data.tables import TableServiceClient

def get_table_client():
    connection_string = os.environ["AzureWebJobsStorage"]
    table_service_client = TableServiceClient.from_connection_string(connection_string)
    return table_service_client.get_table_client("Users")

def generate_token(username: str) -> str:
    jwt_secret = os.environ["JWT_SECRET"]
    expiration = datetime.utcnow() + timedelta(days=7)  # Token expires in 7 days
    
    token_payload = {
        "username": username,
        "exp": expiration,
        "iat": datetime.utcnow()
    }
    
    return jwt.encode(token_payload, jwt_secret, algorithm="HS256")

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing login request')

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

    try:
        # Get user from table
        table_client = get_table_client()
        user = table_client.get_entity(partition_key="user", row_key=username)

        # Verify password
        is_valid = bcrypt.checkpw(
            password.encode('utf-8'),
            user['passwordHash'].encode('utf-8')
        )

        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": "Invalid credentials"}),
                mimetype="application/json",
                status_code=401
            )

        # Generate JWT token
        token = generate_token(username)

        return func.HttpResponse(
            json.dumps({
                "message": "Login successful",
                "token": token,
                "username": username
            }),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error during login: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid credentials"}),
            mimetype="application/json",
            status_code=401
        ) 