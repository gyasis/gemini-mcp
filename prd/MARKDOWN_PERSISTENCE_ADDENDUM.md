# Markdown Persistence Addendum
## PRD Update: Permanent Research Report Storage

**Version:** 1.2  
**Date:** December 14, 2025  
**Status:** Ready for Implementation  
**Critical Feature:** Core functionality (not optional)

---

## Executive Summary

**Problem:** Research results stored only in Redis are temporary. If cache expires or Redis restarts, research is lost. Users need permanent, readable files they can reference later.

**Solution:** Add lightweight MCP tool `save_research_to_markdown` that reads completed research from Redis and saves to permanent Markdown files using template-based generation.

**Key Decision (from Gemini):** Do NOT have Deep Research agent create MD files - this would double token usage and cost. Use separate, lightweight tool for file I/O.

---

## Why This Matters

### User Scenario:
```
User makes 10 research calls on different topics:
1. "Quantum computing developments 2024"
2. "AI regulation in healthcare"
3. "Renewable energy market analysis"
...
10. "Blockchain scalability solutions"

Expected Result:
10 separate Markdown files saved to disk:
- research_abc-123_20251214_103045.md
- research_def-456_20251214_110230.md
- research_ghi-789_20251214_113415.md
...
- research_xyz-890_20251214_152030.md

Each file contains:
✓ Full research report
✓ All citations and sources
✓ Metadata (duration, cost, tokens)
✓ Timestamp and task ID
✓ Formatted as clean, readable Markdown
```

### Without This Feature:
- ❌ Research lost when Redis expires (temporary storage)
- ❌ No permanent record
- ❌ Can't reference later
- ❌ Can't share with team
- ❌ Can't track research history

### With This Feature:
- ✅ Permanent files on disk
- ✅ Can reference anytime
- ✅ Can share via Git, email, etc.
- ✅ Research library builds over time
- ✅ Version control friendly

---

## Research Findings

### From Gemini Brainstorm (December 14, 2025)

**Question:** How to efficiently save research to MD without using expensive Deep Research agent?

**Answer:** **Template-Based Markdown Generation**

**Strategy:**
1. Deep Research agent: Generates report, saves to Redis (its job ends here)
2. Lightweight tool: Reads from Redis, formats using template, saves to file
3. Template engine: Jinja2 (Python) - zero token cost
4. Result: Clean MD files with zero additional LLM tokens

**Advantages:**
- ⚡ **Zero token cost** (no LLM involved)
- 🎯 **Highly controllable** format
- 🚀 **Fast and scalable**
- 🔧 **Easy to modify** templates
- 💰 **No additional API costs**

### From Gemini Ask (December 14, 2025)

**Question:** Deep Research creates MD vs. separate tool?

**Answer:** **Separate tool is better.**

**Reasoning:**
- **Cost:** Significantly lower token usage
- **Architecture:** Separation of concerns (better design)
- **Modularity:** Each tool does ONE thing well
- **Maintainability:** Easier to update and test

---

## Architecture

### Tool Separation (Single Responsibility Principle)

```
┌─────────────────────────────────────────────────────────────┐
│ Tool 1: Deep Research Agent                                 │
│                                                             │
│ Job: Generate comprehensive research report                 │
│ Input: User query                                           │
│ Output: Research report (stored in Redis)                   │
│ Token Usage: HIGH (research generation)                     │
│ Status: Expensive, complex                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Saves to Redis
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Redis (Temporary Storage)                                   │
│ Key: research:result:{task_id}                              │
│ Value: {report, sources, metadata}                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Reads from Redis
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Tool 2: Save to Markdown (NEW)                              │
│                                                             │
│ Job: Format and save to permanent file                      │
│ Input: task_id                                              │
│ Output: Markdown file on disk                               │
│ Token Usage: ZERO (template-based)                          │
│ Status: Cheap, simple, fast                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Writes to disk
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ Permanent Storage                                           │
│ File: research_reports/research_abc-123_20251214.md         │
│ Format: Clean, readable Markdown                            │
│ Contains: Report, sources, citations, metadata              │
└─────────────────────────────────────────────────────────────┘
```

---

## New Tool Specification

### Tool 7: `save_research_to_markdown`

**Purpose:** Save completed research results to permanent Markdown file

**Function Signature:**
```python
@mcp.tool()
def save_research_to_markdown(
    task_id: str,
    output_dir: str = "./research_reports",
    filename_prefix: str = "research",
    include_metadata: bool = True,
    include_sources: bool = True,
    auto_open: bool = False
) -> Dict[str, Any]:
```

