#!/bin/bash
set -e

# Setup PostgreSQL for testing
echo "🐘 Setting up PostgreSQL for testing..."

# Configuration
CONTAINER_NAME="omni-test-postgres"
POSTGRES_VERSION="15"
POSTGRES_PASSWORD="testpass"
POSTGRES_DB="testdb"
POSTGRES_PORT="5432"

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker or set up PostgreSQL manually."
        echo "   See tests/README.md for manual installation instructions."
        exit 1
    fi
}

# Function to start PostgreSQL container
start_postgres() {
    echo "🚀 Starting PostgreSQL container..."
    
    # Stop existing container if running
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        echo "🔄 Stopping existing container..."
        docker stop $CONTAINER_NAME
    fi
    
    # Remove existing container if exists
    if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
        echo "🗑️  Removing existing container..."
        docker rm $CONTAINER_NAME
    fi
    
    # Start new container
    docker run -d \
        --name $CONTAINER_NAME \
        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
        -e POSTGRES_DB=$POSTGRES_DB \
        -p $POSTGRES_PORT:5432 \
        postgres:$POSTGRES_VERSION
    
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 5
    
    # Wait for PostgreSQL to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec $CONTAINER_NAME pg_isready -U postgres -q; then
            echo "✅ PostgreSQL is ready!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            echo "❌ PostgreSQL failed to start after $max_attempts attempts"
            docker logs $CONTAINER_NAME
            exit 1
        fi
        
        echo "   Attempt $attempt/$max_attempts - waiting..."
        sleep 2
        ((attempt++))
    done
}

# Function to set environment variables
set_environment() {
    echo "🔧 Setting environment variables..."
    
    # Export variables for current session
    export POSTGRES_HOST=localhost
    export POSTGRES_PORT=$POSTGRES_PORT
    export POSTGRES_USER=postgres
    export POSTGRES_PASSWORD=$POSTGRES_PASSWORD
    export POSTGRES_DB=$POSTGRES_DB
    
    echo "   POSTGRES_HOST=localhost"
    echo "   POSTGRES_PORT=$POSTGRES_PORT"
    echo "   POSTGRES_USER=postgres"
    echo "   POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
    echo "   POSTGRES_DB=$POSTGRES_DB"
    
    # Create environment file for easy sourcing
    cat > .env.test.postgres << EOF
# PostgreSQL Test Environment Variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=$POSTGRES_PORT
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=$POSTGRES_PASSWORD
export POSTGRES_DB=$POSTGRES_DB
EOF
    
    echo "📝 Environment variables saved to .env.test.postgres"
    echo "   Run 'source .env.test.postgres' to load them in other sessions"
}

# Function to test connection
test_connection() {
    echo "🔌 Testing PostgreSQL connection..."
    
    if docker exec $CONTAINER_NAME psql -U postgres -d $POSTGRES_DB -c "SELECT version();" > /dev/null 2>&1; then
        echo "✅ PostgreSQL connection successful!"
        
        # Show version
        echo "📊 PostgreSQL version:"
        docker exec $CONTAINER_NAME psql -U postgres -d $POSTGRES_DB -c "SELECT version();" | grep PostgreSQL
    else
        echo "❌ PostgreSQL connection failed"
        exit 1
    fi
}

# Function to install Python dependencies
install_dependencies() {
    echo "🐍 Checking Python PostgreSQL dependencies..."
    
    if python -c "import psycopg2" 2>/dev/null; then
        echo "✅ psycopg2 already installed"
    else
        echo "📦 Installing psycopg2..."
        if command -v uv &> /dev/null; then
            uv add psycopg2-binary
        elif [ -f "pyproject.toml" ]; then
            pip install psycopg2-binary
        else
            echo "❌ Could not determine how to install psycopg2"
            echo "   Please run: pip install psycopg2-binary"
            exit 1
        fi
    fi
}

# Function to run a quick test
run_quick_test() {
    echo "🧪 Running a quick test..."
    
    if pytest tests/test_database_models.py::TestInstanceConfigModel::test_create_instance_config -v; then
        echo "✅ Quick test passed with PostgreSQL!"
    else
        echo "❌ Quick test failed"
        exit 1
    fi
}

# Main execution
main() {
    echo "🏁 PostgreSQL Test Setup"
    echo "========================="
    
    check_docker
    start_postgres
    set_environment
    test_connection
    install_dependencies
    run_quick_test
    
    echo ""
    echo "🎉 PostgreSQL test setup complete!"
    echo ""
    echo "📋 Next steps:"
    echo "   • Run tests: make test"
    echo "   • Load env in new shell: source .env.test.postgres"
    echo "   • Stop PostgreSQL: docker stop $CONTAINER_NAME"
    echo "   • Remove PostgreSQL: docker rm $CONTAINER_NAME"
    echo ""
    echo "🔍 View logs: docker logs $CONTAINER_NAME"
}

# Handle command line arguments
case "${1:-}" in
    "stop")
        echo "🛑 Stopping PostgreSQL container..."
        docker stop $CONTAINER_NAME || true
        ;;
    "remove"|"rm")
        echo "🗑️  Removing PostgreSQL container..."
        docker stop $CONTAINER_NAME || true
        docker rm $CONTAINER_NAME || true
        ;;
    "logs")
        echo "📋 PostgreSQL container logs:"
        docker logs $CONTAINER_NAME
        ;;
    "shell"|"psql")
        echo "🐘 Opening PostgreSQL shell..."
        docker exec -it $CONTAINER_NAME psql -U postgres -d $POSTGRES_DB
        ;;
    "status")
        echo "📊 PostgreSQL container status:"
        docker ps -f name=$CONTAINER_NAME
        echo ""
        echo "🔌 Connection test:"
        docker exec $CONTAINER_NAME pg_isready -U postgres || echo "❌ Not ready"
        ;;
    "")
        main
        ;;
    *)
        echo "Usage: $0 [stop|remove|logs|shell|status]"
        echo ""
        echo "Commands:"
        echo "  (no args)  Setup PostgreSQL for testing"
        echo "  stop       Stop the PostgreSQL container"
        echo "  remove     Remove the PostgreSQL container"
        echo "  logs       Show PostgreSQL container logs"
        echo "  shell      Open PostgreSQL shell (psql)"
        echo "  status     Show container status"
        exit 1
        ;;
esac