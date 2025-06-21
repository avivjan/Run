import logging
import json
import os
from datetime import datetime

import azure.functions as func
from azure.data.tables import TableClient, UpdateMode
from azure.core.exceptions import ResourceNotFoundError
from shared.auth import require_auth

EVENTS_TABLE = "Events"
READY_USERS_TABLE = "ReadyUsers"
RUNNERS_TABLE = "RunnersInEvent"

@require_auth
def main(req: func.HttpRequest, signalrMessages: func.Out[str]) -> func.HttpResponse:
    try:
        body = req.get_json()
        event_id = body.get("eventId")
        user_id = body.get("userId")

        if not event_id or not user_id:
            return func.HttpResponse(
                json.dumps({"error": "missing eventId or userId"}),
                status_code=400,
                mimetype="application/json"
            )

        conn = os.getenv("AzureWebJobsStorage")
        if not conn:
            raise ValueError("AzureWebJobsStorage connection string not found")

        # Check if event exists and is in ready state
        events_tbl = TableClient.from_connection_string(conn, EVENTS_TABLE)
        try:
            event = events_tbl.get_entity("Event", event_id)
            if event['status'] != 'ready':
                return func.HttpResponse(
                    json.dumps({"error": "event is not in ready state"}),
                    status_code=409,
                    mimetype="application/json"
                )
        except ResourceNotFoundError:
            return func.HttpResponse(
                json.dumps({"error": f"event {event_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Verify the user is the host
        if event['trainerId'] != user_id:
            return func.HttpResponse(
                json.dumps({"error": "only the host can start the event"}),
                status_code=403,
                mimetype="application/json"
            )

        # Get ready users for this event
        ready_users_tbl = TableClient.from_connection_string(conn, READY_USERS_TABLE)
        ready_filter = f"PartitionKey eq '{event_id}'"
        ready_users = list(ready_users_tbl.query_entities(ready_filter))
        ready_user_ids = [user['RowKey'] for user in ready_users]
        
        # Automatically include the host in the ready users list
        if user_id not in ready_user_ids:
            ready_user_ids.append(user_id)

        # Get all registered users for this event
        runners_tbl = TableClient.from_connection_string(conn, RUNNERS_TABLE)
        runners_filter = f"PartitionKey eq '{event_id}'"
        registered_users = list(runners_tbl.query_entities(runners_filter))
        registered_user_ids = [user['RowKey'] for user in registered_users]

        # Remove users who are not ready
        users_to_remove = []
        for registered_user_id in registered_user_ids:
            if registered_user_id not in ready_user_ids:
                try:
                    runners_tbl.delete_entity(partition_key=event_id, row_key=registered_user_id)
                    users_to_remove.append(registered_user_id)
                    logging.info(f"Removed user {registered_user_id} from event {event_id} - not ready")
                except ResourceNotFoundError:
                    logging.warning(f"User {registered_user_id} was not found in event {event_id}")
                except Exception as e:
                    logging.error(f"Error removing user {registered_user_id} from event {event_id}: {e}")

        # Update event status to started
        # event['status'] = 'started'
        event['startedAt'] = datetime.utcnow().isoformat()
        events_tbl.update_entity(entity=event, mode=UpdateMode.REPLACE)

        # Prepare SignalR message
        signalr_message = {
            'target': 'eventStarted',
            'arguments': [{
                'eventId': event_id,
                'status': 'started',
                'startedAt': event['startedAt'],
                'readyUsers': ready_user_ids,
                'trackId': event.get('trackId'),
                'removedUsers': users_to_remove
            }]
        }
        
        logging.info(f"Sending SignalR message: {json.dumps(signalr_message)}")
        
        # Send SignalR message to notify all participants
        signalrMessages.set(json.dumps(signalr_message))

        return func.HttpResponse(
            json.dumps({
                "message": "event started",
                "eventId": event_id,
                "status": "started",
                "startedAt": event['startedAt'],
                "readyUsers": ready_user_ids,
                "removedUsers": users_to_remove
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"StartEvent error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "something went wrong", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        ) 