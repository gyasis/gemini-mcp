# SpecKit Plan Stage - Research & Brainstorm Protocol

## 🎯 Purpose
**FOR AI ASSISTANTS:** This guide provides the MANDATORY research protocol when running `/speckit.plan`. Follow this protocol step-by-step before creating any technical plan.

### 🚀 Key Features:
- ⚡ **Parallel Execution** - Run tool calls in batches for 75%+ speed improvement
- 📅 **Date-Aware Research** - Always check current date, use current year in queries
- 🔧 **Multi-Tool Integration** - Gemini Research + Context7 + DeepLake RAG + Gemini Brainstorm
- 📊 **Efficient Batching** - 5 parallel batches complete in ~10-12 seconds vs ~40-50 sequential
- ✅ **Research-Backed Plans** - All technical decisions justified with current sources

---

## 🤖 AI Assistant Instructions

When the user runs `/speckit.plan`, you MUST:
1. **Check current date first** - Your knowledge is outdated
2. **Follow this research protocol completely** - All phases required
3. **Run tools in PARALLEL batches** - NOT one-by-one (75%+ faster)
4. **Use all three tool types** - Gemini Research, Context7, DeepLake RAG, and Gemini Brainstorm
5. **Document all findings** - Create plan.md with research justification

**Do not skip any phase. Do not guess. Do not run tools sequentially. Always batch parallel operations.**

### Quick Execution Summary:
```
Step 0: Check current date (use system date, not knowledge base)
         ↓
Batch 1: All gemini_research [5-10 queries] → Parallel
Batch 2: All resolve-library-id [3-5 IDs] → Parallel
Batch 3: All get-library-docs [3-5 docs] → Parallel (after Batch 2)
Batch 4: All retrieve_context [2-4 tutorials] → Parallel
Batch 5: All gemini_brainstorm [2-3 sessions] → Parallel (if independent)
         ↓
Document: Create plan.md with all research sources

Total time: ~10-12 seconds (vs ~40-50 seconds sequential)
```

---

## ⚡ CRITICAL: Run Tool Calls in PARALLEL for Efficiency

**IMPORTANT FOR AI ASSISTANTS:** When executing research, you MUST batch/parallelize tool calls whenever possible. Running tools sequentially is wasteful and slow.

### Why Parallel Execution Matters:
- ✅ **Faster execution** - Multiple tools run simultaneously
- ✅ **Better token efficiency** - Reduces round-trips
- ✅ **Lower latency** - User gets results faster
- ✅ **Optimal resource usage** - Multiple agents working together

### How to Run Tools in Parallel:

**❌ WRONG - Sequential (Slow & Wasteful):**
```bash
# Don't do this - one at a time
gemini_research: "FastAPI best practices 2024"
# Wait for result...
gemini_research: "WebSocket security 2024"
# Wait for result...
gemini_research: "Redis vs RabbitMQ comparison"
# Wait for result...
```

**✅ CORRECT - Parallel (Fast & Efficient):**
```bash
# Do this - batch all research queries together
[
  gemini_research: "FastAPI best practices 2024",
  gemini_research: "WebSocket security 2024",
  gemini_research: "Redis vs RabbitMQ comparison",
  gemini_research: "PostgreSQL connection pooling Python",
  gemini_research: "Docker deployment best practices 2024"
]
# All execute in parallel, results come back together
```

### Parallel Execution by Phase:

#### **PHASE 1A - Batch ALL Gemini Research Queries:**
```bash
# Execute 5-10 research queries in ONE parallel batch
BATCH 1 (Gemini Research):
[
  gemini_research: "problem domain best practices 2024",
  gemini_research: "technology A vs technology B 2024",
  gemini_research: "security considerations 2024",
  gemini_research: "scalability patterns",
  gemini_research: "integration best practices 2024"
]
```

#### **PHASE 1B - Batch ALL Context7 Queries:**
```bash
# First batch: Resolve all library IDs in parallel
BATCH 2 (Context7 Resolve):
[
  resolve-library-id: "fastapi",
  resolve-library-id: "sqlalchemy",
  resolve-library-id: "redis-py",
  resolve-library-id: "pydantic"
]

# Second batch: Get all library docs in parallel
BATCH 3 (Context7 Docs):
[
  get-library-docs: "fastapi",
  get-library-docs: "sqlalchemy",
  get-library-docs: "redis-py",
  get-library-docs: "pydantic"
]
```

#### **PHASE 1C - Batch ALL DeepLake RAG Queries:**
```bash
# Execute all tutorial retrievals in parallel
BATCH 4 (DeepLake RAG):
[
  retrieve_context: "FastAPI implementation tutorial",
  retrieve_context: "SQLAlchemy async patterns",
  retrieve_context: "WebSocket authentication examples"
]
```

#### **PHASE 2 - Brainstorm Sessions (Can be Parallel):**
```bash
# If brainstorms are independent, run in parallel
BATCH 5 (Gemini Brainstorm):
[
  gemini_brainstorm(topic: "Architecture options", context: "..."),
  gemini_brainstorm(topic: "Tech stack combinations", context: "..."),
  gemini_brainstorm(topic: "Edge case handling", context: "...")
]

# Note: Only parallelize if contexts don't depend on each other
```

