---
noteId: "1271f7304f1d11f09d6057759d41440e"
tags: []

---

# Project Brief - Gemini MCP Server

## Overview
A Model Context Protocol (MCP) server that integrates Google's Gemini Pro AI model with AI assistants, enabling collaborative AI workflows through standardized tool interfaces.

## Core Requirements

### Primary Goals
- Provide seamless Gemini AI integration for MCP-compatible clients
- Enable collaborative AI workflows between different AI models
- Maintain type-safe, reliable tool interfaces
- Support multiple Gemini interaction patterns (Q&A, code review, brainstorming, debugging, web research)
- Deliver multimodal capabilities (video and image analysis)

### Target Users
- AI developers building multi-model workflows
- Teams using Claude Code or other MCP clients
- Developers seeking Gemini integration in their AI toolchains

### Success Criteria
- :white_check_mark: Working MCP server with Gemini integration
- :white_check_mark: Seven core tools implemented (ask, code review, brainstorm, debug, research, video, image)
- :white_check_mark: Six deep research tools (start, get_results, check_status, estimate_cost, cancel, save_to_markdown)
- :white_check_mark: Official Anthropic MCP SDK integration
- :white_check_mark: Modern Google Gen AI SDK (v3.0.0) migration completed
- :white_check_mark: Multimodal capabilities (video + image analysis)
- :white_check_mark: Image tool supports multiple input methods (file, URL, base64)
- :white_check_mark: Proper error handling and graceful degradation
- :white_check_mark: SQLite retry logic with exponential backoff
- :white_check_mark: Comprehensive documentation and Memory Bank system
- :white_check_mark: Easy setup and configuration process
- :white_check_mark: 42 integration tests passing (all flows covered)

## Technical Constraints
- Must use official Anthropic MCP SDK (v0.5.0+)
- Must use modern Google Gen AI SDK (google-genai>=0.3.0)
- Requires valid Gemini API key for operation
- Python 3.12+ compatibility
- Minimal dependencies for easy deployment

## Project Scope

### In Scope
- Core MCP server implementation
- Seven primary Gemini tools (including web research with grounding, video analysis, image interpretation)
- Six deep research tools (hybrid sync-to-async research, status checking, cost estimation, cancellation, markdown export)
- Multimodal capabilities (video and image processing)
- Multiple image input methods (file paths, URLs, base64 data URIs)
- SQLite state persistence with WAL mode and retry logic
- Cross-platform desktop notifications
- asyncio background task management
- Jinja2 templated markdown reports
- Configuration management
- Error handling and logging with retry mechanisms
- Setup automation scripts
- Memory Bank documentation system
- Comprehensive integration test suite

### Out of Scope
- GUI/web interface
- Advanced Gemini model fine-tuning
- Multi-user authentication
- Custom model hosting
- Real-time streaming of research progress (polling-based status checking instead)

## Key Deliverables
1. Functional MCP server (`server.py`) with modern SDK
2. Configuration generation script (`generate_config.sh`)
3. Environment setup documentation
4. Tool usage examples and LLM interaction guide
5. Error handling patterns
6. Memory Bank documentation system
7. Modern dependency management (uv + pyproject.toml)

## Risk Mitigation
- **API Key Security**: Environment-based configuration, no hardcoded keys
- **Service Availability**: Graceful degradation when Gemini API unavailable
- **Version Compatibility**: Pin to specific MCP SDK and Google Gen AI SDK versions
- **Setup Complexity**: Automated configuration generation

## Project Status
**Current Phase**: Production Ready - Feature Complete
**Version**: 3.7.0 (Hybrid Deep Research System - COMPLETE)
**Last Major Update**: Completed Feature 001-hybrid-deep-research with all 13 waves (SQLite retry logic, version bump, 6 new deep research tools, 42 integration tests passing)