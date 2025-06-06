import os
import jwt
from functools import wraps
import azure.functions as func
import json

def get_token_from_header(req: func.HttpRequest) -> str:
    """Extract the token from the Authorization header"""
    auth_header = req.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ')[1]

def verify_token(token: str) -> dict:
    """Verify and decode the JWT token"""
    try:
        jwt_secret = os.environ["JWT_SECRET"]
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")

def require_auth(f):
    """Decorator to require authentication for a function"""
    @wraps(f)
    def decorated(req: func.HttpRequest, *args, **kwargs):
        token = get_token_from_header(req)
        if not token:
            return func.HttpResponse(
                json.dumps({"error": "No authorization token provided"}),
                mimetype="application/json",
                status_code=401
            )

        try:
            payload = verify_token(token)
            # Add user info to the request context
            setattr(req, 'user', payload)
            return f(req, *args, **kwargs)
        except Exception as e:
            return func.HttpResponse(
                json.dumps({"error": str(e)}),
                mimetype="application/json",
                status_code=401
            )
    
    return decorated 