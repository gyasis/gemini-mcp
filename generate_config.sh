#!/bin/bash

# Generate MCP client configuration for this server
# This script creates the JSON configuration needed to connect MCP clients to this server

# Check for single-line output flag
SINGLE_LINE=false
if [[ "$1" == "-s" || "$1" == "-ss" ]]; then
    SINGLE_LINE=true
fi

# Get the absolute path to this script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first:" >&2
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

# Define absolute paths for the python executable and server script
PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python"
SERVER_SCRIPT="$SCRIPT_DIR/server.py"

# Check if the virtual environment's Python executable exists
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "Error: Python executable not found at $PYTHON_EXEC" >&2
    echo "Please ensure the virtual environment is created and synced. You can do this by running:" >&2
    echo "uv venv && uv sync" >&2
    exit 1
fi

# Check if server.py exists
if [ ! -f "$SERVER_SCRIPT" ]; then
    echo "Error: server.py not found at $SERVER_SCRIPT" >&2
    exit 1
fi

# Generate the configuration JSON
if [ "$SINGLE_LINE" = true ]; then
  # Compact, single-line output without the top-level key, suitable for piping
  echo -n "{\"name\":\"Gemini MCP Server\",\"description\":\"MCP server for Gemini integration with tools for Q&A, code review, brainstorming, debugging, research, and video analysis.\",\"command\":\"$PYTHON_EXEC\",\"args\":[\"$SERVER_SCRIPT\"],\"cwd\":\"$SCRIPT_DIR\",\"env\":{},\"enabled\":true}"
else
  # Pretty-printed output for human consumption
  cat << EOF
{
  "claude_code-gemini-mcp": {
    "name": "Gemini MCP Server",
    "description": "MCP server for Gemini integration with tools for Q&A, code review, brainstorming, debugging, research, and video analysis.",
    "command": "$PYTHON_EXEC",
    "args": ["$SERVER_SCRIPT"],
    "cwd": "$SCRIPT_DIR",
    "env": {},
    "enabled": true
  }
}
EOF

  echo ""
  echo "📋 Copy the JSON above and add it to your MCP client configuration."
  echo "🔧 Make sure to set your GEMINI_API_KEY in the .env file before using."
fi