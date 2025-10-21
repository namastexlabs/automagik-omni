#!/bin/bash
# Clean restart script for Electron UI in WSL
# Kills all Electron/Vite processes before starting

echo "🧹 Cleaning up old Electron processes..."
pkill -9 -f "electron|vite" 2>/dev/null
sleep 1

echo "🚀 Starting Electron UI..."
pnpm run dev