**Parameters:**
- `task_id` (str, required): Task ID from completed research
- `output_dir` (str, default="./research_reports"): Directory to save file
- `filename_prefix` (str, default="research"): Prefix for filename
- `include_metadata` (bool, default=True): Include cost/duration metadata
- `include_sources` (bool, default=True): Include sources section
- `auto_open` (bool, default=False): Open file in default editor after saving

**Returns:**
```json
{
  "success": true,
  "task_id": "abc-123",
  "file_path": "/path/to/research_reports/research_abc-123_20251214_103045.md",
  "file_size_kb": 45.2,
  "filename": "research_abc-123_20251214_103045.md",
  "created_at": "2025-12-14T10:30:45Z"
}
```

**Behavior:**
1. Retrieve research results from Redis using task_id
2. Load Markdown template (Jinja2)
3. Render template with research data
4. Generate filename: `{prefix}_{task_id}_{timestamp}.md`
5. Save to `{output_dir}/{filename}`
6. Optionally open in default editor
7. Return file path and metadata

**Error Handling:**
- Task not found in Redis → 404 error
- Task not completed → 400 error with status
- File write error → 500 error with details
- Template error → 500 error with template info

---

## File Naming Strategy

### Format:
```
{prefix}_{task_id}_{timestamp}.md
```

### Examples:
```
research_abc-123_20251214_103045.md
research_def-456_20251214_110230.md
research_ghi-789_20251214_113415.md
```

### Components:
- **Prefix:** Customizable (default: "research")
- **Task ID:** First 8 chars or full UUID
- **Timestamp:** YYYYMMDD_HHMMSS format
- **Extension:** Always `.md`

### Why This Format?
- ✅ Sortable by time (timestamp)
- ✅ Unique per research (task_id)
- ✅ Easy to identify (prefix)
- ✅ No conflicts (timestamp + task_id)
- ✅ Git-friendly (no spaces or special chars)

---

## Markdown Template

### Template Location:
```
deep_research/templates/research_report.md.j2
```

### Template Content:
```jinja2
# {{ title }}

**Research ID:** `{{ task_id }}`  
**Completed:** {{ completed_at }}  
**Duration:** {{ duration_minutes }} minutes  
**Cost:** ${{ cost_usd }}

---

## Executive Summary

{{ summary }}

---

## Key Findings

{% for finding in key_findings %}
### {{ finding.title }}

{{ finding.description }}

{% if finding.evidence %}
**Evidence:**
{% for evidence in finding.evidence %}
- {{ evidence }}
{% endfor %}
{% endif %}

{% endfor %}

---

## Detailed Analysis

{{ detailed_analysis }}

---

## Sources & Citations

{% for source in sources %}
### [{{ loop.index }}] {{ source.title }}

- **URL:** {{ source.url }}
- **Relevance Score:** {{ source.relevance_score }}
- **Cited:** {{ source.citation_count }} times

{{ source.summary }}

{% endfor %}

---

{% if include_metadata %}
## Research Metadata

| Metric | Value |
|--------|-------|
| Task ID | `{{ task_id }}` |
| Query | {{ original_query }} |
| Started | {{ started_at }} |
| Completed | {{ completed_at }} |
| Duration | {{ duration_minutes }} minutes |
| Sources Analyzed | {{ sources_analyzed }} |
| Tokens (Input) | {{ tokens_input }} |
| Tokens (Output) | {{ tokens_output }} |
| Total Cost | ${{ cost_usd }} |
| Mode | {{ mode }} (sync/async) |
| Multi-Hop | {{ multi_hop_used }} |

{% endif %}

---

## How to Use This Report

This research report was generated by Gemini Deep Research. The information is current as of {{ completed_at }}.

**Suggested Actions:**
- Review the key findings section for main insights
- Check sources for credibility and additional context
- Use citations when referencing this research
- Consider follow-up research questions based on findings

---

*Generated by Gemini Deep Research via MCP Server*  
*Report Template Version: 1.0*
```

### Template Features:
- ✅ Clean, readable Markdown
- ✅ Proper heading hierarchy
- ✅ Numbered sources with citations
- ✅ Metadata table
- ✅ Conditional sections (if data available)
- ✅ Loop support for findings and sources
- ✅ Professional formatting

---

## Directory Structure

