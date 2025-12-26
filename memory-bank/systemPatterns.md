---
noteId: "3935fa104f1d11f09d6057759d41440e"
tags: []

---

# System Patterns - Gemini MCP Server

## Architecture Overview

### High-Level Design
```
┌─────────────────┐    MCP Protocol    ┌─────────────────┐    Gemini API    ┌─────────────────┐
│   MCP Client    │◄─────────────────►│   MCP Server    │◄───────────────►│   Gemini Pro    │
│  (Claude Code)  │     JSON-RPC      │  (This Server)  │      HTTPS       │     Model       │
└─────────────────┘                   └─────────────────┘                  └─────────────────┘
```

### Core Components

#### 1. FastMCP Server (Entry Point)
- **Purpose**: Handles MCP protocol communication
- **Pattern**: Declarative tool registration with decorators
- **Key Feature**: Automatic JSON-RPC handling

#### 2. Tool Registration Pattern
```python
@mcp.tool()
def tool_name(param: str) -> str:
    """Tool description"""
    # Implementation
    return result
```
- **Benefit**: Type-safe schema generation
- **Pattern**: Function signature → JSON schema
- **Validation**: Automatic parameter validation

#### 3. Gemini Client Wrapper
- **Initialization**: One-time setup with API key
- **Error Handling**: Graceful degradation patterns
- **Response Format**: Consistent "🤖 GEMINI RESPONSE:" prefix

## Key Technical Decisions

### 1. Official MCP SDK Adoption (v2.0.0)
**Decision**: Migrate from custom JSON-RPC to official Anthropic MCP SDK
**Rationale**: 
- Eliminates ~200 lines of boilerplate code
- Ensures protocol compliance
- Automatic schema generation
- Better maintainability

**Impact**: 
- Simplified codebase
- Reduced maintenance burden
- Future-proof compatibility

### 2. Decorator-Based Tool Definition
**Pattern**:
```python
@mcp.tool()
def ask_gemini(question: str, temperature: float = 0.5) -> str:
```

**Benefits**:
- Clear separation of concerns
- Automatic parameter validation
- Self-documenting code
- Type safety

### 3. Gemini Model Selection
**Decision**: Use `gemini-2.0-flash-exp` model
**Rationale**:
- Latest capabilities
- Good balance of speed and quality
- 8192 token output limit
- Cost-effective for general use

### 4. Temperature Strategy
**Pattern**: Tool-specific temperature defaults
- `ask_gemini`: 0.5 (balanced)
- `gemini_code_review`: 0.2 (conservative/analytical)  
- `gemini_brainstorm`: 0.7 (creative)
- `gemini_debug`: 0.2 (systematic/precise)

## Design Patterns in Use

### 1. Configuration Pattern
```python
# Environment-based configuration
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Graceful failure with clear messaging
```

**Benefits**:
- Security (no hardcoded keys)
- Environment flexibility
- Clear error messaging

### 2. Error Handling Pattern
```python
try:
    response = model.generate_content(...)
    return f"🤖 GEMINI RESPONSE:\n{response.text}"
except Exception as e:
    return f"Error: {str(e)}"
```

**Features**:
- Graceful degradation
- User-friendly error messages
- Consistent response format

### 3. Tool Composition Pattern
Each tool follows the same structure:
1. **Input Validation**: Automatic via type hints
2. **Context Building**: Format prompts appropriately
3. **Gemini Interaction**: Single API call pattern
4. **Response Formatting**: Consistent prefix and structure

### 4. Fallback Pattern
```python
def get_server_info() -> str:
    """Fallback tool when Gemini unavailable"""
```

**Purpose**: Provide basic functionality even when main service fails

## Component Relationships

### 1. Server → Tools
- **Relationship**: One-to-many registration
- **Pattern**: Decorator-based discovery
- **Lifecycle**: Registration at import time

### 2. Tools → Gemini Client
- **Relationship**: Shared client instance
- **Pattern**: Dependency injection via global
- **Error Handling**: Individual tool responsibility

### 3. Client → Server
- **Protocol**: MCP over JSON-RPC
- **Transport**: stdio (standard for MCP)
- **Discovery**: Automatic tool enumeration

## Scaling Patterns

