# Run Backend API

A comprehensive Azure Functions backend API for the Run application, providing authentication, run tracking, social features, and AI coaching capabilities.

Main Run app - https://github.com/Eranshh/Run
Companion watch app - https://github.com/Tomer-Zur/Run-wearOS

## Overview

This backend is built using Azure Functions with Python, providing a serverless API for the Run mobile and WearOS applications. It includes user management, run tracking, social features, and AI-powered coaching.

## Base URL

```
https://runfuncionapp.azurewebsites.net/api
```

## Authentication

Most endpoints require JWT token authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## API Endpoints

### Authentication

#### Register User
- **POST** `/register`
- **Description**: Create a new user account
- **Auth Required**: No
- **Request Body**:
```json
{
  "username": "string",
  "password": "string (min 8 characters)"
}
```
- **Response**:
```json
{
  "message": "User registered successfully"
}
```

#### Login
- **POST** `/login`
- **Description**: Authenticate user and receive JWT token
- **Auth Required**: No
- **Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```
- **Response**:
```json
{
  "token": "jwt_token_string",
  "user": {
    "user_id": "string",
    "username": "string"
  }
}
```

#### Validate Token
- **GET** `/validate-token`
- **Description**: Verify if a JWT token is valid
- **Auth Required**: Yes (Bearer token)
- **Response**:
```json
{
  "valid": true,
  "user": {
    "user_id": "string",
    "username": "string"
  }
}
```

### User Management

#### Get User
- **GET** `/getUser`
- **Description**: Get user profile information
- **Auth Required**: Yes
- **Query Parameters**: `user_id` (optional, defaults to authenticated user)
- **Response**:
```json
{
  "user_id": "string",
  "username": "string",
  "created_at": "datetime"
}
```

#### Search Users
- **GET** `/users`
- **Description**: Search for users by username
- **Auth Required**: Yes
- **Query Parameters**: `search` (username search term)
- **Response**:
```json
[
  {
    "user_id": "string",
    "username": "string"
  }
]
```

### Run Tracking

#### Create Activity
- **POST** `/createActivity`
- **Description**: Log a completed run/activity
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "distance": "number (km)",
  "duration": "number (seconds)",
  "calories": "number",
  "pace": "number (min/km)",
  "elevation": "number (meters)",
  "track": [
    {
      "latitude": "number",
      "longitude": "number",
      "timestamp": "datetime"
    }
  ]
}
```
- **Response**:
```json
{
  "activity_id": "string",
  "message": "Activity created successfully"
}
```

#### Get User Activities
- **GET** `/getUsersActivities`
- **Description**: Get user's run history
- **Auth Required**: Yes
- **Query Parameters**: `user_id` (optional, defaults to authenticated user)
- **Response**:
```json
[
  {
    "activity_id": "string",
    "distance": "number",
    "duration": "number",
    "calories": "number",
    "pace": "number",
    "elevation": "number",
    "created_at": "datetime",
    "track": "array of coordinates"
  }
]
```

### Track Management

#### Create Track
- **POST** `/createTrack`
- **Description**: Create a new running track
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "name": "string",
  "description": "string",
  "distance": "number",
  "track": [
    {
      "latitude": "number",
      "longitude": "number"
    }
  ]
}
```
- **Response**:
```json
{
  "track_id": "string",
  "message": "Track created successfully"
}
```

#### Get All Tracks
- **GET** `/getAllTracks`
- **Description**: Get all available tracks
- **Auth Required**: No
- **Response**:
```json
[
  {
    "track_id": "string",
    "name": "string",
    "description": "string",
    "distance": "number",
    "created_by": "string",
    "created_at": "datetime"
  }
]
```

#### Get Track by ID
- **GET** `/getTrackById`
- **Description**: Get specific track details
- **Auth Required**: No
- **Query Parameters**: `track_id`
- **Response**:
```json
{
  "track_id": "string",
  "name": "string",
  "description": "string",
  "distance": "number",
  "track": "array of coordinates",
  "created_by": "string",
  "created_at": "datetime"
}
```

#### Get User Tracks
- **GET** `/getUsersTracks`
- **Description**: Get tracks created by a user
- **Auth Required**: Yes
- **Query Parameters**: `user_id` (optional, defaults to authenticated user)
- **Response**: Array of track objects

#### Delete Track
- **POST** `/deleteTrack`
- **Description**: Delete a track
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "track_id": "string"
}
```

#### Delete All Tracks
- **POST** `/deleteAllTracks`
- **Description**: Delete all tracks (admin function)
- **Auth Required**: Yes

### Event Management

#### Create Event
- **POST** `/createEvent`
- **Description**: Create a new running event
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "name": "string",
  "description": "string",
  "track_id": "string",
  "date": "datetime",
  "max_participants": "number"
}
```
- **Response**:
```json
{
  "event_id": "string",
  "message": "Event created successfully"
}
```

#### Get All Open Events
- **GET** `/getAllOpenEvents`
- **Description**: Get all upcoming events
- **Auth Required**: No
- **Response**: Array of event objects

#### Get Event by ID
- **GET** `/getEventById`
- **Description**: Get specific event details
- **Auth Required**: No
- **Query Parameters**: `event_id`
- **Response**: Event object with participants

#### Get User Events
- **GET** `/getUsersEvents`
- **Description**: Get events for a user
- **Auth Required**: Yes
- **Query Parameters**: `user_id` (optional)

#### Get User Future Events
- **GET** `/getUsersFutureEvents`
- **Description**: Get upcoming events for a user
- **Auth Required**: Yes
- **Query Parameters**: `user_id` (optional)

#### Join Event
- **POST** `/joinEvent`
- **Description**: Join an event
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "event_id": "string"
}
```

