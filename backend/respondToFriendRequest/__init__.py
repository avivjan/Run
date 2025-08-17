import logging
import azure.functions as func
from azure.data.tables import TableClient
import os
import json
from shared.auth import require_auth

@require_auth
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        user = getattr(req, 'user', {})
        user_id = user.get('username')
        request_id = req.route_params.get('request_id')

        try:
            req_body = req.get_json()
            new_status = req_body.get('status')
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid request body"}),
                status_code=400,
                mimetype="application/json"
            )

        if not new_status or new_status not in ['accepted', 'declined']:
            return func.HttpResponse(
                json.dumps({"error": "Invalid status"}),
                status_code=400,
                mimetype="application/json"
            )

        connection_string = os.getenv('AzureWebJobsStorage')
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name='Friendships'
        )

        entity = table_client.get_entity(partition_key='Friendship', row_key=request_id)

        if entity['addressee_id'] != user_id:
            return func.HttpResponse(
                json.dumps({"error": "You are not authorized to respond to this request"}),
                status_code=403,
                mimetype="application/json"
            )

        entity['status'] = new_status
        table_client.update_entity(entity)

        return func.HttpResponse(
            json.dumps({"message": f"Friend request {new_status}"}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in respondToFriendRequest: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 