### Rules for Parallel Execution:

1. **✅ CAN PARALLELIZE** - Independent queries:
   - Multiple gemini_research queries (no dependencies)
   - Multiple resolve-library-id calls (independent libraries)
   - Multiple get-library-docs calls (after resolving IDs)
   - Multiple retrieve_context queries (independent topics)
   - Multiple gemini_brainstorm sessions (if contexts are independent)

2. **❌ CANNOT PARALLELIZE** - Sequential dependencies:
   - resolve-library-id MUST complete before get-library-docs
   - Phase 1 (research) MUST complete before Phase 2 (brainstorm)
   - Must have research results before brainstorming with context

3. **🎯 OPTIMAL BATCHING STRATEGY:**
   ```
   BATCH 1: All gemini_research (5-10 queries) → Parallel
   BATCH 2: All resolve-library-id (3-5 libraries) → Parallel
   BATCH 3: All get-library-docs (3-5 docs) → Parallel (after BATCH 2)
   BATCH 4: All retrieve_context (2-4 tutorials) → Parallel
   BATCH 5: All gemini_brainstorm (2-3 sessions) → Parallel if independent
   ```

### Example: Efficient Parallel Execution

**For a REST API project, execute in 5 batches:**

```bash
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BATCH 1: Gemini Research (Parallel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[
  gemini_research: "REST API authentication best practices 2024",
  gemini_research: "FastAPI vs Flask vs Django 2024",
  gemini_research: "PostgreSQL connection pooling Python",
  gemini_research: "REST API rate limiting strategies 2024",
  gemini_research: "Docker deployment FastAPI 2024",
  gemini_research: "API security vulnerabilities 2024",
  gemini_research: "async Python patterns 2024"
]
⏱️ Executes in ~2-3 seconds (vs 14-21 seconds sequential)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BATCH 2: Context7 Resolve IDs (Parallel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[
  resolve-library-id: "fastapi",
  resolve-library-id: "sqlalchemy",
  resolve-library-id: "pydantic",
  resolve-library-id: "redis-py"
]
⏱️ Executes in ~1 second (vs 4 seconds sequential)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BATCH 3: Context7 Get Docs (Parallel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[
  get-library-docs: "fastapi",
  get-library-docs: "sqlalchemy",
  get-library-docs: "pydantic",
  get-library-docs: "redis-py"
]
⏱️ Executes in ~2 seconds (vs 8 seconds sequential)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BATCH 4: DeepLake RAG (Parallel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[
  retrieve_context: "FastAPI authentication tutorial",
  retrieve_context: "SQLAlchemy async session management",
  retrieve_context: "Redis pub/sub patterns"
]
⏱️ Executes in ~1-2 seconds (vs 3-6 seconds sequential)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BATCH 5: Gemini Brainstorm (Parallel if independent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[
  gemini_brainstorm(topic: "Authentication architecture", context: "..."),
  gemini_brainstorm(topic: "Database schema design", context: "..."),
  gemini_brainstorm(topic: "Scaling strategy", context: "...")
]
⏱️ Executes in ~3-4 seconds (vs 9-12 seconds sequential)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL TIME:
Parallel: ~9-12 seconds
Sequential: ~38-51 seconds
SAVINGS: 75%+ faster! ⚡
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 📊 Visual Comparison: Sequential vs Parallel

```
❌ SEQUENTIAL EXECUTION (Slow):
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ Query 1 │→ │ Query 2 │→ │ Query 3 │→ │ Query 4 │→ │ Query 5 │
└─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘
   3 sec        3 sec        3 sec        3 sec        3 sec
                        Total: ~15 seconds

✅ PARALLEL EXECUTION (Fast):
┌─────────┐
│ Query 1 │
├─────────┤
│ Query 2 │
├─────────┤  All execute
│ Query 3 │  simultaneously
├─────────┤
│ Query 4 │
├─────────┤
│ Query 5 │
└─────────┘
   Total: ~3 seconds (5x faster!)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For a typical /speckit.plan with 5 batches:

Sequential:  ████████████████████████████████████████ 40-50 sec
Parallel:    ██████████ 10-12 sec

TOKEN EFFICIENCY: Same # of tokens, 75% less time!
USER EXPERIENCE: Near-instant research completion
COST: Same API costs, dramatically better performance
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 🎯 AI Assistant Best Practices:

1. **Always identify batchable operations** - Look for independent queries
2. **Group by tool type** - Batch all gemini_research together, all Context7 together
3. **Respect dependencies** - Don't parallelize if one depends on another's result
4. **Maximize batch size** - More parallel = better efficiency
5. **Show batch structure** - Make it clear to user what's running in parallel

### ⚠️ Common Efficiency Mistakes:

| ❌ Inefficient | ✅ Efficient |
|---------------|-------------|
| Run 1 research query, wait, run next | Batch all 5-10 research queries together |
| Resolve library ID, get docs, resolve next ID | Batch all resolve-library-id, THEN batch all get-library-docs |
| Sequential brainstorm sessions | Parallel brainstorm if contexts are independent |
| Wait for each tool call result | Use async/parallel execution wherever possible |