### Recommended Layout:
```
gemini-mcp/
├── research_reports/           # NEW: Permanent research files
│   ├── 2025-12/               # Organized by month
│   │   ├── research_abc-123_20251214_103045.md
│   │   ├── research_def-456_20251214_110230.md
│   │   └── research_ghi-789_20251214_113415.md
│   └── 2025-11/
│       └── research_xyz-890_20251130_152030.md
├── deep_research/
│   ├── templates/             # NEW: Jinja2 templates
│   │   └── research_report.md.j2
│   ├── storage.py             # NEW: File I/O module
│   ├── notification.py
│   ├── engine.py
│   └── worker.py
└── server.py
```

### Benefits:
- ✅ Organized by month (easy to find)
- ✅ Separate from code (clean structure)
- ✅ Git-friendly (can commit or gitignore)
- ✅ Easy to backup
- ✅ Easy to search

---

## Implementation

### File: `deep_research/storage.py`

```python
"""
Markdown file persistence for Deep Research results
Zero token usage - template-based generation
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import jinja2

class MarkdownStorage:
    """
    Saves research results to permanent Markdown files
    Uses Jinja2 templates (no LLM tokens required)
    """
    
    def __init__(
        self,
        template_dir: str = "./deep_research/templates",
        output_dir: str = "./research_reports"
    ):
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        
        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save(
        self,
        task_id: str,
        research_data: Dict[str, Any],
        filename_prefix: str = "research",
        include_metadata: bool = True,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Save research results to Markdown file
        
        Args:
            task_id: Research task ID
            research_data: Results from Redis
            filename_prefix: Filename prefix
            include_metadata: Include metadata section
            include_sources: Include sources section
        
        Returns:
            File information
        """
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{task_id[:8]}_{timestamp}.md"
        
        # Organize by month
        month_dir = self.output_dir / datetime.now().strftime("%Y-%m")
        month_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = month_dir / filename
        
        # Prepare template data
        template_data = self._prepare_template_data(
            task_id,
            research_data,
            include_metadata,
            include_sources
        )
        
        # Render template
        try:
            template = self.jinja_env.get_template("research_report.md.j2")
            markdown_content = template.render(template_data)
        except Exception as e:
            raise Exception(f"Template rendering failed: {e}")
        
        # Write to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        except Exception as e:
            raise Exception(f"File write failed: {e}")
        
        # Get file size
        file_size_kb = file_path.stat().st_size / 1024
        
        return {
            "success": True,
            "task_id": task_id,
            "file_path": str(file_path.absolute()),
            "filename": filename,
            "file_size_kb": round(file_size_kb, 2),
            "created_at": datetime.now().isoformat()
        }
    
    def _prepare_template_data(
        self,
        task_id: str,
        research_data: Dict[str, Any],
        include_metadata: bool,
        include_sources: bool
    ) -> Dict[str, Any]:
        """Prepare data for template rendering"""
        
        # Extract from research_data
        report = research_data.get("report", "")
        sources = research_data.get("sources", [])
        metadata = research_data.get("metadata", {})
        
        # Parse report sections (assuming structured format)
        # This is a simple parser - adjust based on actual report format
        sections = self._parse_report(report)
        
        return {
            "task_id": task_id,
            "title": sections.get("title", "Deep Research Report"),
            "summary": sections.get("summary", ""),
            "key_findings": sections.get("findings", []),
            "detailed_analysis": sections.get("analysis", ""),
            "sources": sources if include_sources else [],
            "include_metadata": include_metadata,
            "original_query": metadata.get("query", ""),
            "started_at": metadata.get("started_at", ""),
            "completed_at": metadata.get("completed_at", ""),
            "duration_minutes": metadata.get("duration_minutes", 0),
            "sources_analyzed": metadata.get("sources_analyzed", 0),
            "tokens_input": metadata.get("tokens_input", 0),
            "tokens_output": metadata.get("tokens_output", 0),
            "cost_usd": metadata.get("cost_usd", 0),
            "mode": metadata.get("mode", "unknown"),
            "multi_hop_used": metadata.get("multi_hop_used", False)
        }
    
    def _parse_report(self, report: str) -> Dict[str, Any]:
        """
        Parse report text into sections
        Assumes report has markdown structure
        """
        # Simple parser - can be enhanced
        sections = {
            "title": "Deep Research Report",
            "summary": "",
            "findings": [],
            "analysis": report  # Fallback: full report as analysis
        }
        
        # Try to extract title (first # heading)
        lines = report.split('\n')
        for line in lines:
            if line.startswith('# '):
                sections["title"] = line[2:].strip()
                break
        
        # Can add more sophisticated parsing here
        # For now, keep it simple and reliable
        
        return sections
```

### Tool Implementation in `server.py`:

