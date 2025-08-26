#!/bin/bash

# Setup script for Unix domain socket directories
# This script ensures the IPC socket directories exist with proper permissions

# Socket directory configuration
SOCKET_DIR="/automagik-omni/sockets"
LOG_DIR="/automagik-omni/logs"

echo "Setting up automagik-omni IPC socket directories..."

# Check if running as root or with sudo
if [ "$EUID" -eq 0 ]; then
    echo "Running with elevated privileges"
    
    # Create directories
    mkdir -p "$SOCKET_DIR"
    mkdir -p "$LOG_DIR"
    
    # Set ownership to the user who will run the services
    # If SUDO_USER is set, use that, otherwise use current user
    if [ -n "$SUDO_USER" ]; then
        chown -R "$SUDO_USER:$SUDO_USER" /automagik-omni
        echo "Ownership set to $SUDO_USER"
    else
        echo "Warning: Running as root without SUDO_USER set"
    fi
    
    # Set permissions
    chmod 755 /automagik-omni
    chmod 755 "$SOCKET_DIR"
    chmod 755 "$LOG_DIR"
    
    echo "✅ Socket directories created successfully at $SOCKET_DIR"
    
else
    echo "This script requires elevated privileges to create /automagik-omni"
    echo "Please run with: sudo ./setup_ipc_sockets.sh"
    echo ""
    echo "Alternatively, for development, you can use a user-writable location:"
    echo "  export AUTOMAGIK_SOCKET_DIR=~/automagik-omni/sockets"
    echo "  mkdir -p ~/automagik-omni/sockets"
    exit 1
fi

# Verify setup
if [ -d "$SOCKET_DIR" ]; then
    echo ""
    echo "Directory structure:"
    ls -la /automagik-omni/
    echo ""
    echo "Setup complete! The following socket paths will be used:"
    echo "  Discord: $SOCKET_DIR/discord-{instance}.sock"
    echo "  Slack:   $SOCKET_DIR/slack-{instance}.sock"
    echo "  Telegram: $SOCKET_DIR/telegram-{instance}.sock"
else
    echo "❌ Error: Socket directory was not created"
    exit 1
fi