---

## ⚠️ CRITICAL: Check Current Date FIRST

**BEFORE doing ANY research, you MUST determine the current date.**

### Why This Matters:
- ❌ Your knowledge base has a cutoff date and is **NOT current**
- ❌ You cannot assume what year or month it is
- ❌ Technology changes rapidly - 2023 advice may be obsolete in 2024
- ✅ You MUST check the system date to research the most recent information

### How to Check the Date:

**Option 1: Ask the system**
```bash
# In terminal or via tool
date +"%Y-%m-%d"
# Returns: 2024-12-14 (example)
```

**Option 2: Check user info**
The user info header contains the current date. Always reference it.

### Use the Current Date in Research:

Once you know the current date (e.g., December 2024):

```bash
# ✅ CORRECT - Use current year in research
gemini_research: "FastAPI best practices 2024"
gemini_research: "WebSocket security vulnerabilities 2024"
gemini_research: "Python async patterns December 2024"

# ❌ WRONG - Don't use outdated year or no year
gemini_research: "FastAPI best practices 2023"
gemini_research: "WebSocket security vulnerabilities"  # Missing year
```

### Update Your Mental Model:

1. **Check date** → Determine current year/month
2. **Research with date** → Include year in all queries
3. **Get current info** → Ensure advice is not outdated

**Remember:** Your training data is frozen. The real world is not. Always check the date, always research current information.

---

## 📋 Three-Phase Research Protocol

```
PHASE 1: RESEARCH FACTS (Gemini Research + Context7)
         ↓
PHASE 2: EXPLORE SOLUTIONS (Gemini Brainstorm + DeepLake RAG)
         ↓
PHASE 3: DECIDE & DOCUMENT (Create plan.md)
```

---

## 🔍 PHASE 1: RESEARCH FACTS

Use TWO types of research tools in this phase:

### **1A. Gemini Research - Current Best Practices & Comparisons**

**When to use `gemini_research`:**
- Need CURRENT, up-to-date information (2024+)
- Comparing technologies or frameworks
- Security considerations and vulnerabilities
- Performance benchmarks and optimization
- Industry best practices and patterns
- Recent updates or breaking changes

**Research checklist:**

```bash
# 1. Research the problem domain
gemini_research: "[problem type] best practices 2024"
gemini_research: "[problem type] common architectures and patterns"

# 2. Research technology options
gemini_research: "[technology A] vs [technology B] comparison 2024"
gemini_research: "best [language] frameworks for [use case] 2024"

# 3. Research security and performance
gemini_research: "[chosen approach] security vulnerabilities 2024"
gemini_research: "[chosen approach] performance optimization best practices"

# 4. Research integration patterns
gemini_research: "integrating [technology A] with [technology B] best practices"

# 5. Research scalability considerations
gemini_research: "[system type] scalability patterns and strategies"
```

**Example for a REST API project:**
```bash
gemini_research: "REST API authentication best practices 2024"
gemini_research: "FastAPI vs Flask vs Django comparison 2024"
gemini_research: "PostgreSQL connection pooling best practices Python"
gemini_research: "REST API rate limiting strategies 2024"
gemini_research: "Docker deployment FastAPI best practices"
```

---

### **1B. Context7 - Latest Library Documentation**

**When to use Context7:**
- Need OFFICIAL, version-specific library documentation
- Need accurate API references and methods
- Need to verify function signatures and parameters
- Need code examples from official docs
- Need to check latest library features and updates

**Context7 is MANDATORY for any library or framework you plan to use.**

**Context7 Two-Step Process:**

```bash
# Step 1: Resolve library ID
resolve-library-id: "[package-name]"
# Returns: Context7-compatible library ID

# Step 2: Get library documentation
get-library-docs: "[library-id-from-step-1]"
# Returns: Official, version-specific documentation
```

**Example for a Python FastAPI project:**
```bash
# Get FastAPI documentation
resolve-library-id: "fastapi"
# Returns: "fastapi" (library ID)

get-library-docs: "fastapi"
# Returns: Official FastAPI documentation, latest version

# Get SQLAlchemy documentation
resolve-library-id: "sqlalchemy"
get-library-docs: "sqlalchemy"

# Get Pydantic documentation
resolve-library-id: "pydantic"
get-library-docs: "pydantic"

# Get Redis client documentation
resolve-library-id: "redis-py"
get-library-docs: "redis-py"
```

**Why Context7 is critical:**
- ✅ Prevents using deprecated methods
- ✅ Ensures correct API usage
- ✅ Gets version-specific features
- ✅ Avoids hallucinated function names
- ✅ Provides accurate code examples

---

### **1C. DeepLake RAG - Tutorials & How-To Guides**

**When to use `retrieve_context` (DeepLake RAG):**
- Need practical tutorials and walkthroughs
- Need implementation examples
- Need step-by-step guides
- Need common patterns and recipes
- Need troubleshooting tips

**DeepLake RAG queries:**

