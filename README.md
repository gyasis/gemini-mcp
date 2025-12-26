# Claude-Gemini MCP Server
# Gemini MCP Server

This project provides a server that implements the Multi-tool Co-pilot Protocol (MCP), enabling a primary AI model to collaborate with Google's Gemini Pro model for enhanced capabilities.

It acts as a bridge, allowing a compatible AI assistant to offload specific tasks like asking questions, reviewing code, or brainstorming to Gemini.

## Features

- **General MCP Interface**: Implements the MCP protocol for easy integration with any compatible client.
- **Gemini Integration**: Leverages the power of Google's Gemini 3 Flash model (gemini-3-flash-preview).
- **Multi-Image Analysis**: Compare and analyze up to 3,600 images in a single request.
- **Extensible Toolset**: Easily add new tools that call upon Gemini's capabilities.
- **Multimodal Support**: Process text, images, and videos through Gemini's multimodal capabilities.
- **Lightweight and Fast**: Built with Python, easy to run and deploy.

## Models Used

This MCP server uses the latest Gemini models for optimal performance:

| Tool Type | Model | Notes |
|-----------|-------|-------|
| **Most Tools** | `gemini-3-flash-preview` | Latest Gemini 3 Flash (Pro-level performance at Flash speeds) |
| ask_gemini | `gemini-3-flash-preview` | General Q&A and collaboration |
| gemini_code_review | `gemini-3-flash-preview` | Code analysis and review |
| gemini_brainstorm | `gemini-3-flash-preview` | Creative ideation |
| gemini_debug | `gemini-3-flash-preview` | Error analysis and debugging |
| gemini_research | `gemini-3-flash-preview` | Google Search grounded research |
| watch_video | `gemini-3-flash-preview` | Video analysis (YouTube & local files) |
| interpret_image | `gemini-3-flash-preview` | Image understanding and analysis |
| **Deep Research** | `deep-research-pro-preview-12-2025` | Specialized research model for complex queries |

**Model Features:**
- 🎯 **Gemini 3 Flash**: Pro-level reasoning at Flash speeds, 1M token context window
- 🔬 **Deep Research Pro**: Multi-hop reasoning, automatic query refinement, source synthesis
- 💰 **Pricing**: Gemini 3 Flash - $0.50/1M input tokens, $3/1M output tokens

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

The server currently exposes **19 tools** to the client:

**Core Gemini Tools (6):**
- `ask_gemini`: Ask Gemini a direct question.
- `gemini_code_review`: Get a code review from Gemini.
- `gemini_brainstorm`: Brainstorm ideas with Gemini.
- `gemini_debug`: Analyze error messages and suggest fixes.
- `gemini_research`: Get research with Google Search grounding.
- `watch_video`: Analyze YouTube videos or local video files.

**Deep Research Tools (7):**
- `start_deep_research`: Start complex research with multi-hop reasoning (5-60 min duration).
- `check_research_status`: Monitor async research task progress.
- `get_research_results`: Retrieve completed research reports (zero-cost retrieval from SQLite).
- `cancel_research`: Stop running research tasks with optional partial saves.
- `resume_research`: Resume failed or interrupted research tasks.
- `estimate_research_cost`: Pre-execution cost and duration estimates.
- `save_research_to_markdown`: Export research to formatted Markdown files.

**File Management Tools (5):**
- `interpret_image`: Analyze one or multiple images (supports up to 3,600 images per request).
- `check_file_status`: Check processing status of uploaded files.
- `list_uploaded_files`: Browse all files in Gemini cloud storage (48-hour retention).
- `get_last_uploaded_video`: Quick access to most recent video upload.
- `delete_uploaded_file`: Delete files from Gemini cloud storage.

**Utility (1):**
- `server_info`: Check server status and connectivity.
