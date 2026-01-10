---
noteId: "530137c04f1d11f09d6057759d41440e"
tags: []

---

# Tech Context - Gemini MCP Server

## Technology Stack

### Core Dependencies
- **Python 3.12+**: Runtime environment (upgraded for modern features)
- **fastmcp (2.14.2)**: FastMCP server framework with native task support (upgraded from 2.13.0)
- **google-genai (>=0.3.0)**: Modern unified Google Gen AI SDK (replaces deprecated google-generativeai)
- **python-dotenv (>=0.21.0)**: Environment variable management
- **grpcio (>=1.62.0,<1.70.0)**: gRPC runtime (version constrained for compatibility)
- **grpcio-status (>=1.62.0,<1.70.0)**: gRPC status handling
- **pillow (>=10.0.0)**: Image processing support for video thumbnails

### Deep Research System Dependencies (v3.6.0+)
- **notify-py (>=0.3.42)**: Cross-platform desktop notifications (optional, with fallback)
- **Jinja2 (>=3.1.0)**: Markdown report template rendering
- **pytest (>=7.0.0)**: Testing framework for integration tests
- **sqlite3**: SQLite database (Python stdlib - no external dependency)
- **asyncio**: Asynchronous task management (Python stdlib - no external dependency)

### Development Tools
- **uv**: Modern Python package manager and runtime
- **pyproject.toml**: Project metadata and dependency specification
- **requirements.txt**: Legacy compatibility (auto-generated)

## Development Setup

### Initial Setup
```bash
# 1. Clone repository
git clone <repository-url>
cd claude_code-gemini-mcp

# 2. Install dependencies (uv automatically creates venv)
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env to add GEMINI_API_KEY

# 4. Run server
uv run python server.py
```

### Configuration Management
- **Environment File**: `.env` for API keys
- **Config Generation**: `./generate_config.sh` for MCP client setup
- **Project Config**: `pyproject.toml` for Python metadata

### Package Management Strategy
**Primary**: `uv` for development and deployment
- Fast dependency resolution
- Automatic virtual environment management
- Lock file for reproducible builds (`uv.lock`)

**Fallback**: Traditional pip + requirements.txt
- Generated from pyproject.toml for compatibility
- Supports environments without uv

## Technical Constraints

### Python Version Support
- **Minimum**: Python 3.8
- **Recommended**: Python 3.11+
- **Compatibility**: Must work across major Python versions

### Dependency Constraints
- **MCP SDK**: Pin to major version (0.x.x)
- **Gemini Client**: Pin to compatible version (0.8.x)
- **Minimal Dependencies**: Avoid heavy frameworks

### Runtime Requirements
- **Memory**: Minimal (< 50MB typical usage)
- **CPU**: Low usage (I/O bound operations)
- **Network**: Outbound HTTPS to Gemini API required

## Architecture Decisions

### 1. Package Manager Choice: uv
**Rationale**:
- Modern, fast dependency resolution
- Built-in virtual environment management
- Compatible with existing Python ecosystem
- Future-proof development experience

**Trade-offs**:
- Requires uv installation
- Newer tool (less widespread adoption)
- Dual maintenance (uv.lock + requirements.txt)

### 2. FastMCP Version Strategy (v3.8.0)
**Decision**: Upgrade to FastMCP 2.14.2 for native task support
**Benefits**:
- Protocol compliance with MCP SEP-1686 (task specification)
- 98% token savings vs manual polling (50-100k → 1-2k tokens)
- Automatic progress notifications via Progress dependency injection
- Docket integration for background task management
- Simpler code (~100 lines removed)

**Migration Impact**:
- v3.8.0: Upgraded from FastMCP 2.13.0 → 2.14.2
- Removed BackgroundTaskManager (now redundant)
- Added Progress dependency injection to start_deep_research
- Created progress_bridge for engine callback integration
- Breaking changes from FastMCP 2.14.2:
  - Memory footprint increased 30% (Docket always loaded)
  - Lifespan semantics changed (server vs session lifecycle)
  - Some deprecated APIs removed (BearerAuthProvider, etc.)
  - No impact on our codebase - only affects unused features

**Previous Migration (v2.0.0)**:
- Complete rewrite from custom JSON-RPC to official MCP SDK
- Eliminated ~200 lines of boilerplate
- Breaking change requiring client reconfiguration

### 3. Gemini Model Selection
**Current**: `gemini-2.0-flash-exp` (for general tools)
**Rationale**:
- Latest experimental features
- Good performance/cost balance
- 8192 token output limit
- Multimodal capabilities