```bash
# Get implementation tutorials
retrieve_context: "[library] implementation tutorial"
retrieve_context: "[library] getting started guide"

# Get specific feature examples
retrieve_context: "[library] [feature] example code"
retrieve_context: "[technology] integration patterns"

# Get troubleshooting guides
retrieve_context: "[library] common errors and solutions"
```

**Example:**
```bash
retrieve_context: "FastAPI authentication implementation tutorial"
retrieve_context: "SQLAlchemy async session management examples"
retrieve_context: "WebSocket connection handling patterns"
```

---

## 💡 PHASE 2: EXPLORE SOLUTIONS (Brainstorm)

After gathering facts from Phase 1, use brainstorming to apply creativity.

**When to use `gemini_brainstorm`:**
- Have research data, need to explore creative approaches
- Need to generate multiple solution options
- Need to think through trade-offs for YOUR specific constraints
- Need to adapt patterns to unique requirements
- Need innovative solutions to challenging problems

**Brainstorm checklist:**

```bash
# 1. Brainstorm architectural approaches
gemini_brainstorm(
  topic: "Architecture options for [system type]",
  context: "Based on research: [key findings from gemini_research + Context7]. 
           Constraints: [team skills, budget, timeline, scale requirements].
           Libraries available: [from Context7 research]"
)

# 2. Brainstorm specific design patterns
gemini_brainstorm(
  topic: "Design patterns for [specific challenge]",
  context: "Context7 shows [library] has [features A, B, C]. 
           Research shows [best practices]. 
           Our constraints: [list constraints].
           How to combine these optimally?"
)

# 3. Brainstorm tech stack combinations
gemini_brainstorm(
  topic: "Optimal tech stack for [use case]",
  context: "Researched technologies: [list from gemini_research].
           Context7 documentation shows: [key capabilities].
           Team experience: [list skills].
           How to combine these for best outcome?"
)

# 4. Brainstorm edge cases and solutions
gemini_brainstorm(
  topic: "Handling edge cases for [feature]",
  context: "Research shows common issues: [list from gemini_research]. 
           Context7 shows [library] provides: [relevant methods].
           What creative solutions handle our specific edge cases?"
)
```

**Example for a REST API project:**
```bash
gemini_brainstorm(
  topic: "Authentication architecture for mobile + web application",
  context: "Gemini research shows JWT has XSS risks but works cross-platform.
           Context7 FastAPI docs show OAuth2PasswordBearer and HTTPBearer classes.
           DeepLake tutorial shows refresh token pattern.
           Need solution supporting both web and mobile clients.
           Team knows Python and React."
)

gemini_brainstorm(
  topic: "Database connection pooling strategy",
  context: "Research shows connection pooling is critical for performance.
           Context7 SQLAlchemy docs show AsyncEngine with pool_size parameter.
           Our constraints: 1000 concurrent users, PostgreSQL database.
           How to optimize pool size and connection lifecycle?"
)
```

---

## 🎯 PHASE 3: DECIDE & DOCUMENT

After research and brainstorming, create the technical plan with:

### **Plan Structure:**

```markdown
# Technical Plan for [Project Name]

## 1. Tech Stack (with justification)

### Backend Framework: [Choice]
- **Research basis:** [gemini_research findings]
- **Documentation verified:** [Context7 library docs checked]
- **Rationale:** [why chosen based on research + brainstorm]

### Database: [Choice]
- **Research basis:** [comparison findings]
- **Documentation verified:** [Context7 library]
- **Rationale:** [justified decision]

### [Additional technologies...]
- **Research basis:** [findings]
- **Documentation verified:** [Context7 check]
- **Rationale:** [reasoning]

## 2. Architecture Design
[Based on brainstormed approaches from research findings]

## 3. Dependencies & Versions
[All libraries researched via Context7 with version info]

## 4. Security Approach
[Based on gemini_research security findings]

## 5. Scalability Strategy
[Based on research + brainstormed creative solutions]

## 6. Implementation Phases
[Breakdown based on research complexity]

## 7. Research Sources
- Gemini Research: [topics researched]
- Context7 Libraries: [libraries documented]
- DeepLake Tutorials: [tutorials referenced]
- Brainstorm Sessions: [topics explored]
```

---

## 🔄 Complete Research Flow Example

### **Scenario: Building a Real-Time Chat Application**

