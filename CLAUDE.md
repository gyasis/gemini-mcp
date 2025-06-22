---
noteId: "016020f04f1511f09d6057759d41440e"
tags: []

---

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Gemini MCP (Multi-tool Co-pilot Protocol) Server that enables AI assistants to collaborate with Google's Gemini Pro model. The server implements the MCP protocol to expose Gemini's capabilities as tools that can be called by compatible AI clients.

## Running the Server

The project uses `uv` for Python package management. To run the server:

```bash
uv run python server.py
```

This automatically creates a virtual environment and installs dependencies from `requirements.txt`.

## Configuration

- Create a `.env` file with `GEMINI_API_KEY="YOUR_API_KEY_HERE"`
- The server will exit with an error if the API key is not properly configured
- Use `./generate_config.sh` to generate MCP client configuration JSON

## Architecture

### Core Components

- **server.py**: Main MCP server implementation using official Anthropic MCP SDK
- **FastMCP**: High-level server abstraction that handles JSON-RPC protocol automatically
- **@mcp.tool() decorators**: Automatic tool registration with type-safe schema generation

### Available Tools

The server exposes four main Gemini integration tools:

1. **ask_gemini**: Direct question/answer with configurable temperature
2. **gemini_code_review**: Code review with focus areas (security, performance, etc.)
3. **gemini_brainstorm**: Creative brainstorming with context
4. **gemini_debug**: Error analysis and debugging assistance

### Error Handling

- Graceful degradation when Gemini API is unavailable  
- SDK handles all JSON-RPC error responses automatically
- Fallback `server_info` tool when Gemini is not accessible

## Dependencies

- `mcp>=0.5.0`: Official Anthropic MCP SDK
- `google-generativeai>=0.8.5`: Gemini API client
- `python-dotenv>=0.21.0`: Environment variable management

## Development Notes

- **Version 2.0.0**: Refactored to use official MCP SDK
- Uses FastMCP server for simplified protocol handling
- @mcp.tool() decorators automatically generate JSON schemas from type hints
- No manual JSON-RPC handling required
- Uses Gemini 2.0 Flash model with 8192 max output tokens
- All Gemini responses are prefixed with "🤖 GEMINI RESPONSE:" for clarity
- Temperature defaults: 0.5 (general), 0.2 (code review/debug), 0.7 (brainstorm)

## Code Improvements in v2.0.0

- **Eliminated boilerplate**: ~200 lines of manual JSON-RPC code removed
- **Type safety**: Automatic schema generation from Python type hints
- **Better maintainability**: Each tool is a simple decorated function
- **SDK compliance**: Follows official Anthropic MCP best practices

## Memory Understanding

- My memory resets completely between sessions
- I rely ENTIRELY on my Memory Bank to understand the project and continue work effectively
- I MUST read ALL memory bank files at the start of EVERY task - this is not optional