<!--
=============================================================================
SYNC IMPACT REPORT
=============================================================================
Version Change: 1.0.0 → 1.1.0 (MINOR - Two new principles added)

Modified Principles: None (existing principles unchanged)

Added Sections:
- Principle VI: Agent Nesting for Context Preservation
- Principle VII: Wave-Based Parallel Execution
- Agent Orchestration Standards (new section)

Removed Sections: None

Templates Requiring Updates:
- .specify/templates/plan-template.md: ✅ Reviewed - Compatible
- .specify/templates/spec-template.md: ✅ Reviewed - Compatible
- .specify/templates/tasks-template.md: ⚠ PENDING - May benefit from wave-based task grouping guidance

Follow-up TODOs: None
=============================================================================
-->

# Gemini MCP Server Constitution

## Core Principles

### I. FastMCP Decorator-First Design

All server functionality MUST be exposed through FastMCP's `@mcp.tool()` decorator pattern. This ensures:
- Automatic JSON schema generation from Python type hints
- Self-documenting tools via docstrings (docstrings become tool descriptions)
- Type-safe parameter validation handled by the framework
- Zero manual JSON-RPC protocol handling

**Non-negotiable rules:**
- Every public tool MUST use the `@mcp.tool()` decorator
- Every tool function MUST have comprehensive docstrings explaining use cases
- Every tool parameter MUST have type annotations
- Return types MUST be explicitly annotated

**Rationale:** FastMCP 2.0 eliminates boilerplate by inferring schemas from type hints. Violating this principle reintroduces complexity the framework is designed to remove.

### II. Single-File Server Simplicity

The MCP server implementation MUST remain in a single `server.py` file until complexity justifies extraction. This ensures:
- Immediate comprehension of full server capability
- Simple deployment and configuration
- Minimal dependency on internal module structure

**Non-negotiable rules:**
- New tools MUST be added to `server.py` unless they require >100 lines
- Helper functions supporting tools MAY be extracted only when reused by 3+ tools
- Configuration (API keys, model settings) MUST use environment variables via `python-dotenv`

**Rationale:** MCP servers are meant to be lightweight bridges. Over-engineering defeats the purpose of the protocol's simplicity.

### III. Graceful Degradation

The server MUST remain operational even when external services (Gemini API) are unavailable. This ensures:
- Diagnostic capability via `server_info()` tool always available
- Clear error messages indicating the specific failure
- No server crashes from API key misconfiguration or network issues

**Non-negotiable rules:**
- Server initialization MUST NOT raise exceptions for missing API keys
- Every tool MUST check `GEMINI_AVAILABLE` before API calls
- Error responses MUST follow the `🤖 GEMINI RESPONSE:` prefix convention
- Fallback behavior MUST be documented in tool docstrings

**Rationale:** AI assistants calling this server need diagnostic information when things fail, not opaque crashes.

### IV. Comprehensive Tool Documentation

Every tool MUST be self-documenting with docstrings that serve as LLM guidance. This ensures:
- AI clients understand when and how to use each tool
- Parameter semantics are clear without reading source code
- Example use cases guide appropriate tool selection

**Non-negotiable rules:**
- Tool docstrings MUST include: purpose, use cases (bulleted), parameter descriptions, return format
- Docstrings MUST explicitly state what the tool is NOT for (to prevent misuse)
- Temperature and other behavioral parameters MUST document their effect
- Response formats MUST be consistent and prefixed for identification

**Rationale:** The primary consumers of this server are AI assistants who rely entirely on docstrings for tool selection and usage guidance.

### V. Semantic Versioning with Feature Tracking

Version numbers MUST follow semantic versioning (MAJOR.MINOR.PATCH) with clear feature attribution. This ensures:
- Breaking changes are immediately visible (MAJOR bump)
- New tools increment MINOR version
- Bug fixes and documentation updates increment PATCH

**Non-negotiable rules:**
- `__version__` variable MUST exist in `server.py`
- CLAUDE.md MUST document version history with feature attribution
- Version MUST be passed to FastMCP server initialization
- Breaking changes to tool signatures MUST trigger MAJOR version bump

**Rationale:** Clients may depend on specific tool behavior; version tracking ensures compatibility expectations are clear.

### VI. Agent Nesting for Context Preservation

Development tasks MUST leverage multiple specialized agents with nested task delegation to prevent context rot. This ensures:
- Main agent context window remains focused on orchestration
- Specialized agents handle implementation details within their own context
- Long-running tasks do not degrade response quality due to context overflow

**Non-negotiable rules:**
- Complex tasks (3+ distinct operations) MUST spawn specialized subagents
- Research-heavy tasks MUST use dedicated research agents to isolate context consumption
- Agents MUST be nested when subtasks have their own multi-step requirements
- Parent agents MUST summarize subagent results rather than absorbing full context
- Context-intensive operations (file analysis, codebase exploration) MUST be delegated

**Rationale:** Context rot degrades AI performance on long tasks. Isolating work into specialized agents preserves quality and enables parallel execution.

### VII. Wave-Based Parallel Execution

Task execution MUST follow wave-based orchestration to maximize parallelism while respecting dependencies. This ensures:
- Independent tasks execute concurrently (reduced total execution time)
- Dependent tasks execute sequentially (correct ordering)
- File conflicts are prevented through explicit lock management
- Progress checkpoints enable recovery and documentation