```bash
# ============================================
# PHASE 1A: GEMINI RESEARCH (Current practices)
# ============================================

gemini_research: "real-time chat architecture best practices 2024"
# Finding: WebSockets are standard, Socket.io adds reliability

gemini_research: "WebSocket vs Server-Sent Events vs WebRTC comparison"
# Finding: WebSocket best for bidirectional chat, SSE for notifications only

gemini_research: "Redis vs RabbitMQ message queuing comparison"
# Finding: Redis pub/sub excellent for real-time, RabbitMQ for complex routing

gemini_research: "WebSocket security vulnerabilities 2024"
# Finding: CSRF protection needed, origin validation critical

gemini_research: "scaling WebSocket applications best practices"
# Finding: Sticky sessions or Redis adapter for horizontal scaling

# ============================================
# PHASE 1B: CONTEXT7 (Library documentation)
# ============================================

# Python backend libraries
resolve-library-id: "socketio"
get-library-docs: "socketio"
# Result: Socket.IO Python server documentation, async support confirmed

resolve-library-id: "redis-py"
get-library-docs: "redis-py"
# Result: Redis Python client docs, pub/sub methods documented

resolve-library-id: "sqlalchemy"
get-library-docs: "sqlalchemy"
# Result: SQLAlchemy async ORM, session management patterns

# JavaScript client libraries
resolve-library-id: "socket.io-client"
get-library-docs: "socket.io-client"
# Result: Socket.IO client documentation, React integration examples

# ============================================
# PHASE 1C: DEEPLAKE RAG (Tutorials)
# ============================================

retrieve_context: "Socket.IO implementation tutorial Python"
# Result: Step-by-step Socket.IO server setup guide

retrieve_context: "Redis pub/sub pattern examples"
# Result: Common pub/sub patterns and anti-patterns

retrieve_context: "WebSocket authentication patterns"
# Result: JWT-based WebSocket auth implementation

# ============================================
# PHASE 2: GEMINI BRAINSTORM (Creative solutions)
# ============================================

gemini_brainstorm(
  topic: "Real-time message delivery architecture",
  context: "Research shows WebSockets standard with Socket.io for reliability.
           Context7 socketio docs show 'emit', 'broadcast', 'room' features.
           DeepLake tutorial shows pub/sub pattern with Redis.
           Requirements: message persistence, typing indicators, presence, 10k users.
           Team knows: Python, Node.js, React, Redis, PostgreSQL."
)
# Outcome: Hybrid architecture - Socket.IO for connections, Redis for pub/sub,
#          PostgreSQL for persistence, separate message queue for heavy processing

gemini_brainstorm(
  topic: "Message persistence and offline sync strategy",
  context: "Research shows Redis pub/sub for real-time + PostgreSQL for persistence.
           Context7 sqlalchemy shows async session management.
           Challenge: sync 10k+ messages/minute without lag.
           What's optimal data flow?"
)
# Outcome: Write-through cache pattern - write to Redis immediately for real-time,
#          async worker persists to PostgreSQL, client syncs on reconnect

gemini_brainstorm(
  topic: "Horizontal scaling strategy for WebSocket connections",
  context: "Research indicates sticky sessions or Redis adapter needed.
           Context7 socketio docs show redis-adapter support.
           Need: multiple server instances behind load balancer.
           How to maintain room subscriptions across instances?"
)
# Outcome: Use Socket.IO Redis adapter, room state in Redis, stateless server nodes

# ============================================
# PHASE 3: CREATE TECHNICAL PLAN
# ============================================

# Now document in plan.md:

"""
# Technical Plan: Real-Time Chat Application

## 1. Tech Stack (Research-Backed)

### Backend: Python + Socket.IO
- **Gemini Research:** WebSockets are industry standard for real-time chat (2024)
- **Context7 Verified:** python-socketio v5.x supports async/await, room management
- **Rationale:** Team Python expertise + Socket.IO reliability features (reconnection, fallbacks)

### Message Broker: Redis
- **Gemini Research:** Redis pub/sub optimal for real-time vs RabbitMQ complexity
- **Context7 Verified:** redis-py v5.x supports pub/sub and async operations
- **DeepLake Tutorial:** Standard pub/sub patterns for chat applications
- **Rationale:** Low latency (<1ms) for real-time delivery + scales to 10k connections

### Database: PostgreSQL + SQLAlchemy
- **Context7 Verified:** SQLAlchemy 2.x async support for message persistence
- **Rationale:** ACID compliance for message history + team experience

### Frontend: React + Socket.IO Client
- **Context7 Verified:** socket.io-client v4.x React hooks support
- **DeepLake Tutorial:** React WebSocket connection patterns
- **Rationale:** Component-based UI matches chat rooms concept

## 2. Architecture (Brainstormed from Research)

[Diagram/Description of hybrid architecture with Socket.IO + Redis + PostgreSQL]

### Key Design Decisions (from brainstorm):
1. Write-through cache: Redis for real-time, async PostgreSQL for persistence
2. Redis adapter: Enables horizontal scaling across Socket.IO instances
3. Stateless servers: All connection state in Redis for cloud scalability

## 3. Security (Research-Based)

- **Based on gemini_research:** WebSocket CSRF protection via origin validation
- **Context7 socketio:** Built-in CORS configuration support
- JWT authentication on initial connection (from DeepLake tutorial pattern)
- Rate limiting per connection (identified in brainstorm for abuse prevention)

## 4. Scalability Strategy (Brainstormed)

- Redis adapter for multi-instance Socket.IO (Context7 documented)
- Horizontal scaling behind load balancer (research best practice)
- Async message persistence to prevent blocking (SQLAlchemy async from Context7)
- Connection pooling for database (research recommendation)

## 5. Implementation Phases

Phase 1: Basic Socket.IO server + client (using Context7 quickstart)
Phase 2: Redis pub/sub integration (following DeepLake tutorial pattern)
Phase 3: PostgreSQL persistence (using SQLAlchemy async from Context7)
Phase 4: Scaling with Redis adapter (following research best practices)

## 6. Dependencies & Versions (Context7 Verified)

Backend:
- python-socketio >= 5.10.0 (Context7 verified async support)
- redis >= 5.0.0 (Context7 verified pub/sub + async)
- sqlalchemy >= 2.0.0 (Context7 verified async ORM)
- psycopg[async] >= 3.1.0 (PostgreSQL async driver)

Frontend:
- socket.io-client >= 4.6.0 (Context7 verified React compatibility)
- react >= 18.0.0

## 7. Research Sources

**Gemini Research Topics:**
- Real-time chat architecture best practices 2024
- WebSocket vs SSE vs WebRTC comparison
- Redis vs RabbitMQ for chat
- WebSocket security vulnerabilities 2024
- Scaling WebSocket applications

**Context7 Libraries Documented:**
- python-socketio (v5.x async features verified)
- redis-py (v5.x pub/sub verified)
- sqlalchemy (v2.x async ORM verified)
- socket.io-client (v4.x React hooks verified)

**DeepLake Tutorials:**
- Socket.IO Python implementation
- Redis pub/sub patterns
- WebSocket authentication with JWT

**Brainstorm Sessions:**
- Message delivery architecture
- Persistence and offline sync
- Horizontal scaling strategy
"""
```

