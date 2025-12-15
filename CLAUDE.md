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

The server exposes six main Gemini integration tools:

1. **ask_gemini**: Direct question/answer with configurable temperature
2. **gemini_code_review**: Code review with focus areas (security, performance, etc.)
3. **gemini_brainstorm**: Creative brainstorming with context
4. **gemini_debug**: Error analysis and debugging assistance
5. **gemini_research**: Research with Google Search grounding
6. **watch_video**: Analyze YouTube videos (by URL) or local video files

### Deep Research Tools (v3.7.0)

Six specialized tools for long-running research with SQLite persistence:

1. **start_deep_research**: Hybrid sync-to-async research execution
   - Tries sync for 30s, auto-switches to async for complex queries
   - Returns task_id for tracking, optional desktop notifications
2. **check_research_status**: Monitor async task progress
   - Real-time progress % and current action
   - Works for both sync-completed and async tasks
3. **get_research_results**: Zero-cost result retrieval from SQLite
   - Pulls completed reports with sources and metadata
   - No additional API calls needed
4. **cancel_research**: Stop running tasks with optional partial saves
   - Graceful cancellation with cleanup
   - Option to save partial results before stopping
5. **estimate_research_cost**: Pre-execution cost analysis
   - Query complexity classification (simple/medium/complex)
   - Token and USD estimates before committing
6. **save_research_to_markdown**: Export results to formatted Markdown files
   - Jinja2-templated reports with sources and metadata
   - Organized by month in ./research_reports/

### Error Handling

- Graceful degradation when Gemini API is unavailable  
- SDK handles all JSON-RPC error responses automatically
- Fallback `server_info` tool when Gemini is not accessible

## Dependencies

- `fastmcp>=2.0.0`: FastMCP server abstraction
- `google-genai>=0.3.0`: Unified Google Gen AI SDK
- `python-dotenv>=1.1.0`: Environment variable management
- `notify-py>=0.3.0`: Cross-platform desktop notifications
- `jinja2>=3.1.0`: Markdown report templating

## Development Notes

- **Version 3.7.0**: Added Gemini Deep Research tools with SQLite persistence and asyncio
- **Version 3.6.0**: Added file management system for Gemini storage
- **Version 3.1.0**: Added watch_video tool for video analysis
- **Version 3.0.0**: Migrated to unified Google Gen AI SDK
- **Version 2.0.0**: Refactored to use official MCP SDK
- Uses FastMCP server for simplified protocol handling
- @mcp.tool() decorators automatically generate JSON schemas from type hints
- No manual JSON-RPC handling required
- Uses Gemini 2.0 Flash model with 8192 max output tokens
- All Gemini responses are prefixed with "🤖 GEMINI RESPONSE:" for clarity
- Temperature defaults: 0.5 (general), 0.2 (code review/debug), 0.7 (brainstorm)
- Video processing: YouTube URLs sent directly, local files <20MB inline, >20MB use File API

### Deep Research Architecture (v3.7.0)

- **deep_research/**: Package with SQLite state, async background tasks, and notifications
- **StateManager**: WAL-mode SQLite with retry logic for concurrent access
- **BackgroundTaskManager**: asyncio task scheduling and cancellation
- **DeepResearchEngine**: Hybrid sync-to-async with 30s timeout pattern
- **CostEstimator**: Pre-execution cost analysis via query complexity
- **MarkdownStorage**: Jinja2-templated report export to ./research_reports/
- **NativeNotifier**: Cross-platform desktop notifications (macOS/Windows/Linux)
- Recovery: Incomplete tasks resumed on server startup via interaction_id

## Code Improvements in v2.0.0

- **Eliminated boilerplate**: ~200 lines of manual JSON-RPC code removed
- **Type safety**: Automatic schema generation from Python type hints
- **Better maintainability**: Each tool is a simple decorated function
- **SDK compliance**: Follows official Anthropic MCP best practices

## Memory Understanding

- My memory resets completely between sessions
- I rely ENTIRELY on my Memory Bank to understand the project and continue work effectively
- I MUST read ALL memory bank files at the start of EVERY task - this is not optional