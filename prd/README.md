# PRD Folder - Hybrid Deep Research Enhancement

## Quick Reference

**Main Document:** `HYBRID_DEEP_RESEARCH_PRD.md`

**Purpose:** Specification for adding 6 new Deep Research tools to the Gemini MCP Server

**Status:** ✅ Ready for Implementation

---

## What This PRD Adds

### 7 New MCP Tools:

1. **`start_deep_research`** - Main hybrid research tool with auto sync→async switching
2. **`check_research_status`** - Poll status of running research
3. **`get_research_results`** - Retrieve completed results
4. **`cancel_research`** - Cancel running research
5. **`multi_hop_research`** - Orchestrate gemini_research + gemini_brainstorm
6. **`estimate_research_cost`** - Estimate before starting
7. **`save_research_to_markdown`** - Save results to permanent MD files (zero tokens)

### Key Features:

- ⚡ **5-minute timeout**: Start sync, auto-switch to async if needed
- 🔔 **Native OS Notifications**: Desktop notifications (Linux/macOS/Windows)
- 🔄 **Multi-hop**: Chain research → brainstorm → refined research
- 💰 **Cost tracking**: Token usage and pricing estimation
- 📊 **Progress tracking**: Real-time status updates
- 💾 **State persistence**: Resume from any point
- 📝 **Markdown files**: Permanent storage (zero token cost)

---

## How This PRD Was Created

This PRD was created using **multi-hop collaboration** with Gemini tools:

### Step 1: Research Best Practices
**Tool:** `mcp_gemini-mcp_gemini_research`  
**Query:** "MCP async best practices 2024-2025"  
**Result:** Industry standards for sync/async switching patterns

### Step 2: Brainstorm Architecture
**Tool:** `mcp_gemini-mcp_gemini_brainstorm`  
**Query:** "Hybrid Deep Research architecture with 5-min timeout"  
**Result:** Complete technical architecture design

### Step 3: Brainstorm Multi-Hop Strategy
**Tool:** `mcp_gemini-mcp_gemini_brainstorm`  
**Query:** "Multi-hop orchestration combining research + brainstorm"  
**Result:** Detailed workflow for chaining tools

### Step 4: Synthesis
Combined all findings into comprehensive PRD with:
- Research findings (verbatim from Gemini)
- Architecture specifications
- Tool specifications
- Pseudo code examples
- Implementation guidelines

---

## For LLM Agents: Implementation Instructions

### Read the PRD:
```python
# Open and read the comprehensive PRD
with open('HYBRID_DEEP_RESEARCH_PRD.md', 'r') as f:
    prd_content = f.read()
```

### Implementation Order:

1. **Phase 1**: Core Infrastructure
   - Create `deep_research/` module
   - Set up Redis & Celery
   - Implement `DeepResearchEngine`

2. **Phase 2**: Add Tools to `server.py`
   - Follow `@mcp.tool()` pattern
   - Implement all 6 tools
   - Integrate with existing tools

3. **Phase 3**: Notification System
   - Webhook, Email, Discord, Slack, Telegram

4. **Phase 4**: Testing
   - Test sync mode
   - Test async mode
   - Test notifications
   - Test multi-hop

5. **Phase 5**: Documentation
   - Update README.md
   - Add usage examples

### Key Files to Modify:

```
gemini-mcp/
├── server.py                    # MODIFY: Add 6 @mcp.tool() functions
├── requirements.txt             # MODIFY: Add redis, celery, httpx
├── .env                         # MODIFY: Add Redis config
├── deep_research/              # CREATE: New module
│   ├── __init__.py
│   ├── engine.py
│   ├── state_manager.py
│   ├── notification_service.py
│   ├── multi_hop.py
│   └── cost_estimator.py
└── README.md                    # MODIFY: Document new tools
```

---

## Example Usage (After Implementation)

### Quick Research (Completes Sync):
```python
result = await start_deep_research(
    query="What are Python 3.12 features?",
    notification_type="database"
)
# Returns: {"status": "completed", "results": {...}}
```

### Long Research (Goes Async):
```python
result = await start_deep_research(
    query="Comprehensive quantum computing analysis 2024-2025...",
    notification_type="discord",
    notification_config={"webhook_url": "https://..."}
)
# Returns: {"status": "running_async", "task_id": "abc-123"}

# Later...
status = check_research_status(task_id="abc-123")
# Returns: {"progress": 67, "current_action": "Analyzing source 67/100"}

# After Discord notification...
results = get_research_results(task_id="abc-123")
# Returns: Full report, sources, metadata
```

### Multi-Hop Research:
```python
result = await multi_hop_research(
    query="AI regulation impact on healthcare",
    hops=3,
    auto_refine=True
)
# Executes: Research → Brainstorm → Research → Brainstorm → Research → Brainstorm
# Returns: Synthesized report from all hops
```

---

## Cost Estimation

Based on research findings:

**Gemini 2.5/3 Pro Pricing:**
- Input: $2 per million tokens
- Output: $12 per million tokens (≤200k prompt)
- Output: $18 per million tokens (>200k prompt)

**Typical Costs:**
- Simple query: $0.30 - $0.80
- Medium query: $0.50 - $3.00
- Complex query: $2.00 - $10.00
- Multi-hop (2 hops): 1.6x single query cost

---

## Success Criteria

✅ **Mode Switching**: 95%+ accurate sync/async decisions  
✅ **Notifications**: 99%+ delivery rate  
✅ **State Recovery**: 100% after failure  
✅ **Cost Accuracy**: ±10% estimate vs actual  
✅ **Async Completion**: 95%+ within max_wait_hours  

---

## Questions?

**For Implementation Details:** Read `HYBRID_DEEP_RESEARCH_PRD.md` sections:
- Tool Specifications (complete API specs)
- Implementation Guidelines (file structure, patterns)
- High-Level Pseudo Code (logic examples)

**For Architecture:** See "Architecture Design" section

**For Multi-Hop:** See "Multi-Hop Research Strategy" section

---

## Addendums

1. **NATIVE_OS_NOTIFICATIONS_ADDENDUM.md** - Replaces external services with native desktop notifications
2. **MARKDOWN_PERSISTENCE_ADDENDUM.md** - Permanent file storage (zero token cost)

---

**Last Updated:** December 14, 2025  
**Created By:** Multi-hop Gemini collaboration (research + brainstorm)  
**Status:** Ready for Implementation ✅

