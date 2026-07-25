## ADDED Requirements

### Requirement: Health Check Endpoint
The backend application SHALL expose a `GET /api/v1/health` endpoint that returns server status, database connection state, and a timestamp.

#### Scenario: Server and DB are Healthy
- **WHEN** a client performs a `GET` request on `/api/v1/health` while both the server and MongoDB are fully functional
- **THEN** the server returns status code `200` with the response body `{"status": "healthy", "db_connected": true, "timestamp": "<ISO-timestamp>"}`

#### Scenario: Database is Offline
- **WHEN** a client performs a `GET` request on `/api/v1/health` while MongoDB is offline or disconnected
- **THEN** the server returns status code `200` with the response body `{"status": "healthy", "db_connected": false, "timestamp": "<ISO-timestamp>"}`
