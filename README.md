# Automagik Omni

## Overview

Automagik Omni is a **omnichannel messaging hub** that connects AI agents to WhatsApp, Slack, Discord, and more. Part of the Automagik Suite, it bridges intelligent agents with real-world messaging platforms at enterprise scale.

## Key Features

### 🤖 Smart AI Agent Integration
Connect your [Automagik Agents](https://github.com/namastexlabs/automagik) and [Automagik Hive](https://github.com/namastexlabs/automagik-hive) to any messaging platform with intelligent routing and context preservation.

### 📱 Multi-Channel Support
Deploy across WhatsApp, Slack(comming-soon), Discord(comming-soon), and other platforms from a single unified interface with real-time message handling.

### 🏢 Multi-Tenant Architecture
Manage multiple messaging instances for different clients, teams, or use cases with complete isolation and independent configurations.

### 📊 Real-Time Analytics
Track message flows, conversation metrics, and system performance with comprehensive tracing and detailed analytics dashboard.

### ⚡ Production-Ready APIs
RESTful APIs with authentication, real-time streaming, WebSocket support, and Docker-ready deployment out of the box.

### 🔄 Message Intelligence
Advanced message routing, mention parsing, media handling, and context-aware responses for natural conversations.

## Installation

### Universal Installation (Recommended)
```bash
# Clone and install with UV (fast Python package manager)
git clone https://github.com/namastexlabs/automagik-omni
cd automagik-omni
make install
```

## Tech Stack

### Core Framework
- **FastAPI** - High-performance async API framework
- **SQLAlchemy** - Database ORM with PostgreSQL support
- **Pydantic** - Data validation and serialization
- **Alembic** - Database migrations

### Messaging Integration
- **Evolution API** - WhatsApp Business API integration
- **Multi-platform** - Slack, Discord, and custom webhook support
- **Real-time** - WebSocket and streaming capabilities

### AI & Intelligence
- **Agent Routing** - Intelligent message distribution to AI agents
- **Context Preservation** - Maintain conversation context across sessions
- **Analytics** - Comprehensive message and performance tracking

## Deployment

### Quick Start
```bash
# Start development server
make dev

# Or deploy as production service
make deploy-service
```

### Docker Deployment
```bash
# Production deployment with Docker
docker-compose up --build -d

# View logs
make logs
```

### Configuration
Create a `.env` file with your settings:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/automagik_omni

# API Configuration  
API_HOST=0.0.0.0
API_PORT=8882
API_KEY=your_secure_api_key
```

## Getting Started

### 1. Start the Hub
```bash
make start-service
```

### 2. Check System Health
```bash
automagik-omni health
```

### 3. Manage Messaging Instances
```bash
# List all instances
make cli-instances

# Add a new WhatsApp instance (interactive)
make cli-create

# View detailed status
make status-local
```

## API Usage

Complete REST API for messaging hub management:

### Health Check
```bash
curl http://localhost:8882/health
```

### Send Messages
```bash
curl -X POST \
     -H "Authorization: Bearer your_api_key" \
     -H "Content-Type: application/json" \
     -d '{"phone": "+1234567890", "message": "Hello from Automagik!"}' \
     http://localhost:8882/api/v1/messages/text
```

### MCP Integration
Built-in Claude Code integration via MCP server:
```bash
# Available MCP tools
- manage_instances: Create and manage messaging instances
- send_message: Send messages through any configured channel  
- manage_traces: Track and analyze message flows
- manage_profiles: Handle user profiles and avatars
```

## Development

### Running Tests
```bash
# Run all tests with coverage
make test-coverage

# Run specific database tests
make test-postgres

# Quick quality check
make check
```

### Code Quality
```bash
# Format and lint code
make format lint

# Type checking
make typecheck

# All quality checks
make quality
```

## Automagik Suite Integration

Automagik Omni is part of the comprehensive **Automagik Suite**:

- **[Automagik Agents](https://github.com/namastexlabs/automagik)** - Rapid AI agent development framework
- **[Automagik Hive](https://github.com/namastexlabs/automagik-hive)** - Enterprise multi-agent orchestration  
- **Automagik Omni** - Omnichannel messaging hub (this project)

Connect them together for complete AI-powered messaging solutions at enterprise scale.

## Performance Benchmarks

| Metric | Development | Production |
|--------|-------------|------------|
| Startup Time | ~2-3s | ~5-8s |
| Message Response | <100ms | <300ms |
| Concurrent Messages | 50+ | 500+ |
| Instance Capacity | 10+ | 100+ |

## Community & Support

- **Documentation**: [Complete API Guide](COMPLETE_API_GUIDE.md)
- **Issues**: [GitHub Issues](https://github.com/namastexlabs/automagik-omni/issues)
- **Discord**: [Join our community](https://discord.gg/xcW8c7fF3R) 
- **Email**: [genie@namastex.ai](mailto:genie@namastex.ai)

## License

Built with ❤️ by [Namastex Labs](https://namastex.ai)

---

**Ready to connect your AI agents to the world?** Start with and watch the magic happen! ✨