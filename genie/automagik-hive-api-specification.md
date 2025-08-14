# Automagik Hive API Technical Specification Document

**Version**: 0.1.0a61  
**Status**: Production Ready  
**Framework**: Agno Playground + FastAPI  
**Authentication**: x-api-key based  

## Executive Summary

The Automagik Hive API is a comprehensive multi-agent system built on the Agno framework that automatically generates RESTful CRUD endpoints for agents, teams, and workflows. The API provides both auto-generated Agno Playground endpoints for component management and custom business endpoints for specialized operations.

## API Architecture

### Core Components

1. **Agno Playground** (`/playground/*`) - Auto-generated CRUD endpoints
2. **Custom Business Endpoints** (`/api/v1/*`) - Specialized operations
3. **Dynamic Component Registry** - File-system based discovery
4. **Version Management** - Component versioning system
5. **MCP Integration** - Model Context Protocol tools

### Base Configuration

- **Base URL**: `http://localhost:8886` (configurable via HIVE_API_PORT)
- **OpenAPI Spec**: `/openapi.json`
- **Documentation**: `/docs` (Swagger UI)
- **ReDoc**: `/redoc`
- **Health Check**: `/api/v1/health`

## Authentication & Security

### API Key Authentication
- **Header**: `x-api-key`
- **Type**: String (required for protected endpoints)
- **Scope**: All `/playground/*` endpoints require authentication
- **Public Endpoints**: `/api/v1/health` (no auth required)

### Security Configuration
```yaml
# Environment Variables
HIVE_AUTH_DISABLED: true|false  # Development override
HIVE_API_KEY: "your-api-key"    # Required for authentication
```

### Usage Example
```bash
curl -H "x-api-key: your-api-key" \
     http://localhost:8886/playground/agents
```

## Auto-Generated Endpoints (Agno Playground)

The Agno framework automatically generates comprehensive CRUD endpoints for each component type:

### 1. Agent Endpoints

#### List All Agents
- **Endpoint**: `GET /playground/agents`
- **Authentication**: Required
- **Response**: `Array<AgentGetResponse>`
- **Description**: Get all available agents with metadata

```json
// Response Schema
[{
  "agent_id": "string",
  "name": "string", 
  "model": {
    "name": "string",
    "model": "string", 
    "provider": "string"
  },
  "add_context": boolean,
  "tools": [{}],
  "memory": {},
  "storage": {},
  "knowledge": {},
  "description": "string",
  "instructions": "string|array"
}]
```

#### Execute Agent
- **Endpoint**: `POST /playground/agents/{agent_id}/runs`
- **Authentication**: Required
- **Content-Type**: `multipart/form-data`
- **Description**: Execute agent with message and optional files

**Request Parameters:**
```json
{
  "message": "string (required)",
  "stream": "boolean (default: true)",
  "monitor": "boolean (default: false)", 
  "session_id": "string (optional)",
  "user_id": "string (optional)",
  "files": "array of files (optional)"
}
```

**Response:**
- **Streaming**: `StreamingResponse` (when stream=true)
- **Non-streaming**: `RunResponse` dictionary

**Supported File Types:**
- Images: JPG, PNG, GIF, WebP
- Audio: MP3, WAV, OGG
- Video: MP4, AVI, MOV
- Documents: PDF, TXT, MD

#### Continue Agent Run
- **Endpoint**: `POST /playground/agents/{agent_id}/runs/{run_id}/continue`
- **Authentication**: Required
- **Content-Type**: `application/x-www-form-urlencoded`
- **Description**: Continue paused agent execution

**Request Parameters:**
```json
{
  "tools": "string (JSON of ToolExecution objects - required)",
  "session_id": "string (optional)",
  "user_id": "string (optional)", 
  "stream": "boolean (default: true)"
}
```

#### Agent Session Management
- **List Sessions**: `GET /playground/agents/{agent_id}/sessions`
- **Get Session**: `GET /playground/agents/{agent_id}/sessions/{session_id}`
- **Delete Session**: `DELETE /playground/agents/{agent_id}/sessions/{session_id}`
- **Rename Session**: `POST /playground/agents/{agent_id}/sessions/{session_id}/rename`