### Current Limitations
- Single Gemini API key (no multi-tenancy)
- Synchronous request handling
- In-memory only (no persistence)

### Future Extension Points
- **Multi-Model Support**: Additional model endpoints
- **Request Queuing**: Handle concurrent requests
- **Caching Layer**: Response caching for efficiency
- **Authentication**: Multi-user API key management

## Security Patterns

### 1. API Key Management
- Environment variable only
- No logging of sensitive data
- Early validation and clear error messages

### 2. Input Sanitization
- Automatic via MCP SDK validation
- Type checking prevents injection
- Length limits via Gemini API

### 3. Output Safety
- No raw exception exposure
- Consistent error message format
- No sensitive information in responses

## Testing Strategy (Future)
- **Unit Tests**: Individual tool functions
- **Integration Tests**: Full MCP client interaction
- **Error Tests**: Gemini API failure scenarios
- **Security Tests**: Input validation and sanitization

### 5. Grounded Generation Pattern
**Pattern**:
```python
@mcp.tool()
def gemini_research(topic: str) -> str:
```
- **Purpose**: Provide up-to-date, factual answers by grounding the model with Google Search results.
- **Mechanism**: Utilizes the `gemini-1.5-flash` model with a `GoogleSearch` tool.
- **Benefit**: Reduces hallucinations and provides more accurate information for research-oriented queries.
- **Use Case**: Ideal for questions about current events, technical topics, or anything requiring real-time data.

### 6. Deep Research System Architecture (Feature 001 - v3.6.0+)

**Pattern**: Hybrid sync-to-async execution with SQLite persistence

**Implementation**:
```python
# Wave 1-2 Foundation Components
deep_research/
├── __init__.py           # Data models (TaskStatus, Source, TokenUsage, etc.)
├── state_manager.py      # SQLite + WAL mode persistence
├── notification.py       # Cross-platform desktop notifications
├── background.py         # asyncio task lifecycle management
├── engine.py            # DeepResearchEngine (Wave 3)
├── cost_estimator.py    # CostEstimator (Wave 6)
└── storage.py           # MarkdownStorage with Jinja2 (Wave 8)
```

**Key Architectural Decisions**:
- **Zero External Dependencies**: Core functionality uses only Python stdlib (SQLite, asyncio)
- **WAL Mode**: Write-Ahead Logging enables concurrent reads during background execution
- **Hybrid Execution**: 30-second sync timeout before switching to async background task
- **Crash Recovery**: SQLite persistence enables server restart without losing state
- **Notification Fallback Chain**: notify-py → CLI tools (notify-send/osascript) → console logging

**Data Flow**:
1. User starts research via `start_deep_research` tool
2. System attempts sync completion (30s timeout)
3. If timeout: save state to SQLite, spawn background asyncio task
4. Background task polls Gemini Deep Research API, updates progress in SQLite
5. On completion: save results to SQLite, send desktop notification
6. User retrieves results via `get_research_results` (zero token cost - reads from SQLite)

**State Management**:
- `research_tasks` table: task metadata, status, progress, tokens, cost
- `research_results` table: completed reports, sources, metadata
- Automatic recovery on server restart for incomplete tasks

**Implementation Status**: Wave 1-2 complete (8/30 tasks), Wave 3 pending API research

## Gemini Interaction Modes

These modes define how the primary assistant collaborates with Gemini.

### 1. Default Mode (Assistant-Led)
- **Trigger**: Standard operation; no specific mode is invoked.
- **Rule**: Gemini is only used when explicitly requested by the user. The primary assistant leads the interaction and is responsible for all responses unless it decides to delegate a specific task to Gemini.

### 2. Paired Programming Mode (Collaborative)
- **Trigger**: User invokes "Paired Programming Mode".
- **Rule**: The primary assistant and Gemini work together on a task. The primary assistant can leverage its specialized tools, while Gemini provides knowledge, alternative perspectives, and code suggestions. This is a partnership to solve complex problems.

### 3. Gemini Suggest Mode (Validation)
- **Trigger**: User invokes "Gemini Suggest Mode".
- **Rule**: The primary assistant first attempts to solve a problem on its own. After arriving at a solution, it can ask Gemini for suggestions. Gemini's suggestions are treated as a "second opinion" or a validation mechanism, particularly for fixing problems the assistant believes it has already solved.