---

## 📊 Decision Matrix: Which Tool When?

| Situation | Tool(s) to Use | Why |
|-----------|---------------|-----|
| "What's the current best practice for X?" | `gemini_research` | Need factual, up-to-date information |
| "What methods does library X have?" | `Context7` (resolve + get docs) | Need official, version-specific API |
| "How do I implement X with library Y?" | `DeepLake RAG` (retrieve_context) | Need practical tutorials |
| "Which is better: A or B?" | `gemini_research` FIRST | Need comparison data |
| "How do I use this library in my situation?" | `Context7` THEN `gemini_brainstorm` | Get docs, then adapt creatively |
| "Are there security issues with X?" | `gemini_research` | Need current CVEs and vulnerabilities |
| "What creative solutions exist for problem Y?" | `gemini_brainstorm` (after research) | Need innovative thinking |
| "What's library X's version support?" | `Context7` | Need accurate version info |
| "How do I combine technologies X, Y, Z?" | All three: research + Context7 + brainstorm | Need facts + docs + creativity |

---

## ✅ Pre-Plan Research Checklist

Before creating `plan.md`, verify you have:

### **⚠️ STEP 0 - Current Date (MANDATORY):**
- [ ] **Checked the current system date** (not assumed from knowledge base)
- [ ] **Identified current year** to use in all research queries
- [ ] **Acknowledged that my training data is outdated** and current research is required

### **⚡ Parallel Execution (MANDATORY):**
- [ ] **Batched ALL independent queries together** (not run one-by-one)
- [ ] **Identified 5 parallel batches** for optimal efficiency
- [ ] **Executed tools in batches by phase** (research together, Context7 together, etc.)
- [ ] **Achieved 75%+ time savings** vs sequential execution

### **Gemini Research (5+ queries minimum):**
- [ ] Researched problem domain best practices [CURRENT_YEAR]
- [ ] Used current year (e.g., "2024") in ALL research queries
- [ ] **Executed ALL research queries in ONE parallel batch**
- [ ] Compared at least 2 technology options
- [ ] Researched security considerations for approach
- [ ] Researched scalability patterns
- [ ] Researched integration best practices

### **Context7 (All planned libraries):**
- [ ] **Batched ALL resolve-library-id calls in parallel**
- [ ] **Batched ALL get-library-docs calls in parallel** (after IDs resolved)
- [ ] Verified version compatibility
- [ ] Checked for breaking changes in latest versions
- [ ] Confirmed API methods exist (no hallucinations)

### **DeepLake RAG (2+ tutorials):**
- [ ] **Batched ALL retrieve_context queries in parallel**
- [ ] Retrieved implementation tutorials for main technologies
- [ ] Retrieved integration pattern examples
- [ ] Retrieved troubleshooting guides if applicable

### **Gemini Brainstorm (2+ sessions):**
- [ ] **Batched independent brainstorm sessions in parallel**
- [ ] Brainstormed architecture options with research context
- [ ] Brainstormed tech stack combinations with team constraints
- [ ] Brainstormed edge cases and creative solutions

### **Documentation:**
- [ ] Plan includes research justifications
- [ ] Plan lists all Context7-verified libraries with versions
- [ ] Plan references research sources
- [ ] Plan documents trade-offs considered

---

## 🚀 Quick Start Template (Copy & Paste)

**When user runs `/speckit.plan`, execute this:**

