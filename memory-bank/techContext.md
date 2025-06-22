---
noteId: "530137c04f1d11f09d6057759d41440e"
tags: []

---

# Tech Context - Gemini MCP Server

## Technology Stack

### Core Dependencies
- **Python 3.8+**: Runtime environment
- **mcp (>=0.5.0)**: Official Anthropic MCP SDK
- **google-generativeai (>=0.8.5)**: Gemini API client. **Note**: The `gemini_research` tool requires a more recent version that supports tool usage (grounding).
- **python-dotenv (>=0.21.0)**: Environment variable management

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

### 2. MCP SDK Version Strategy
**Decision**: Use official Anthropic MCP SDK (>=0.5.0)
**Benefits**:
- Protocol compliance guaranteed
- Reduced maintenance burden
- Automatic schema generation
- Future compatibility

**Migration Impact**:
- v2.0.0: Complete rewrite from custom JSON-RPC
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

### 4. Error Handling Philosophy
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
└── memory-bank/      # Project documentation
```

### Code Organization
- **Single Module**: All code in `server.py` for simplicity
- **Tool Functions**: Decorated functions for MCP tools
- **Configuration**: Environment-based with validation
- **Error Handling**: Consistent patterns across tools

### Development Workflow
1. **Setup**: `uv sync` installs all dependencies
2. **Run**: `uv run python server.py` starts server
3. **Test**: Manual testing with MCP clients
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

## Testing Strategy (Future)

### Unit Testing
- Test individual tool functions
- Mock Gemini API responses
- Validate error handling

### Integration Testing
- Full MCP client/server interaction
- Configuration generation testing
- Error scenario validation

### Development Tools
- **Linting**: Could add ruff or flake8
- **Type Checking**: Could add mypy
- **Testing**: Could add pytest
- **CI/CD**: Could add GitHub Actions

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