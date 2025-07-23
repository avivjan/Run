import logging
import azure.functions as func
from azure.data.tables import TableClient
import os
import json
from shared.auth import require_auth
import uuid

@require_auth
def main(req: func.HttpRequest, signalrMessage: func.Out[str]) -> func.HttpResponse:
    try:
        user = getattr(req, 'user', {})
        requester_id = user.get('username')
        
        try:
            req_body = req.get_json()
            addressee_id = req_body.get('addressee_id')
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid request body"}),
                status_code=400,
                mimetype="application/json"
            )

        if not addressee_id:
            return func.HttpResponse(
                json.dumps({"error": "missing addressee_id"}),
                status_code=400,
                mimetype="application/json"
            )

        connection_string = os.getenv('AzureWebJobsStorage')
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name='Friendships'
        )

        friend_request = {
            'PartitionKey': 'Friendship',
            'RowKey': str(uuid.uuid4()),
            'requester_id': requester_id,
            'addressee_id': addressee_id,
            'status': 'pending'
        }

        table_client.create_entity(entity=friend_request)

        # Send a SignalR message to the addressee
        signalrMessage.set(json.dumps({
            'target': 'newFriendRequest',
            'arguments': [friend_request],
            'userId': addressee_id
        }))

        return func.HttpResponse(
            json.dumps({"message": "Friend request sent successfully."}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in sendFriendRequest: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 