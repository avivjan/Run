import logging
import azure.functions as func
from azure.data.tables import TableClient, TableServiceClient
import os
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Get userId from query parameters
        user_id = req.params.get('userId')
        if not user_id:
            return func.HttpResponse(
                "Please pass a userId on the query string",
                status_code=400
            )

        # Initialize TableServiceClient and TableClient
        connection_string = os.environ["AzureWebJobsStorage"]
        table_service_client = TableServiceClient.from_connection_string(connection_string)
        table_name = "Activities"

        # Create table if it doesn't exist
        try:
            table_client = table_service_client.create_table_if_not_exists(table_name)
            logging.info(f"Table {table_name} exists or was created successfully")
        except Exception as e:
            logging.error(f"Error creating table: {str(e)}")
            return func.HttpResponse(
                f"Error creating table: {str(e)}",
                status_code=500
            )

        # Get table client for querying
        table_client = table_service_client.get_table_client(table_name)

        # Query activities for the user
        query_filter = f"PartitionKey eq '{user_id}'"
        logging.info(f"Querying with filter: {query_filter}")
        
        activities = table_client.query_entities(
            query_filter=query_filter
        )

        # Format the response
        activities_list = []
        for activity in activities:
            activities_list.append({
                'id': activity['RowKey'],
                'date': activity['timestamp'],
                'distance': float(activity['distance']),
                'duration': int(activity['duration']),
                'averagePace': float(activity['averagePace']) if 'averagePace' in activity else None,
                'averageSpeed': float(activity['averageSpeed']) if 'averageSpeed' in activity else None,
                'calories': float(activity['calories']) if 'calories' in activity else None,
                'trackId': activity['trackId'],
                'startTime': activity['start_time'],
                'stopTime': activity['stop_time'],
                'eventId': activity['eventId'] if 'eventId' in activity else None,
                'type': activity['type'] if 'type' in activity else 'Free Run'
            })

        logging.info(f"Found {len(activities_list)} activities for user {user_id}")
        return func.HttpResponse(
            json.dumps(activities_list),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error fetching user activities: {str(e)}")
        return func.HttpResponse(
            f"Error fetching user activities: {str(e)}",
            status_code=500
        )