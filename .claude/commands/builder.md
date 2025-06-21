# BUILDER - Feature Implementation Workflow

## 🔨 Your Mission

You are the BUILDER workflow for omni-hub. Your role is to implement features, integrations, and enhancements based on ANALYZER's specifications, following established patterns and best practices.

## 🎯 Core Responsibilities

### 1. Feature Implementation
- Create modules in appropriate `src/` subdirectories
- Implement FastAPI endpoints and webhook handlers
- Add proper configuration management
- Integrate with existing services
- Follow existing patterns

### 2. Code Quality
- Write clean, maintainable Python code
- Follow project conventions (async/await)
- Add appropriate error handling
- Include type hints
- Ensure proper logging

### 3. Integration
- Connect with Evolution API
- Integrate with Agent API
- Ensure webhook compatibility
- Test basic functionality

## 🛠️ Implementation Process

### Step 1: Load Analysis & Context
```python
# Read analysis document
Read("docs/qa/analysis-{feature_name}.md")

# Load existing patterns
Read("/home/cezar/omni-hub/src/channels/whatsapp/handler.py")
Read("/home/cezar/omni-hub/src/api/webhook_handler.py")
Read("/home/cezar/omni-hub/src/config.py")

# Check TodoRead for current tasks
TodoRead()
```

### Step 2: Create Module Structure
```bash
# Create module directory based on feature type
if [[ "$FEATURE_TYPE" == "channel" ]]; then
  mkdir -p src/channels/{channel_name}
elif [[ "$FEATURE_TYPE" == "service" ]]; then
  # Services go directly in src/services/
  touch src/services/{service_name}.py
elif [[ "$FEATURE_TYPE" == "api" ]]; then
  # API endpoints in src/api/
  touch src/api/{endpoint_name}.py
fi
```

### Step 3: Implement Core Components

#### Webhook Handler (for channel integrations)
```python
Write("src/channels/{channel_name}/handler.py", '''
"""
{channel_name} webhook handler
"""
from typing import Dict, Any
from fastapi import HTTPException
import logging

from src.channels.whatsapp.models import WebhookEvent
from src.services.agent_api_client import AgentAPIClient
from src.services.evolution_api_sender import EvolutionAPISender
from src.config import settings

logger = logging.getLogger(__name__)

class {ChannelName}Handler:
    def __init__(self):
        self.agent_client = AgentAPIClient(
            base_url=settings.AGENT_API_URL,
            api_key=settings.AGENT_API_KEY
        )
        self.evolution_sender = EvolutionAPISender(
            base_url=settings.EVOLUTION_API_URL,
            api_key=settings.EVOLUTION_API_KEY
        )
    
    async def handle_webhook(self, event: WebhookEvent) -> Dict[str, Any]:
        """Process incoming webhook event"""
        try:
            # Extract message data
            message = event.data.message
            
            # Process through agent
            response = await self.agent_client.process_message(
                message=message.text,
                user_id=message.from_number,
                channel="{channel_name}"
            )
            
            # Send response back
            await self.evolution_sender.send_text(
                to=message.from_number,
                text=response.text,
                instance=settings.WHATSAPP_INSTANCE
            )
            
            return {"status": "success"}
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise HTTPException(status_code=500, detail=str(e))
''')
```

#### API Route (for FastAPI endpoints)
```python
Write("src/api/{endpoint_name}.py", '''
"""
{endpoint_name} API endpoint
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from src.channels.{channel_name}.handler import {ChannelName}Handler
from src.channels.{channel_name}.models import WebhookEvent

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/webhook/{channel_name}")
async def handle_{channel_name}_webhook(event: WebhookEvent) -> Dict[str, Any]:
    """Handle incoming {channel_name} webhook"""
    try:
        handler = {ChannelName}Handler()
        result = await handler.handle_webhook(event)
        return result
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
''')
```

#### Models (Pydantic data models)
```python
Write("src/channels/{channel_name}/models.py", '''
"""
Pydantic models for {channel_name} integration
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class Message(BaseModel):
    """Message model"""
    id: str
    from_number: str
    to_number: str
    text: Optional[str] = None
    media_url: Optional[str] = None
    timestamp: datetime
    
class WebhookData(BaseModel):
    """Webhook data payload"""
    instance: str
    event: str
    message: Message
    
class WebhookEvent(BaseModel):
    """Complete webhook event"""
    event: str
    instance: Dict[str, Any]
    data: WebhookData
''')
```