```python
@mcp.tool()
def save_research_to_markdown(
    task_id: str,
    output_dir: str = "./research_reports",
    filename_prefix: str = "research",
    include_metadata: bool = True,
    include_sources: bool = True
) -> Dict[str, Any]:
    """
    Save completed Deep Research results to permanent Markdown file.
    
    This tool reads research results from Redis and formats them as a clean,
    readable Markdown file saved to disk. Perfect for creating a permanent
    research library.
    
    **Zero Token Cost:** Uses template-based generation (no LLM involved).
    
    **File Naming:** {prefix}_{task_id}_{timestamp}.md
    **Organization:** Files saved in monthly folders
    
    Example Usage:
        # After research completes
        result = save_research_to_markdown(
            task_id="abc-123",
            output_dir="./my_research",
            filename_prefix="quantum_computing"
        )
        
        # Returns:
        {
            "success": true,
            "file_path": "/path/to/my_research/2025-12/quantum_computing_abc-123_20251214.md",
            "file_size_kb": 45.2
        }
    
    Args:
        task_id: Task ID from completed research
        output_dir: Directory to save files (default: ./research_reports)
        filename_prefix: Filename prefix (default: research)
        include_metadata: Include cost/duration info (default: True)
        include_sources: Include sources section (default: True)
    
    Returns:
        File information including path and size
    """
    from deep_research.storage import MarkdownStorage
    from deep_research.state_manager import StateManager
    
    # Check if research is complete
    state_manager = StateManager()
    task = state_manager.get_task(task_id)
    
    if not task:
        return {
            "success": False,
            "error": "Task not found",
            "task_id": task_id
        }
    
    if task["status"] != "completed":
        return {
            "success": False,
            "error": f"Task not completed yet. Status: {task['status']}",
            "current_status": task["status"]
        }
    
    # Get research results
    results = state_manager.get_result(task_id)
    
    if not results:
        return {
            "success": False,
            "error": "Results not found",
            "task_id": task_id
        }
    
    # Save to Markdown
    storage = MarkdownStorage(output_dir=output_dir)
    
    try:
        file_info = storage.save(
            task_id=task_id,
            research_data=results,
            filename_prefix=filename_prefix,
            include_metadata=include_metadata,
            include_sources=include_sources
        )
        return file_info
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "task_id": task_id
        }
```

---

## Auto-Save Feature (Optional)

### Option 1: Manual Save (Default)
```python
# Research completes
result = await start_deep_research(query="...")

# User decides when to save
file_info = save_research_to_markdown(task_id=result["task_id"])
```

### Option 2: Auto-Save (Configurable)
```python
# Add parameter to start_deep_research
result = await start_deep_research(
    query="...",
    auto_save_markdown=True  # Automatically save when complete
)

# File saved automatically after research completes
# Notification includes file path
```

**Recommendation:** Start with manual save (Option 1) for flexibility.

---

## Usage Examples

### Example 1: Basic Save
```python
# Research completed
result = await start_deep_research(
    query="Quantum computing developments 2024-2025"
)

# Save to Markdown
file_info = save_research_to_markdown(task_id=result["task_id"])

print(file_info)
# {
#   "success": true,
#   "file_path": "/path/to/research_reports/2025-12/research_abc-123_20251214_103045.md",
#   "file_size_kb": 45.2,
#   "filename": "research_abc-123_20251214_103045.md"
# }
```

### Example 2: Custom Directory and Prefix
```python
# Save to custom location with custom prefix
file_info = save_research_to_markdown(
    task_id="abc-123",
    output_dir="./my_quantum_research",
    filename_prefix="quantum_analysis"
)

# Result:
# ./my_quantum_research/2025-12/quantum_analysis_abc-123_20251214.md
```

### Example 3: Minimal Metadata
```python
# Save without metadata section (smaller file)
file_info = save_research_to_markdown(
    task_id="abc-123",
    include_metadata=False,
    include_sources=True  # Keep sources, remove metadata
)
```

### Example 4: Batch Save (10 Research Tasks)
```python
# After multiple research tasks
task_ids = ["abc-123", "def-456", "ghi-789", ...]  # 10 task IDs

for task_id in task_ids:
    file_info = save_research_to_markdown(task_id=task_id)
    print(f"Saved: {file_info['filename']}")

# Result: 10 separate MD files
# research_abc-123_20251214_103045.md
# research_def-456_20251214_110230.md
# ...
```

---

## Token & Cost Analysis