**Research Model**: `gemini-1.5-flash` (for `gemini_research` tool)
**Rationale**:
- Optimized for tool use and grounding with Google Search.
- Provides more accurate, up-to-date answers for research tasks.

**Fallback Strategy**: Could switch to stable models if needed

### 4. Video Processing Architecture (watch_video tool)
**YouTube URL Support**:
- Direct URL passing to Gemini (no downloading)
- Supports public YouTube videos only
- Time range queries via prompt (e.g., "from 1:00 to 1:30")

**Local File Handling**:
- Files <20MB: Sent inline as base64
- Files >20MB: Uploaded via File API, then deleted
- Supported formats: mp4, mpeg, mov, avi, flv, mpg, webm, wmv, 3gpp
- Automatic MIME type detection

**Model Selection**: `gemini-2.0-flash-001` for video analysis
- Optimized for multimodal tasks
- Supports up to 2 hours of video (standard resolution)
- Can process 6 hours at low resolution

### 5. Image Processing Architecture (interpret_image tool - v3.3.0)
**Three Input Methods Supported**:

1. **Local File Paths** (original functionality):
   - Files <20MB: Sent inline using `types.Part.from_bytes`
   - Files >20MB: Uploaded via File API using `types.Part.from_uri`
   - Automatic MIME type detection from file extension
   - Supported formats: jpg, jpeg, png, gif, webp, bmp

2. **Image URLs** (NEW in v3.3.0):
   - Direct HTTP/HTTPS image URLs
   - URL detection via `is_image_url()` helper function
   - Images downloaded and processed inline
   - No size limits (downloaded then processed like local files)
   - Automatic MIME type detection with fallback to image/jpeg

3. **Base64 Data URIs** (NEW in v3.3.0):
   - Format: `data:image/{type};base64,{encoded_data}`
   - Detection via `is_base64_image()` helper function
   - Base64 data decoded and processed inline
   - MIME type extracted from data URI or defaults to image/jpeg

**Implementation Pattern**:
```python
# URL detection
def is_image_url(path: str) -> bool:
    return path.startswith(('http://', 'https://'))

# Base64 detection
def is_base64_image(path: str) -> bool:
    return path.startswith('data:image/')
```

**Processing Flow**:
1. Check input type (URL, base64, or file path)
2. Download/decode if needed
3. Determine MIME type
4. Send inline (<20MB) or via File API (>20MB)
5. Return Gemini's analysis

**Model Selection**: `gemini-2.0-flash-exp` for image interpretation
- Optimized for vision tasks
- Supports high-resolution images
- Fast processing for real-time use cases

### 6. FastMCP Task Protocol (v3.8.0)
**Protocol**: MCP SEP-1686 - Native Task Support
**Implementation**: FastMCP 2.14.2 with Docket background task integration

**Key Technical Features**:

1. **Progress Dependency Injection**:
   - FastMCP automatically injects `Progress` parameter into task tools
   - Tool decorated with `@mcp.tool(task=True)` receives Progress object
   - No manual progress tracking infrastructure needed

2. **Progress Bridge Pattern**:
   - Converts DeepResearchEngine callbacks to FastMCP Progress API
   - Uses `asyncio.create_task()` for non-blocking progress updates
   - Prevents blocking main execution thread during progress reporting

3. **Token Economics**:
   - **Manual Polling (Before)**: 50-100k tokens per research session
     - Client polls check_research_status every 10-30 seconds
     - Each poll: 2-4k tokens (request + response + context)
     - 10-30 minute research: 30-100 polls required
   - **Task Protocol (After)**: 1-2k tokens per research session
     - Single start_deep_research invocation: ~1k tokens
     - Protocol-native notifications: zero token cost
     - Result retrieval from SQLite: ~1k tokens
   - **Net Savings**: 98% token reduction

