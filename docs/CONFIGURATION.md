# Configuration Reference

Complete reference for all environment variables and configuration options in Automagik Omni.

## Quick Start

The `.env.example` file contains all commonly-used configuration options with sensible defaults. Copy it to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

**Required Configuration:**
- `AUTOMAGIK_OMNI_API_KEY` - Must be set for API authentication

**Commonly Changed:**
- `AUTOMAGIK_OMNI_API_PORT` - API server port (default: 8882)
- `AUTOMAGIK_OMNI_CORS_ORIGINS` - Allowed CORS origins (comma-separated)

## Core API Settings

### `AUTOMAGIK_OMNI_API_KEY` (REQUIRED)
- **Type:** String
- **Default:** None (must be set)
- **Description:** API authentication key for securing endpoints
- **Example:** `"sk-omni-abc123xyz..."`

### `AUTOMAGIK_OMNI_API_HOST`
- **Type:** String
- **Default:** `"0.0.0.0"`
- **Description:** Host address to bind the API server
- **Options:** `"0.0.0.0"` (all interfaces), `"127.0.0.1"` (localhost only)

### `AUTOMAGIK_OMNI_API_PORT`
- **Type:** Integer
- **Default:** `8882`
- **Description:** Port number for the API server
- **Example:** `"8882"`

### `AUTOMAGIK_OMNI_PROD_SERVER_URL`
- **Type:** String (URL)
- **Default:** Empty
- **Description:** Production server URL for Swagger UI documentation
- **Example:** `"https://api.example.com"`

## CORS Configuration

### `AUTOMAGIK_OMNI_CORS_ORIGINS`
- **Type:** Comma-separated list
- **Default:** `"*"`
- **Description:** Allowed origins for CORS requests
- **Development:** `"*"` or `"http://localhost:3000,http://localhost:8888"`
- **Production:** Specific domains only, e.g., `"https://app.example.com"`

### Advanced CORS Options

These have sensible defaults but can be customized:

#### `AUTOMAGIK_OMNI_CORS_CREDENTIALS`
- **Type:** Boolean string
- **Default:** `"true"`
- **Description:** Allow credentials (cookies, auth headers) in CORS requests
- **Options:** `"true"`, `"false"`

#### `AUTOMAGIK_OMNI_CORS_METHODS`
- **Type:** Comma-separated list
- **Default:** `"GET,POST,PUT,DELETE,OPTIONS"`
- **Description:** Allowed HTTP methods for CORS

#### `AUTOMAGIK_OMNI_CORS_HEADERS`
- **Type:** Comma-separated list
- **Default:** `"*"`
- **Description:** Allowed headers for CORS requests

## Environment & Logging

### `ENVIRONMENT`
- **Type:** String
- **Default:** `"development"`
- **Description:** Application environment mode
- **Options:** `"development"`, `"production"`

### `LOG_LEVEL`
- **Type:** String
- **Default:** `"INFO"`
- **Description:** Minimum log level to display
- **Options:** `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`

### `LOG_FOLDER`
- **Type:** Path
- **Default:** `"./logs"`
- **Description:** Directory for log file outputs

### `AUTOMAGIK_OMNI_LOG_VERBOSITY`
- **Type:** String
- **Default:** `"short"`
- **Description:** Log output detail level
- **Options:**
  - `"short"` - Shortened file paths in logs
  - `"full"` - Full file paths in logs

### `AUTOMAGIK_TIMEZONE`
- **Type:** String (timezone name)
- **Default:** `"UTC"`
- **Description:** Timezone for message timestamps
- **Example:** `"America/New_York"`, `"Europe/London"`, `"Asia/Tokyo"`
- **Note:** Must be a valid IANA timezone identifier

## Database Configuration

### `AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH`
- **Type:** File path
- **Default:** `"./data/automagik-omni.db"`
- **Description:** Path to SQLite database file
- **Recommended:** Use for development and small-to-medium deployments

### `AUTOMAGIK_OMNI_DATABASE_URL`
- **Type:** Database URL
- **Default:** Empty (uses SQLite)
- **Description:** PostgreSQL or other database connection URL
- **Format:** `"postgresql://user:password@host:port/database"`
- **Example:** `"postgresql://omni:secret@localhost:5432/automagik_omni"`
- **Note:** When set, overrides SQLite configuration

## Message Tracing