### Without This Feature (Using Deep Research to Create MD):
```
Deep Research generates report: 500k tokens input, 100k tokens output
Deep Research formats as MD:   +50k tokens input, +20k tokens output
                               ─────────────────────────────────────
Total per research:            550k input, 120k output
Cost per research:             $1.00 (research) + $0.34 (MD) = $1.34
Cost for 10 researches:        $13.40
```

### With This Feature (Separate Tool):
```
Deep Research generates report: 500k tokens input, 100k tokens output
Template-based MD save:         0 tokens (pure file I/O)
                               ─────────────────────────────────────
Total per research:            500k input, 100k output
Cost per research:             $1.00 (research) + $0.00 (MD) = $1.00
Cost for 10 researches:        $10.00

SAVINGS: $3.40 (25% reduction)
```

**Per 100 Researches:** Save $34.00  
**Per 1000 Researches:** Save $340.00

---

## Success Metrics

### Technical:
- ✅ File write success rate: 99.9%+
- ✅ Template rendering: < 100ms
- ✅ File size: Typically 20-100KB
- ✅ Zero token usage for MD generation

### User Experience:
- ✅ One file per research task
- ✅ Clean, readable Markdown
- ✅ Organized by month
- ✅ Easy to find and reference
- ✅ Git-friendly format

---

## Implementation Checklist

### Phase 1: Core Storage (Week 1)
- [ ] Create `deep_research/storage.py` module
- [ ] Install Jinja2 dependency
- [ ] Create Markdown template
- [ ] Implement `MarkdownStorage` class
- [ ] Test file writing

### Phase 2: Tool Integration (Week 1)
- [ ] Add `save_research_to_markdown` to `server.py`
- [ ] Integrate with state manager
- [ ] Test with completed research tasks
- [ ] Handle error cases

### Phase 3: Polish (Week 2)
- [ ] Improve template formatting
- [ ] Add template customization options
- [ ] Implement auto-save feature (optional)
- [ ] Update documentation

---

## Comparison Table

| Aspect | External Services | Native Notifications | Markdown Files ✅ |
|--------|------------------|---------------------|-------------------|
| **Purpose** | Real-time alerts | Completion alerts | Permanent storage |
| **When** | Research complete | Research complete | Anytime after complete |
| **Volatile** | ❌ Not stored | ❌ Disappears | ✅ Permanent |
| **Shareable** | ❌ Platform-specific | ❌ Can't share | ✅ Easy to share |
| **Offline** | ❌ Requires service | ✅ Works offline | ✅ Always available |
| **Cost** | May cost money | Free | Free |
| **Token Usage** | N/A | N/A | **Zero tokens** |

**Conclusion:** All three serve different purposes:
- **Native Notifications:** "Research is done!" (ephemeral)
- **Markdown Files:** "Here's your permanent research library" (persistent)

---

## Dependencies

**Add to `requirements.txt`:**
```txt
# Markdown template engine
Jinja2>=3.1.0
```

**That's it!** Jinja2 is the only additional dependency.

---

## FAQ

**Q: Why not just keep results in Redis?**  
A: Redis is temporary cache. It expires, can be cleared, doesn't survive restarts.

**Q: Why Markdown instead of PDF or DOCX?**  
A: Markdown is:
- ✅ Plain text (Git-friendly)
- ✅ Human-readable
- ✅ Easy to convert (Pandoc → PDF/DOCX)
- ✅ No special software needed
- ✅ Perfect for developers

**Q: Can I customize the template?**  
A: Yes! Edit `deep_research/templates/research_report.md.j2`

**Q: What if I want to save as JSON instead?**  
A: Easy - just write the `research_data` dict directly to JSON file.

**Q: Does this work with multi-hop research?**  
A: Yes! All research results (standard or multi-hop) can be saved.

**Q: Can I organize files differently (not by month)?**  
A: Yes - modify `MarkdownStorage.save()` to use different folder structure.

---

## Appendix: Gemini Research Sources

### Gemini Brainstorm Results
**Date:** December 14, 2025  
**Tool:** `mcp_gemini-mcp_gemini_brainstorm`  
**Topic:** Token-efficient MD generation

**Key Recommendation:** Template-based Markdown generation (Jinja2)

**Full findings:** See research output above

### Gemini Ask Results
**Date:** December 14, 2025  
**Tool:** `mcp_gemini-mcp_ask_gemini`  
**Question:** Deep Research creates MD vs. separate tool?

**Answer:** Separate tool is better (cost + architecture)

**Full reasoning:** See ask output above

---

**Status:** ✅ Core Feature - Ready for Implementation  
**Token Cost:** Zero (template-based)  
**Approval:** Recommended by Gemini research

---

**END OF ADDENDUM**