**Session Response Schema:**
```json
{
  "title": "string",
  "session_id": "string",
  "session_name": "string", 
  "created_at": "integer (timestamp)"
}
```

#### Agent Memories
- **Endpoint**: `GET /playground/agents/{agent_id}/memories`
- **Authentication**: Required
- **Query Parameters**: `user_id` (required)
- **Description**: Retrieve agent memories for user

### 2. Team Endpoints

#### List All Teams
- **Endpoint**: `GET /playground/teams`
- **Authentication**: Required
- **Response**: `Array<TeamGetResponse>`
- **Description**: Get all available teams

#### Get Team Details
- **Endpoint**: `GET /playground/teams/{team_id}`
- **Authentication**: Required
- **Response**: `TeamGetResponse`
- **Description**: Get team configuration and details

#### Execute Team
- **Endpoint**: `POST /playground/teams/{team_id}/runs`
- **Authentication**: Required
- **Content-Type**: `multipart/form-data`
- **Description**: Execute team coordination

**Request Parameters:**
```json
{
  "message": "string (required)",
  "stream": "boolean (default: true)",
  "monitor": "boolean (default: true)",
  "session_id": "string (optional)",
  "user_id": "string (optional)",
  "files": "array of files (optional)"
}
```

#### Team Session Management
- **List Sessions**: `GET /playground/teams/{team_id}/sessions`
- **Get Session**: `GET /playground/teams/{team_id}/sessions/{session_id}`
- **Delete Session**: `DELETE /playground/teams/{team_id}/sessions/{session_id}`
- **Rename Session**: `POST /playground/teams/{team_id}/sessions/{session_id}/rename`

#### Team Memories
- **Endpoint**: `GET /playground/team/{team_id}/memories`
- **Authentication**: Required
- **Query Parameters**: `user_id` (required)

### 3. Workflow Endpoints

#### List All Workflows
- **Endpoint**: `GET /playground/workflows`
- **Authentication**: Required
- **Response**: `Array<WorkflowsGetResponse>`

#### Get Workflow Details
- **Endpoint**: `GET /playground/workflows/{workflow_id}`
- **Authentication**: Required
- **Response**: `WorkflowGetResponse`

#### Execute Workflow
- **Endpoint**: `POST /playground/workflows/{workflow_id}/runs`
- **Authentication**: Required
- **Content-Type**: `application/json`
- **Request**: `WorkflowRunRequest`

#### Workflow Session Management
- **List Sessions**: `GET /playground/workflows/{workflow_id}/sessions`
- **Get Session**: `GET /playground/workflows/{workflow_id}/sessions/{session_id}`
- **Delete Session**: `DELETE /playground/workflows/{workflow_id}/sessions/{session_id}`
- **Rename Session**: `POST /playground/workflows/{workflow_id}/sessions/{session_id}/rename`

### 4. System Status
- **Endpoint**: `GET /playground/status`
- **Authentication**: Required
- **Query Parameters**: `app_id` (optional)
- **Description**: Get playground system status

## Custom Business Endpoints

### Health Check
- **Endpoint**: `GET /api/v1/health`
- **Authentication**: None (public)
- **Response**: `{status: "healthy"}`

### Version Management

#### Execute Versioned Component
- **Endpoint**: `POST /api/v1/version/execute`
- **Authentication**: Required
- **Request**: `VersionedExecutionRequest`
- **Response**: `VersionedExecutionResponse`

#### Component Version CRUD
- **Create Version**: `POST /api/v1/version/components/{component_id}/versions`
- **List Versions**: `GET /api/v1/version/components/{component_id}/versions`
- **Get Version**: `GET /api/v1/version/components/{component_id}/versions/{version}`
- **Update Version**: `PUT /api/v1/version/components/{component_id}/versions/{version}`
- **Delete Version**: `DELETE /api/v1/version/components/{component_id}/versions/{version}`
- **Activate Version**: `POST /api/v1/version/components/{component_id}/versions/{version}/activate`

