import logging
import azure.functions as func
from azure.data.tables import TableClient
import os
import json


def main(req: func.HttpRequest, signalrHub: func.Out[str]) -> func.HttpResponse:
    try:
        # Get userId from query string or request body
        user_id = req.params.get('userId')
        if not user_id:
            try:
                req_body = req.get_json()
                user_id = req_body.get('userId')
            except ValueError:
                pass

        if not user_id:
            return func.HttpResponse("Missing userId", status_code=400)

        # Connect to Azure Table Storage
        connection_string = os.getenv('AzureWebJobsStorage')
        table_client = TableClient.from_connection_string(
            conn_str=connection_string,
            table_name='Users'
        )

        # Retrieve user from table
        entity = table_client.get_entity(partition_key='User', row_key=user_id)

        # Remove metadata that isn't JSON serializable
        user_data = {k: v for k, v in entity.items() if k not in ['PartitionKey', 'RowKey', 'etag']}

        # Optionally include userId in response
        user_data['userId'] = entity['RowKey']

        return func.HttpResponse(
            json.dumps(user_data),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error in getUser: {e}")
        return func.HttpResponse("Something went wrong", status_code=500)
