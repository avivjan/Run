import json
import logging
import os
import jwt
from datetime import datetime
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing token validation request')

    # Get the Authorization header
    auth_header = req.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return func.HttpResponse(
            json.dumps({"error": "Missing or invalid Authorization header"}),
            mimetype="application/json",
            status_code=401
        )

    # Extract the token
    token = auth_header.split(' ')[1]
    
    try:
        # Get the JWT secret from environment variables
        jwt_secret = os.environ["JWT_SECRET"]
        
        # Decode and verify the token
        decoded_token = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"]
        )
        
        # Check if token is expired
        exp = decoded_token.get('exp')
        if exp and datetime.utcnow().timestamp() > exp:
            return func.HttpResponse(
                json.dumps({"error": "Token has expired"}),
                mimetype="application/json",
                status_code=401
            )

        # Token is valid, return the decoded information
        return func.HttpResponse(
            json.dumps({
                "message": "Token is valid",
                "username": decoded_token.get('username'),
                "expires_at": datetime.fromtimestamp(exp).isoformat() if exp else None
            }),
            mimetype="application/json",
            status_code=200
        )

    except jwt.ExpiredSignatureError:
        return func.HttpResponse(
            json.dumps({"error": "Token has expired"}),
            mimetype="application/json",
            status_code=401
        )
    except jwt.InvalidTokenError as e:
        logging.error(f"Invalid token: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Invalid token"}),
            mimetype="application/json",
            status_code=401
        )
    except Exception as e:
        logging.error(f"Error validating token: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            mimetype="application/json",
            status_code=500
        )