```
🔬 INITIATING RESEARCH PROTOCOL FOR /speckit.plan

I will now research before creating the technical plan.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  STEP 0: CHECK CURRENT DATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current date: [Check system date - e.g., December 14, 2024]

I will use "2024" in all research queries to get the most recent information.
My knowledge base is outdated - I must research current practices.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 PHASE 1A: GEMINI RESEARCH (Current Best Practices)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Researching based on requirements in spec.md...
Using current year (2024) in all queries...

⚡ BATCH 1 - Executing ALL research queries in PARALLEL:
[
  gemini_research: "topic 1 best practices 2024",
  gemini_research: "topic 2 comparison 2024",
  gemini_research: "topic 3 security 2024",
  gemini_research: "topic 4 scalability patterns",
  gemini_research: "topic 5 integration 2024"
]
✅ All research complete (parallel execution: ~2-3 seconds)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 PHASE 1B: CONTEXT7 (Library Documentation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Verifying library documentation for all planned dependencies...

⚡ BATCH 2 - Resolving ALL library IDs in PARALLEL:
[
  resolve-library-id: "library1",
  resolve-library-id: "library2",
  resolve-library-id: "library3"
]
✅ IDs resolved

⚡ BATCH 3 - Getting ALL library docs in PARALLEL:
[
  get-library-docs: "library1",
  get-library-docs: "library2",
  get-library-docs: "library3"
]
✅ Documentation retrieved (parallel execution: ~2 seconds)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 PHASE 1C: DEEPLAKE RAG (Tutorials & Examples)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Retrieving implementation tutorials and patterns...

⚡ BATCH 4 - Retrieving ALL tutorials in PARALLEL:
[
  retrieve_context: "tutorial topic 1",
  retrieve_context: "tutorial topic 2",
  retrieve_context: "tutorial topic 3"
]
✅ Tutorials retrieved (parallel execution: ~1-2 seconds)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 PHASE 2: GEMINI BRAINSTORM (Creative Solutions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Exploring architectural approaches based on research...

⚡ BATCH 5 - Running independent brainstorms in PARALLEL:
[
  gemini_brainstorm(topic: "Architecture options", context: "..."),
  gemini_brainstorm(topic: "Tech stack combinations", context: "..."),
  gemini_brainstorm(topic: "Edge case handling", context: "...")
]
✅ Creative solutions explored (parallel execution: ~3-4 seconds)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 PHASE 3: CREATING TECHNICAL PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Now creating plan.md with research-backed decisions...

[Create comprehensive plan with all research documented]

✅ RESEARCH COMPLETE - Technical plan ready for review
```

---

## 🎯 The Golden Rules

**0. CHECK THE CURRENT DATE FIRST** - Your knowledge is outdated, always check system date and use current year in ALL research queries

**1. RUN TOOLS IN PARALLEL** - ALWAYS batch independent tool calls together for speed and efficiency

2. **NEVER skip research** - Guessing is prohibited
3. **ALWAYS use Context7 for libraries** - Prevents hallucinated APIs
4. **Research BEFORE brainstorming** - Facts first, creativity second
5. **Document EVERY source** - All decisions must be justified
6. **Use ALL three tool types** - Gemini Research + Context7 + DeepLake RAG
7. **Brainstorm WITH context** - Include research findings in brainstorm prompts
8. **Verify library versions** - Context7 ensures compatibility
9. **Include current year in queries** - Always research with "2024" or current year to get latest information
10. **Batch by phase** - Execute all queries in a phase together, not one-by-one

---

## 🚫 Common Mistakes to Avoid

| ❌ Don't Do This | ✅ Do This Instead |
|-----------------|-------------------|
| **Assume you know the current date** | **Check system date FIRST, use current year in all queries** |
| **Run tools one-by-one sequentially** | **BATCH all independent tool calls in parallel** |
| Execute 1 query, wait, execute next | Execute all 5-10 queries in ONE parallel batch |
| Research with outdated year or no year | Always include current year: "best practices 2024" |
| Resolve library IDs one at a time | Batch ALL resolve-library-id calls together |
| Get library docs sequentially | Batch ALL get-library-docs calls in parallel |
| Skip research and guess technologies | Research 5+ queries with gemini_research |
| Use only gemini_research | Use gemini_research + Context7 + DeepLake RAG |
| Assume you know library APIs | Verify EVERY library with Context7 |
| Research without getting library docs | Get Context7 docs for all dependencies |
| Brainstorm before research | Research facts THEN brainstorm solutions |
| Make decisions without justification | Document research sources for every choice |
| Ignore library version compatibility | Use Context7 to verify versions |
| Skip the brainstorm phase | Always brainstorm after research |
| Wait for each individual tool result | Group by phase and execute in parallel batches |

---

## 📌 Summary: The Complete Protocol