#### Leave Event
- **POST** `/leaveEvent`
- **Description**: Leave an event
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "event_id": "string"
}
```

#### Get Event Registered Users
- **GET** `/getEventRegisteredUsers`
- **Description**: Get list of users registered for an event
- **Auth Required**: No
- **Query Parameters**: `event_id`

#### Start Event
- **POST** `/startEvent`
- **Description**: Start an event (host only)
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "event_id": "string"
}
```

#### End Event Run
- **POST** `/endEventRun`
- **Description**: End an event run
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "event_id": "string"
}
```

#### Mark User Ready
- **POST** `/markUserReady`
- **Description**: Mark user as ready for event
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "event_id": "string"
}
```

#### Set Event Ready
- **POST** `/setEventReady`
- **Description**: Set event as ready to start
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "event_id": "string"
}
```

#### Get Event Ready Users
- **GET** `/getEventReadyUsers`
- **Description**: Get users ready for an event
- **Auth Required**: No
- **Query Parameters**: `event_id`

#### Get Event Runners Positions
- **GET** `/getEventRunnersPositions`
- **Description**: Get real-time positions of event participants
- **Auth Required**: No
- **Query Parameters**: `event_id`

#### Update Runner Position
- **POST** `/updateRunnerPosition`
- **Description**: Update user's position during event
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "event_id": "string",
  "latitude": "number",
  "longitude": "number"
}
```

#### Delete Event
- **POST** `/deleteEvent`
- **Description**: Delete an event (host only)
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "event_id": "string"
}
```

#### Delete All Events
- **POST** `/deleteAllEvents`
- **Description**: Delete all events (admin function)
- **Auth Required**: Yes

### Social Features

#### Send Friend Request
- **POST** `/friend-requests`
- **Description**: Send a friend request
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "target_user_id": "string"
}
```

#### Get Friend Requests
- **GET** `/friend-requests`
- **Description**: Get incoming friend requests
- **Auth Required**: Yes
- **Response**: Array of friend request objects

#### Respond to Friend Request
- **POST** `/friend-requests/{request_id}`
- **Description**: Accept or reject a friend request
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "action": "accept" | "reject"
}
```

#### Get Friends
- **GET** `/friends`
- **Description**: Get user's friends list
- **Auth Required**: Yes
- **Query Parameters**: `user_id` (optional)

#### Get Friendship Status
- **GET** `/friendship-status`
- **Description**: Check friendship status with another user
- **Auth Required**: Yes
- **Query Parameters**: `target_user_id`

#### Remove Friend
- **POST** `/friends/{friend_user_id}`
- **Description**: Remove a friend
- **Auth Required**: Yes

### AI Coaching

#### Analyze User Data
- **POST** `/analyze-user`
- **Description**: Analyze user's running data and provide insights
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "user_id": "string"
}
```

#### Generate Training Plan
- **POST** `/generate-plan`
- **Description**: Generate personalized training plan
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "user_id": "string",
  "goal": "string",
  "duration_weeks": "number"
}
```

#### AI Coaching Service
- **POST** `/ai-coaching`
- **Description**: Get AI-powered coaching advice
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "message": "string",
  "context": "string"
}
```

### SignalR Integration

#### Negotiate
- **POST** `/negotiate`
- **Description**: SignalR connection negotiation
- **Auth Required**: Yes
- **Response**: SignalR connection details

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message description"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `409` - Conflict
- `500` - Internal Server Error

## Environment Variables

Required environment variables:
- `JWT_SECRET` - Secret key for JWT token signing
- `AzureWebJobsStorage` - Azure Storage connection string
- `AzureSignalRConnectionString` - SignalR connection string
- `OPENAI_API_KEY` - OpenAI API key for AI features

## Development

### Prerequisites
- Python 3.9+
- Azure Functions Core Tools
- Azure Storage Account
- Azure SignalR Service

### Local Development
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `local.settings.json`
4. Run locally: `func start`

### Testing
Run the API smoke tests:
```bash
python api_smoke_test.py
```

## Deployment

This backend is deployed on Azure Functions. The production URL is:
```
https://runfuncionapp.azurewebsites.net/api
```

## Project Structure

```
backend/
├── shared/
│   └── auth.py              # Authentication utilities
├── login/                   # User authentication
├── register/                # User registration
├── createActivity/          # Run tracking
├── createEvent/             # Event management
├── createTrack/             # Track management
├── aiCoachingService/       # AI coaching features
├── [other function folders] # Additional API endpoints
├── requirements.txt         # Python dependencies
├── host.json               # Azure Functions configuration
└── api_smoke_test.py       # API testing
```

## License

This project is licensed under the MIT License.
