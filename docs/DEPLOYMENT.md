# 🚀 Omni-Hub Deployment Guide v0.2.0

## Quick Start

### Prerequisites
- Python 3.10 or higher
- uv package manager (recommended) or pip
- Git

### Installation

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd omni-hub
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Deploy**
   ```bash
   make install           # Install dependencies
   make db-init          # Initialize database
   make dev              # Start development server
   # OR
   ./scripts/deploy.sh   # Deploy production
   ```

## Configuration

### Required Environment Variables
```bash
# Agent API Configuration
AGENT_API_URL=https://your-agent-api.com
AGENT_API_KEY=your-agent-api-key
AGENT_API_DEFAULT_AGENT_NAME=your-agent

# Evolution API Configuration (WhatsApp)
EVOLUTION_TRANSCRIPT_API=http://your-evolution-api:8080
EVOLUTION_API_KEY=your-evolution-key
WHATSAPP_INSTANCE=your-whatsapp-instance
WHATSAPP_SESSION_ID_PREFIX=omni-
WHATSAPP_MINIO_URL=http://your-minio:9000
```

### Optional Configuration
```bash
# API Settings
API_PORT=8000
LOG_LEVEL=INFO

# Database (default: SQLite)
DATABASE_URL=sqlite:///omnihub.db
```

## Multi-Tenancy Features

### Instance Management via CLI
```bash
# List all instances
make cli-instances

# Create new instance (interactive)
make cli-create

# Or use direct commands
omnihub-instance list
omnihub-instance create --name "production" --whatsapp-instance "prod-wpp"
```

### Instance Management via API
```bash
# List instances
curl http://localhost:8000/api/instances/

# Create instance
curl -X POST http://localhost:8000/api/instances/ \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "whatsapp_instance": "test-wpp", "agent_api_url": "http://localhost:3000", "default_agent_name": "test-agent"}'

# Get instance
curl http://localhost:8000/api/instances/test
```

### Webhook Endpoints

**Legacy (backward compatible):**
```
POST /webhook/evolution
```

**Multi-tenant:**
```
POST /webhook/evolution/{instance_name}
```

## Service Management

### Using Makefile
```bash
make install-service    # Install systemd service
make start-service     # Start service
make stop-service      # Stop service  
make service-status    # Check status
make logs             # View logs
```

### Manual Management
```bash
# Start
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000

# Stop
pkill -f uvicorn

# View logs
tail -f logs/omni-hub.log
```

## Development

### Development Commands
```bash
make dev              # Start dev server with auto-reload
make test            # Run tests
make lint            # Check code quality
make format          # Format code
make validate        # Run validation checks
```

### Project Structure
```
omni-hub/
├── src/
│   ├── api/          # FastAPI application
│   ├── db/           # Database models and management
│   ├── cli/          # CLI tools
│   ├── channels/     # Channel handlers (WhatsApp)
│   └── services/     # Business logic
├── tests/            # Test suite
├── docs/             # Documentation
├── scripts/          # Deployment scripts
└── Makefile          # Automation commands
```

## Production Deployment

### Systemd Service (Recommended)
1. Install as service: `make install-service`
2. Start service: `make start-service`
3. Enable auto-start: Service is automatically enabled
4. Monitor: `make logs` or `journalctl -u omni-hub -f`

### Manual Process Management
For simple deployments, use the deployment script:
```bash
./scripts/deploy.sh
```

### Health Monitoring
- Health endpoint: `http://localhost:8000/health`
- API documentation: `http://localhost:8000/docs`
- Instance management: `http://localhost:8000/api/instances/`

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Change port in .env
   API_PORT=8001
   ```

2. **Permission errors**
   ```bash
   # Check file permissions
   ls -la logs/
   mkdir -p logs && chmod 755 logs
   ```

3. **Database errors**
   ```bash
   # Reinitialize database
   rm omnihub.db
   make db-init
   ```

4. **Service not starting**
   ```bash
   # Check logs
   make logs
   # Or check service status
   make service-status
   ```

### Logs Location
- **Development**: Console output
- **Production**: `logs/omni-hub.log`
- **Systemd**: `journalctl -u omni-hub`

## Migration from v0.1.0

The v0.2.0 release maintains full backward compatibility:

1. **Existing deployments continue working unchanged**
2. **Environment variables remain the same**
3. **Webhook endpoints unchanged** (`/webhook/evolution`)
4. **No breaking changes in API**

### To use new multi-tenancy features:
1. **Upgrade**: `git pull && make install`
2. **Initialize**: Database automatically creates default instance from env
3. **Manage**: Use CLI tools or API to create additional instances
4. **Route**: Use new endpoints `/webhook/evolution/{instance}` for specific instances

## Next Steps

- **Add more instances**: Use CLI or API to create tenant-specific configurations
- **Monitor**: Set up log monitoring and health checks
- **Scale**: Configure load balancing for multiple instances
- **Secure**: Review authentication and access controls

For more information, see the [Multi-Tenancy Plan](../MULTI_TENANCY_PLAN.md) and [API Documentation](http://localhost:8000/docs).