4. **Background Task Management**:
   - FastMCP's task wrapper handles async execution automatically
   - Docket (FastMCP's background task manager) manages task lifecycle
   - Automatic cleanup on completion, failure, or timeout
   - No manual BackgroundTaskManager needed (removed in v3.8.0)

5. **Protocol Flow**:
   ```
   Client → start_deep_research(task=True) → FastMCP Task Wrapper
                                           ↓
                                    Background Execution
                                           ↓
                           Progress Updates (Protocol Notifications)
                                           ↓
                                    Completion Notification
                                           ↓
   Client ← get_research_results ← SQLite Cache (zero tokens)
   ```

**Implementation Details**:
- Only affects `start_deep_research` tool (1 of 13 tools)
- All other 18 tools unchanged
- SQLite state management preserved for crash recovery
- Custom polling logic preserved for error scenarios
- Backward compatible - old tools continue to work

### 7. Error Handling Philosophy
**Approach**: Graceful degradation
- Server continues running even if Gemini unavailable
- Clear error messages without exposing internals
- Fallback tools for basic functionality

## Development Patterns

### Project Structure
```
claude_code-gemini-mcp/
├── server.py              # Main MCP server
├── main.py               # Alternative entry point
├── requirements.txt      # Pip compatibility
├── pyproject.toml       # Project configuration
├── uv.lock             # Dependency lock file
├── generate_config.sh  # Client configuration helper
├── .env               # Environment variables (gitignored)
├── CLAUDE.md         # Development documentation
├── memory-bank/      # Project documentation
├── deep_research/    # Deep research module (v3.6.0+)
│   ├── __init__.py        # Data models
│   ├── state_manager.py   # SQLite persistence
│   ├── notification.py    # Cross-platform notifications
│   ├── background.py      # asyncio task manager
│   ├── engine.py          # DeepResearchEngine
│   ├── cost_estimator.py  # Cost estimation (stub)
│   └── storage.py         # Markdown storage (stub)
├── tests/            # Test infrastructure (v3.6.0+)
│   ├── __init__.py
│   └── integration/
│       ├── __init__.py
│       └── test_deep_research_flow.py
└── research_reports/ # Research output directory
```

### Code Organization
- **Main Server**: Core MCP tools in `server.py`
- **Deep Research Module**: Modular architecture in `deep_research/` package
- **Tool Functions**: Decorated functions for MCP tools
- **Configuration**: Environment-based with validation
- **Error Handling**: Consistent patterns across tools
- **Testing**: Integration tests in `tests/integration/` directory

### Development Workflow
1. **Setup**: `uv sync` installs all dependencies
2. **Run**: `uv run python server.py` starts server
3. **Test**:
   - Manual testing with MCP clients
   - Integration tests: `pytest tests/integration/`
   - Unit tests: `pytest tests/` (when available)
4. **Deploy**: Copy files + run setup script

## Deployment Considerations

### Environment Requirements
- Python 3.8+ runtime
- Internet access for Gemini API
- Environment variable for API key
- MCP client configured to connect

### Scaling Limitations
- **Single Process**: No multi-threading/async
- **Single API Key**: No multi-tenancy
- **Memory Bound**: No persistence or caching
- **Local Only**: No remote deployment patterns

### Security Considerations
- **API Key Storage**: Environment variables only
- **No Logging**: Avoid sensitive data exposure
- **Input Validation**: Rely on MCP SDK
- **Network**: Outbound only (no listening ports)

## Testing Strategy

### Integration Testing (v3.6.0+)
- **Framework**: pytest
- **Coverage**: Deep research flow testing in `tests/integration/test_deep_research_flow.py`
- **Test Cases**:
  - Sync completion path (research completes within 30s)
  - Async switch after timeout (research takes >30s)
  - State persistence and recovery (server restart scenarios)
  - Result retrieval (get_research_results validation)
- **Mocking**: Mock Gemini API for reproducible tests
- **Execution**: `pytest tests/integration/`

### Unit Testing (Future)
- Test individual tool functions
- Mock Gemini API responses for core tools
- Validate error handling
- Deep research module unit tests

### End-to-End Testing (Future)
- Full MCP client/server interaction
- Configuration generation testing
- Error scenario validation
- Multi-tool workflow testing

### Development Tools
- **Testing**: pytest (implemented for integration tests)
- **Linting**: Could add ruff or flake8 (future)
- **Type Checking**: Could add mypy (future)
- **CI/CD**: Could add GitHub Actions (future)

## Performance Characteristics

### Expected Performance
- **Startup Time**: < 2 seconds
- **Response Time**: 2-10 seconds (depends on Gemini)
- **Memory Usage**: < 50MB steady state
- **Concurrent Requests**: Limited (synchronous handling)

### Bottlenecks
- **Network**: Gemini API response time
- **CPU**: Minimal (mostly I/O wait)
- **Memory**: Text processing only

### Optimization Opportunities
- **Caching**: Response caching for repeated queries
- **Async**: Asynchronous request handling
- **Pooling**: Connection pooling for Gemini API
- **Streaming**: Stream responses for long outputs