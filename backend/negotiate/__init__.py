import azure.functions as func


def main(req: func.HttpRequest, connectionInfo) -> func.HttpResponse:
    # Real authentication is needed here. 
    # For now anyone can connect to our hub!
    return func.HttpResponse(connectionInfo)

