# Testing Documentation

## Database Testing Options

The test suite supports multiple database backends with automatic fallback:

### 1. SQLite (Default)
- **Pros**: No external dependencies, fast setup
- **Cons**: Limited SQL features, different behavior from production
- **Usage**: Default behavior, no configuration needed

### 2. PostgreSQL (Recommended)
- **Pros**: Production parity, full SQL features, better isolation
- **Cons**: Requires PostgreSQL server
- **Usage**: Set `POSTGRES_HOST` environment variable

### 3. Custom Database
- **Usage**: Set `TEST_DATABASE_URL` environment variable

## PostgreSQL Testing Setup

### Option 1: Docker (Recommended)

```bash
# Start PostgreSQL container
docker run --name test-postgres -e POSTGRES_PASSWORD=testpass -e POSTGRES_DB=testdb -p 5432:5432 -d postgres:15

# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=testpass
export POSTGRES_DB=testdb

# Run tests
make test
```

### Option 2: Local PostgreSQL Installation

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt-get install postgresql postgresql-contrib python3-psycopg2

# Create test user and database
sudo -u postgres createuser --createdb testuser
sudo -u postgres createdb testdb -O testuser

# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_USER=testuser
export POSTGRES_DB=testdb
# No password needed for local peer authentication

# Run tests
make test
```

### Option 3: GitHub Actions / CI

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: testpass
      POSTGRES_DB: testdb
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5

env:
  POSTGRES_HOST: localhost
  POSTGRES_PORT: 5432
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: testpass
  POSTGRES_DB: testdb
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_DATABASE_URL` | Explicit database URL override | None |
| `POSTGRES_HOST` | PostgreSQL server host | localhost |
| `POSTGRES_PORT` | PostgreSQL server port | 5432 |
| `POSTGRES_USER` | PostgreSQL username | postgres |
| `POSTGRES_PASSWORD` | PostgreSQL password | (empty) |
| `POSTGRES_DB` | PostgreSQL database name | postgres |

## Test Database Behavior

### SQLite Mode
- Creates temporary `.db` files for each test
- Automatically cleaned up after tests
- Isolated per test function

### PostgreSQL Mode
- Creates unique temporary databases (`test_omni_<random>`)
- Automatically dropped after tests
- Full transaction isolation
- Terminates active connections before cleanup

### Database Selection Priority
1. `TEST_DATABASE_URL` if set (highest priority)
2. PostgreSQL if `POSTGRES_HOST` is set and `psycopg2` is available
3. Temporary SQLite (fallback)

## Examples

### Run tests with SQLite (default)
```bash
make test
```

### Run tests with PostgreSQL
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PASSWORD=mypass
make test
```

### Run tests with custom database
```bash
export TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/mydb"
make test
```

### Run specific test with PostgreSQL
```bash
export POSTGRES_HOST=localhost
pytest tests/test_session_filtering_integration.py::TestSessionFilteringIntegration::test_filter_by_agent_session_id_functional -v
```

## Troubleshooting

### PostgreSQL Connection Issues
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Test connection manually
psql -h localhost -U postgres -d postgres
```

### Missing psycopg2
```bash
# Install PostgreSQL Python driver
pip install psycopg2-binary
# or
conda install psycopg2
```

### Permission Issues
```bash
# Grant database creation privileges
sudo -u postgres psql -c "ALTER USER myuser CREATEDB;"
```