#### Component Management
- **List All Components**: `GET /api/v1/version/components`
- **List by Type**: `GET /api/v1/version/components/by-type/{component_type}`
- **Get History**: `GET /api/v1/version/components/{component_id}/history`

### MCP (Model Context Protocol) Status

#### System Status
- **Endpoint**: `GET /api/v1/mcp/status`
- **Authentication**: Required
- **Response**: System status with available servers

#### Server Management
- **List Servers**: `GET /api/v1/mcp/servers`
- **Test Connection**: `GET /api/v1/mcp/servers/{server_name}/test`
- **Get Configuration**: `GET /api/v1/mcp/config`

## Component Discovery System

The API uses a file-system based discovery system for dynamic component loading:

### Agent Discovery
- **Location**: `ai/agents/{agent-id}/`
- **Required Files**:
  - `config.yaml` - Agent configuration
  - Agent implementation files
- **Registry**: `AgentRegistry` with MCP integration
- **Factory Pattern**: Version-based instantiation via `create_agent()`

### Team Discovery
- **Location**: `ai/teams/{team-id}/`
- **Required Files**:
  - `config.yaml` - Team configuration
  - `team.py` - Team implementation
- **Factory Patterns**: Configurable factory function names
- **Default Patterns**: `get_{team_name}_team`, `create_{team_name}_team`

### Workflow Discovery
- **Location**: `ai/workflows/{workflow-id}/`
- **Required Files**:
  - `config.yaml` - Workflow configuration
  - `workflow.py` - Workflow implementation
- **Factory Pattern**: `get_{workflow_name}_workflow`

## Request/Response Schemas

### Core Data Types

#### AgentGetResponse
```json
{
  "agent_id": "string",
  "name": "string",
  "model": {
    "name": "string",
    "model": "string", 
    "provider": "string"
  },
  "add_context": "boolean",
  "tools": "array",
  "memory": "object",
  "storage": "object", 
  "knowledge": "object",
  "description": "string",
  "instructions": "string|array"
}
```

#### AgentRenameRequest
```json
{
  "name": "string (required)",
  "user_id": "string (required)"
}
```

#### TeamSessionResponse
```json
{
  "title": "string", 
  "session_id": "string",
  "session_name": "string",
  "created_at": "integer"
}
```

#### WorkflowRunRequest
```json
{
  "message": "string (required)",
  "session_id": "string (optional)",
  "user_id": "string (optional)",
  "parameters": "object (optional)"
}
```

#### VersionedExecutionRequest
```json
{
  "component_type": "string (required)",
  "component_id": "string (required)",
  "version": "integer (optional)",
  "parameters": "object (required)"
}
```

#### VersionedExecutionResponse  
```json
{
  "execution_id": "string",
  "component_type": "string",
  "component_id": "string", 
  "version": "integer",
  "status": "string",
  "result": "object",
  "error": "string (optional)"
}
```

## Error Handling

### HTTP Status Codes
- **200**: Success
- **401**: Authentication required/failed
- **404**: Resource not found
- **422**: Validation Error
- **500**: Internal server error

### Error Response Format
```json
{
  "detail": [
    {
      "loc": ["array", "of", "error", "location"],
      "msg": "Human readable error message",
      "type": "error_type"
    }
  ]
}
```

### Authentication Errors
```json
{
  "detail": "Invalid or missing x-api-key header",
  "headers": {
    "WWW-Authenticate": "x-api-key"
  }
}
```

## Streaming & Real-time Features

### Server-Sent Events (SSE)
- **Agent Runs**: Real-time streaming of agent responses
- **Team Coordination**: Live updates during team execution
- **Monitoring**: Optional monitoring for execution tracking

### Stream Configuration
- **Default**: `stream=true` for agent/team runs
- **Monitor**: `monitor=false` for agents, `monitor=true` for teams
- **Content-Type**: `text/event-stream`

## Development & Testing

### Local Development Setup
```bash
# Start API server
uv run api/serve.py

# With specific port
HIVE_API_PORT=8886 uv run api/serve.py

# Development mode with auto-reload  
HIVE_ENVIRONMENT=development uv run api/serve.py
```