**Non-negotiable rules:**
- Every task list MUST be analyzed for dependency relationships
- Tasks MUST be grouped into execution waves where Wave N completes before Wave N+1 begins
- Each task MUST declare file locks (paths it will modify)
- Tasks within the same wave that share file locks MUST be separated into different waves
- Checkpoint protocol MUST be followed between waves:
  - `git-version-manager` agent for commits/staging after each wave
  - `memory-bank-keeper` agent for progress documentation updates

**Wave Execution Schema:**
```json
{
  "execution_plan": {
    "phase_id": "String",
    "waves": [
      {
        "wave_id": "Integer",
        "strategy": "PARALLEL_SWARM | SEQUENTIAL_MERGE",
        "rationale": "Why these tasks are grouped",
        "tasks": [
          {
            "task_id": "String",
            "agent_role": "String (e.g., QA_Engineer, Backend_Dev)",
            "instruction": "Actionable goal",
            "file_locks": ["Array of file paths"],
            "dependencies": ["Array of Task IDs"]
          }
        ],
        "checkpoint_after": {
          "enabled": "Boolean",
          "git_agent": "git-version-manager",
          "memory_bank_agent": "memory-bank-keeper"
        }
      }
    ]
  }
}
```

**Rationale:** Linear task execution wastes time when tasks are independent. Wave-based execution maximizes throughput while preventing race conditions on shared files.

## FastMCP 2.0 Architecture Standards

### Server Initialization
- Use `FastMCP(name, version)` constructor with explicit name and version
- Initialize client connections (e.g., Gemini) at module level with try/except
- Store availability flags as module-level constants (`GEMINI_AVAILABLE`, `GEMINI_ERROR`)

### Tool Pattern
```python
@mcp.tool()
def tool_name(required_param: type, optional_param: type = default) -> str:
    """
    One-line summary of what this tool does.

    Extended description of use cases and when to use this tool.

    Args:
        required_param: Description of this parameter
        optional_param: Description with default behavior noted

    Returns:
        Description of return format
    """
    # Implementation
    return f"🤖 GEMINI RESPONSE:\n\n{result}"
```

### Error Handling Pattern
```python
if not GEMINI_AVAILABLE or not client:
    return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"
```

### File Processing Pattern
- Files <20MB: Process inline with `types.Part.from_bytes()`
- Files >20MB: Upload via File API with `client.files.upload()`
- Always clean up uploaded files after processing

## Agent Orchestration Standards

### Agent Selection Matrix

| Task Type | Primary Agent | Delegation Strategy |
|-----------|--------------|---------------------|
| Code implementation | `frontend-developer`, `python-pro`, `typescript-architect` | Nest QA agents for validation |
| Research/exploration | `Explore`, `search-specialist` | Isolate to prevent context rot |
| Debugging | `debugger`, `error-detective` | Spawn with full error context |
| Code review | `code-reviewer`, `architect-reviewer` | Run post-implementation |
| Git operations | `git-version-manager` | Checkpoint agent between waves |
| Documentation | `memory-bank-keeper` | Checkpoint agent between waves |

### Wave Planning Process

1. **Dependency Analysis**: Identify which tasks depend on outputs of other tasks
2. **File Lock Assignment**: Map each task to files it will create/modify
3. **Wave Grouping**: Group independent tasks (no shared dependencies or file locks) into same wave
4. **Conflict Resolution**: If two tasks share file locks, assign to sequential waves
5. **Checkpoint Insertion**: Add checkpoint after each wave for git commit and memory bank update

### Parallel Launch Pattern
```python
# CORRECT: Independent tasks in single message with multiple tool calls
# Wave 1: Tasks T001, T002, T003 have no dependencies and different file locks
<launch T001 agent in parallel>
<launch T002 agent in parallel>
<launch T003 agent in parallel>
# Wait for all to complete
# Checkpoint: git-version-manager + memory-bank-keeper
# Wave 2: Tasks T004, T005 depend on Wave 1 outputs
```

## Development Workflow

### Adding New Tools
1. Add tool function with `@mcp.tool()` decorator to `server.py`
2. Write comprehensive docstring following the documentation principle
3. Implement with graceful degradation for API unavailability
4. Update `__version__` (MINOR bump for new tools)
5. Document in CLAUDE.md under "Available Tools" section

### Testing
- Use `uv run mcp dev server.py` for development server
- Use MCP Inspector (`npx @modelcontextprotocol/inspector`) for interactive testing
- Validate all tools respond correctly when Gemini is unavailable

### Configuration
- All secrets via `.env` file (never committed)
- Use `generate_config.sh` for client configuration JSON
- Document environment variables in README.md

## Governance

### Constitution Authority
This constitution supersedes all other development practices for this project. When conflicts arise between this document and external guidelines, this constitution takes precedence.

### Amendment Process
1. Propose amendment with rationale
2. Document impact on existing tools and patterns
3. Update version following semantic versioning rules:
   - MAJOR: Principle removal or fundamental redefinition
   - MINOR: New principle or section addition
   - PATCH: Clarifications, wording improvements
4. Update affected documentation (CLAUDE.md, README.md)

### Compliance Review
- All PRs MUST verify compliance with Core Principles
- New tools MUST demonstrate adherence to FastMCP patterns
- Complexity additions MUST be justified against Single-File Simplicity principle
- Multi-task implementations MUST follow Wave-Based Parallel Execution principle

### Guidance Files
- CLAUDE.md: AI assistant development guidance (runtime reference)
- README.md: User-facing setup and usage documentation
- This constitution: Governing principles and standards

**Version**: 1.1.0 | **Ratified**: 2025-12-14 | **Last Amended**: 2025-12-14