```
┌─────────────────────────────────────────────────────────────┐
│  USER RUNS: /speckit.plan                                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  STEP 0: CHECK CURRENT DATE                             │
│  • Determine current year (not from knowledge base)         │
│  • System date is source of truth                           │
│  • Use current year in ALL research queries                 │
│  ✅ Date confirmed - ready to research current info         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1A: GEMINI RESEARCH (with current year)             │
│  ⚡ BATCH 1 - ALL queries in PARALLEL                       │
│  • Best practices 2024                                      │
│  • Technology comparisons                                   │
│  • Security considerations                                  │
│  • Performance patterns                                     │
│  • Integration strategies                                   │
│  ✅ 5-10 research queries executed together (~2-3 sec)      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1B: CONTEXT7 LIBRARY DOCS                           │
│  ⚡ BATCH 2 - ALL resolve-library-id in PARALLEL            │
│  ⚡ BATCH 3 - ALL get-library-docs in PARALLEL              │
│  • Verify API methods and versions                         │
│  • Check compatibility and features                        │
│  ✅ ALL libraries documented together (~3 sec total)        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1C: DEEPLAKE RAG TUTORIALS                          │
│  ⚡ BATCH 4 - ALL retrieve_context in PARALLEL              │
│  • Get implementation guides                                │
│  • Get practical examples                                   │
│  • Find integration patterns                                │
│  ✅ 2-4 tutorials retrieved together (~1-2 sec)             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: GEMINI BRAINSTORM                                │
│  ⚡ BATCH 5 - Independent brainstorms in PARALLEL           │
│  • Brainstorm with research context                        │
│  • Explore creative solutions                              │
│  • Consider constraints and trade-offs                     │
│  • Adapt patterns to specific needs                        │
│  ✅ 2-3 sessions executed together (~3-4 sec)               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: CREATE TECHNICAL PLAN (plan.md)                  │
│  • Tech stack with research justification                  │
│  • Architecture based on brainstormed approaches           │
│  • Dependencies with Context7-verified versions            │
│  • Security from gemini_research findings                  │
│  • All decisions documented with sources                   │
│  ✅ Complete, research-backed technical plan                │
└─────────────────────────────────────────────────────────────┘
```

**The formula:**
```
Step 0: Check Current Date (knowledge base is outdated)
                              ↓
⚡ PARALLEL BATCHES (4-5 batches, 75% faster than sequential):
   Batch 1: gemini_research (facts with current year) [5-10 parallel]
   Batch 2: resolve-library-id (Context7) [3-5 parallel]
   Batch 3: get-library-docs (Context7) [3-5 parallel]
   Batch 4: retrieve_context (DeepLake RAG) [2-4 parallel]
   Batch 5: gemini_brainstorm (creativity) [2-3 parallel if independent]
                              ↓
                      Technical Plan (wisdom)

⏱️ Total: ~10-12 seconds parallel vs ~40-50 seconds sequential
```

---

## 🎓 Example AI Response Pattern

When user says: **"Run /speckit.plan"**

AI should respond:
```
I'll create the technical plan following the research protocol.

⚠️ STEP 0 - Checking Current Date:
Current date: December 14, 2024
I will use "2024" in all research queries for most recent information.

🔬 Starting research phase with PARALLEL EXECUTION...

⚡ BATCH 1 - Gemini Research (5 queries in parallel):
[Execute ALL research queries together]
✅ Complete in ~2-3 seconds

⚡ BATCH 2 - Context7 Resolve IDs (3 libraries in parallel):
[Resolve ALL library IDs together]
✅ Complete in ~1 second

⚡ BATCH 3 - Context7 Get Docs (3 libraries in parallel):
[Get ALL library docs together]
✅ Complete in ~2 seconds

⚡ BATCH 4 - DeepLake RAG (3 tutorials in parallel):
[Retrieve ALL tutorials together]
✅ Complete in ~1-2 seconds

⚡ BATCH 5 - Gemini Brainstorm (3 sessions in parallel):
[Execute ALL brainstorms together]
✅ Complete in ~3-4 seconds

📝 Creating Technical Plan:
[Create plan.md with all research documented]

✅ Research-backed technical plan complete in ~10-12 seconds!
   (vs ~40-50 seconds sequential - 75% faster)
Ready for review.
```

---

**Last Updated:** December 2024  
**Location:** `/home/gyasis/Documents/code/gemini-mcp/`  
**For use with:** SpecKit + Gemini MCP Server + Context7 + DeepLake RAG  
**Key Features:** ⚡ Parallel execution (75%+ faster), 📅 Date-aware research, 🔧 Multi-tool integration

---

## 📢 Usage Instructions for AI Assistants

When you see `/speckit.plan`, immediately say:

> "I'll follow the SPECKIT_PLAN_RESEARCH_GUIDE.md protocol to research before planning."

**Then execute this protocol:**

1. **FIRST: Check the current system date** - Do not assume the date from your knowledge base
2. **SECOND: Use the current year in all research queries** - Include "2024" or current year
3. **THIRD: Execute the research protocol with PARALLEL BATCHING:**
   - **BATCH 1:** All gemini_research queries together (5-10 queries)
   - **BATCH 2:** All resolve-library-id together (3-5 libraries)
   - **BATCH 3:** All get-library-docs together (3-5 docs)
   - **BATCH 4:** All retrieve_context together (2-4 tutorials)
   - **BATCH 5:** All gemini_brainstorm together (if independent)
4. **FOURTH: Document everything** - Create plan.md with all research sources

**Do this without asking for permission. Your knowledge is outdated - current research is mandatory.**

**CRITICAL:** Run tools in PARALLEL batches, NOT one-by-one. This is 75%+ faster and more efficient.