### `AUTOMAGIK_OMNI_ENABLE_TRACING`
- **Type:** Boolean string
- **Default:** `"true"`
- **Description:** Enable message flow tracing and debugging
- **Options:** `"true"`, `"false"`

### `AUTOMAGIK_OMNI_TRACE_RETENTION_DAYS`
- **Type:** Integer
- **Default:** `30`
- **Description:** Number of days to retain trace records

### `AUTOMAGIK_OMNI_TRACE_MAX_PAYLOAD_SIZE`
- **Type:** Integer (bytes)
- **Default:** `1048576` (1MB)
- **Description:** Maximum payload size to store in traces

### `AUTOMAGIK_OMNI_TRACE_INCLUDE_SENSITIVE`
- **Type:** Boolean string
- **Default:** `"false"`
- **Description:** Include sensitive data (credentials, tokens) in traces
- **Warning:** NEVER enable in production!
- **Use case:** Development debugging only

## Advanced Configuration

The following options are available but rarely need to be changed from their defaults. They are not included in `.env.example` to keep it minimal.

### Performance & Scaling

While these environment variables are not currently implemented in the code, they are documented here for future reference:

- `AUTOMAGIK_OMNI_MAX_CONCURRENT_REQUESTS` - Max concurrent API requests (future)
- `AUTOMAGIK_OMNI_REQUEST_TIMEOUT` - API request timeout in seconds (future)
- `AUTOMAGIK_OMNI_UVICORN_WORKERS` - Number of uvicorn worker processes (future)

### Security

Advanced security options (not currently implemented):

- `AUTOMAGIK_OMNI_RATE_LIMIT_PER_MINUTE` - API rate limiting (future)
- `AUTOMAGIK_OMNI_ENABLE_SSL` - Enable SSL/TLS (future)
- `AUTOMAGIK_OMNI_SSL_CERT_PATH` - SSL certificate path (future)
- `AUTOMAGIK_OMNI_SSL_KEY_PATH` - SSL private key path (future)

### Monitoring

Monitoring options (not currently implemented):

- `AUTOMAGIK_OMNI_METRICS_ENABLED` - Enable Prometheus metrics (future)
- `AUTOMAGIK_OMNI_METRICS_PORT` - Metrics endpoint port (future)
- `AUTOMAGIK_OMNI_HEALTH_CHECK_INTERVAL` - Health check interval (future)

## Configuration Precedence

Configuration is loaded in the following order (later sources override earlier ones):

1. Default values in `src/config.py`
2. Environment variables from `.env` file
3. Environment variables set in shell/system

## Validation

The application validates configuration on startup:

- `AUTOMAGIK_OMNI_API_KEY` must be set (REQUIRED)
- Timezone must be a valid IANA identifier
- Database URL must be valid if PostgreSQL is used

Invalid configuration will cause the application to fail at startup with clear error messages.

## Example Configurations

### Development Setup

```bash
# .env
AUTOMAGIK_OMNI_API_KEY="dev-test-key-123"
AUTOMAGIK_OMNI_API_PORT="8882"
AUTOMAGIK_OMNI_CORS_ORIGINS="*"
ENVIRONMENT="development"
LOG_LEVEL="DEBUG"
AUTOMAGIK_OMNI_ENABLE_TRACING="true"
```

### Production Setup

```bash
# .env
AUTOMAGIK_OMNI_API_KEY="prod-secure-random-key-here"
AUTOMAGIK_OMNI_API_PORT="8882"
AUTOMAGIK_OMNI_CORS_ORIGINS="https://app.example.com,https://admin.example.com"
ENVIRONMENT="production"
LOG_LEVEL="INFO"
AUTOMAGIK_OMNI_DATABASE_URL="postgresql://omni:password@db.example.com:5432/omni_prod"
AUTOMAGIK_OMNI_ENABLE_TRACING="true"
AUTOMAGIK_OMNI_TRACE_INCLUDE_SENSITIVE="false"
AUTOMAGIK_TIMEZONE="America/New_York"
```

### Testing Setup

```bash
# .env.test
AUTOMAGIK_OMNI_API_KEY="test-key"
ENVIRONMENT="development"
LOG_LEVEL="WARNING"
AUTOMAGIK_OMNI_ENABLE_TRACING="false"
AUTOMAGIK_OMNI_SQLITE_DATABASE_PATH=":memory:"
```

## See Also

- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [API Documentation](../README.md#api-documentation) - API endpoint reference
- Main README for quick start and overview
