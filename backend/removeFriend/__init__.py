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
        friend_user_id = req.route_params.get('friend_user_id')

        connection_string = os.getenv('AzureWebJobsStorage')
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name='Friendships'
        )

        query_filter = f"((requester_id eq '{user_id}' and addressee_id eq '{friend_user_id}') or (requester_id eq '{friend_user_id}' and addressee_id eq '{user_id}')) and status eq 'accepted'"
        entities = table_client.query_entities(query_filter)

        entity_to_delete = next(entities, None)

        if not entity_to_delete:
            return func.HttpResponse(
                json.dumps({"error": "Friendship not found"}),
                status_code=404,
                mimetype="application/json"
            )

        table_client.delete_entity(partition_key=entity_to_delete['PartitionKey'], row_key=entity_to_delete['RowKey'])

        return func.HttpResponse(
            json.dumps({"message": "Friend removed successfully"}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in removeFriend: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 