### Testing Examples

#### List Agents
```bash
curl -H "x-api-key: your-key" \
     http://localhost:8886/playground/agents
```

#### Execute Agent
```bash
curl -X POST \
     -H "x-api-key: your-key" \
     -F "message=Hello World" \
     -F "stream=false" \
     http://localhost:8886/playground/agents/my-agent/runs
```

#### Health Check
```bash
curl http://localhost:8886/api/v1/health
```

## Configuration Management

### Environment Variables
```bash
# Server Configuration
HIVE_API_PORT=8886
HIVE_API_HOST=localhost
HIVE_ENVIRONMENT=production|development

# Authentication  
HIVE_AUTH_DISABLED=false
HIVE_API_KEY=your-secret-key

# Logging
HIVE_LOG_LEVEL=INFO
AGNO_LOG_LEVEL=WARNING

# CORS
HIVE_CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Component Configuration
Each component requires a `config.yaml` file with metadata and configuration:

```yaml
# Agent Configuration Example
agent:
  agent_id: "example-agent"
  version: 1
  model:
    name: "gpt-4"
    provider: "openai"
  tools:
    - name: "calculator"
      enabled: true
  instructions: |
    You are a helpful assistant...
```

## Deployment Considerations

### Production Configuration
- **Authentication**: Always enable API key authentication
- **CORS**: Configure specific origins, avoid wildcards
- **Logging**: Set appropriate log levels
- **Health Checks**: Monitor `/api/v1/health`

### Performance Optimization
- **Streaming**: Use streaming for long-running operations
- **Session Management**: Implement session cleanup
- **Component Caching**: Registry initialization is cached
- **Database**: Configure connection pooling for version management

### Security Best Practices
- **API Keys**: Use strong, unique API keys
- **HTTPS**: Enable TLS in production
- **Rate Limiting**: Implement request rate limiting
- **Input Validation**: All inputs are validated by Pydantic
- **File Upload**: Restrict file types and sizes

## API Client Examples

### Python Client
```python
import requests

class AutomagikHiveClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"x-api-key": api_key}
    
    def list_agents(self):
        response = requests.get(
            f"{self.base_url}/playground/agents",
            headers=self.headers
        )
        return response.json()
    
    def execute_agent(self, agent_id: str, message: str, stream: bool = True):
        data = {"message": message, "stream": stream}
        response = requests.post(
            f"{self.base_url}/playground/agents/{agent_id}/runs",
            headers=self.headers,
            files=data
        )
        return response

# Usage
client = AutomagikHiveClient("http://localhost:8886", "your-api-key")
agents = client.list_agents()
result = client.execute_agent("my-agent", "Hello!")
```

### JavaScript Client
```javascript
class AutomagikHiveClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = { 'x-api-key': apiKey };
    }
    
    async listAgents() {
        const response = await fetch(`${this.baseUrl}/playground/agents`, {
            headers: this.headers
        });
        return response.json();
    }
    
    async executeAgent(agentId, message, stream = true) {
        const formData = new FormData();
        formData.append('message', message);
        formData.append('stream', stream);
        
        const response = await fetch(
            `${this.baseUrl}/playground/agents/${agentId}/runs`,
            {
                method: 'POST',
                headers: this.headers,
                body: formData
            }
        );
        return response;
    }
}

// Usage
const client = new AutomagikHiveClient('http://localhost:8886', 'your-api-key');
const agents = await client.listAgents();
const result = await client.executeAgent('my-agent', 'Hello!');
```

## Conclusion

The Automagik Hive API provides a comprehensive, auto-generating REST interface for multi-agent system management. Built on the Agno framework, it offers both standardized CRUD operations for component management and specialized business endpoints for advanced functionality.

Key strengths:
- **Auto-generation**: Minimal configuration, maximum functionality
- **Dynamic Discovery**: File-system based component registration
- **Streaming Support**: Real-time execution monitoring
- **Version Management**: Component versioning with activation controls
- **Enterprise Ready**: Authentication, error handling, and production features

The API is designed for both direct integration and UI development, providing all necessary endpoints for building sophisticated multi-agent applications.