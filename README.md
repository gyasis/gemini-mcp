# Claude-Gemini MCP Server
# Gemini MCP Server

This project provides a server that implements the Multi-tool Co-pilot Protocol (MCP), enabling a primary AI model to collaborate with Google's Gemini Pro model for enhanced capabilities.

It acts as a bridge, allowing a compatible AI assistant to offload specific tasks like asking questions, reviewing code, or brainstorming to Gemini.

## Features

- **General MCP Interface**: Implements the MCP protocol for easy integration with any compatible client.
- **Gemini Integration**: Leverages the power of Google's Gemini model.
- **Extensible Toolset**: Easily add new tools that call upon Gemini's capabilities.
- **Lightweight and Fast**: Built with Python, easy to run and deploy.

## Setup and Installation

This project uses `uv` for fast and reliable Python environment and package management.

1.  **Install `uv`**:
    If you don't have `uv` installed, follow the official installation instructions:
    ```bash
    # On macOS and Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2.  **Configure API Key**:
    Create a `.env` file in the root of the project and add your Gemini API key:
    ```
    GEMINI_API_KEY="YOUR_API_KEY_HERE"
    ```

## Running the Server

With `uv` installed and your `.env` file created, you can run the server with a single command. `uv` will automatically create a virtual environment and install the dependencies from `requirements.txt` for you.

```bash
uv run python server.py
```

The server will start and listen for requests from any MCP-compatible client.

## Development and Testing

### Using MCP Dev Server

For development and testing, you can use the built-in MCP development server:

```bash
# Run the development server
uv run mcp dev server.py
```

This provides enhanced debugging output and development features.

### Testing with MCP Inspector

The MCP Inspector provides a web-based interface to test your server tools interactively:

```bash
# Install and run MCP Inspector
npx @modelcontextprotocol/inspector
```

Then open the provided URL (usually `http://localhost:6274`) in your browser. You can:
- Test all available tools
- View tool schemas and descriptions  
- Execute tools with custom parameters
- Monitor server responses in real-time

To connect your server to the inspector:
1. In the inspector web interface, add a new server
2. Use these connection details:
   - **Command**: `uv`
   - **Args**: `["run", "python", "server.py"]`
   - **Working Directory**: `/path/to/your/claude_code-gemini-mcp`

### Direct Testing

You can also test the server directly:

```bash
# Test server startup
uv run python server.py

# The server will wait for JSON-RPC input on stdin
# Press Ctrl+C to exit
```

## Client Integration

To integrate this server with an MCP-compatible client, you need to generate a JSON configuration. The included script makes this easy.

Run the script to generate the necessary JSON:

```bash
./generate_config.sh
```

This will output a JSON block that you can add to your client's configuration file. The output will look something like this, with the correct absolute paths for your system:

```json
{
  "claude_code-gemini-mcp": {
    "name": "Gemini MCP Server",
    "description": "A general MCP server for Gemini integration.",
    "command": "/path/to/your/project/claude_code-gemini-mcp/.venv/bin/python",
    "args": ["/path/to/your/project/claude_code-gemini-mcp/server.py"],
    "env": {},
    "enabled": true
  }
}
```

## How it Works

The server follows the [Multi-tool Co-pilot Protocol (MCP)](https://github.com/sourcegraph/handbook/blob/main/engineering/rfcs/2024-04-22-rfc-1075-mcp-v0.md), a spec for how an AI assistant can talk to tools.

- **`initialize`**: The client starts communication and the server returns its capabilities.
- **`tools/list`**: The client requests a list of available tools.
- **`tools/call`**: The client asks the server to run a specific tool with given arguments.

The server currently exposes the following tools to the client:
- `ask_gemini`: Ask Gemini a direct question.
- `gemini_code_review`: Get a code review from Gemini.
- `gemini_brainstorm`: Brainstorm ideas with Gemini.
- `gemini_debug`: Analyze error messages and suggest fixes.
- `gemini_research`: Get research with Google Search grounding.
- `watch_video`: Analyze YouTube videos or local video files.