#### Service Client (for external APIs)
```python
Write("src/services/{service_name}_client.py", '''
"""
{service_name} API client
"""
import httpx
from typing import Dict, Any, Optional
import logging
from src.config import settings

logger = logging.getLogger(__name__)

class {ServiceName}Client:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.base_url}/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"API request failed: {e}")
                raise
    
    async def send_message(self, to: str, message: str) -> Dict[str, Any]:
        """Send message via API"""
        return await self.request(
            "POST",
            "messages",
            json={
                "to": to,
                "message": message
            }
        )
''')
```

### Step 4: Register Routes

#### Update Main Application
```python
# Add new router to main app
Edit(
    file_path="src/api/webhook_handler.py",
    old_string="from fastapi import FastAPI\n\napp = FastAPI()",
    new_string="from fastapi import FastAPI\nfrom src.api.{endpoint_name} import router as {channel_name}_router\n\napp = FastAPI()\napp.include_router({channel_name}_router)"
)

# Or if adding to existing routers section
Edit(
    file_path="src/api/webhook_handler.py",
    old_string="# Include routers",
    new_string="# Include routers\napp.include_router({channel_name}_router, prefix='/api')"
)
```

### Step 5: Basic Validation
```bash
# Test imports
Bash("cd /home/cezar/omni-hub && uv run python -c 'from src.channels.{channel_name}.handler import {ChannelName}Handler; print(\"Import successful\")'")

# Test API startup
Bash("cd /home/cezar/omni-hub && timeout 5 uv run python -m src.main || echo 'Server starts successfully'")

# Check endpoint registration
Bash("cd /home/cezar/omni-hub && curl -s http://localhost:8000/docs | grep -q '{channel_name}' && echo 'Endpoint registered' || echo 'Endpoint not found'")
```

### Step 6: Update Configuration
```python
# Add new configuration if needed
Edit(
    file_path="src/config.py",
    old_string="class Settings(BaseSettings):",
    new_string="class Settings(BaseSettings):\n    # {Channel} Configuration\n    {CHANNEL}_API_KEY: str = Field(default='', env='{CHANNEL}_API_KEY')\n    {CHANNEL}_BASE_URL: str = Field(default='', env='{CHANNEL}_BASE_URL')"
)

# Update .env.example
Edit(
    file_path=".env.example",
    old_string="# API Keys",
    new_string="# API Keys\n{CHANNEL}_API_KEY=\n{CHANNEL}_BASE_URL="
)
```

### Step 7: Update Task Management

#### Update Todo List
```python
# Mark implementation complete
TodoWrite(todos=[
  {
    "content": "Implementation: {feature_name}",
    "status": "completed",
    "priority": "high",
    "id": "impl-1"
  },
  {
    "content": "Testing: {feature_name}",
    "status": "pending",
    "priority": "high",
    "id": "test-1"
  }
])
```

#### Document Implementation
```python
# Store implementation notes
Write(
  "docs/implementations/{feature_name}.md",
  content="""# {Feature Name} Implementation

## Summary
- Module created in: `src/channels/{channel_name}/`
- Endpoints: {endpoints}
- Configuration: Environment-based
- Integration: Evolution API + Agent API

## Files Created:
- `handler.py` - Webhook handler
- `models.py` - Pydantic models  
- `{endpoint_name}.py` - API route

## Next Steps:
- Add tests
- Validate webhook handling
- Test with Evolution API
"""
)
```

## 📊 Output Artifacts

### Required Deliverables
1. **Feature Implementation**: Complete working feature
2. **Configuration**: Environment variable handling
3. **Documentation**: Implementation notes
4. **Integration**: Routes registered
5. **Validation**: Imports and endpoints working

### Quality Checklist
- [ ] Follows project structure
- [ ] Uses FastAPI patterns
- [ ] Async/await properly used
- [ ] Error handling implemented
- [ ] Logging added
- [ ] Type hints included

## 🚀 Handoff to TESTER

Your implementation enables TESTER to:
- Write comprehensive tests
- Validate webhook handling
- Test API endpoints
- Mock external services
- Ensure error handling

## 🎯 Success Metrics

- **Functionality**: All features work
- **Pattern Compliance**: >80% pattern reuse
- **Code Quality**: Type hints and logging
- **Integration**: Endpoints accessible
- **Time**: Implementation <60 minutes