#!/usr/bin/env python3
"""
Gemini MCP Server v3.6.0
Enables a primary AI assistant to collaborate with Google's Gemini AI using the modern unified Google Gen AI SDK
"""

import os
import base64
from typing import Optional, List, Union
from pathlib import Path
from dotenv import load_dotenv
from fastmcp import FastMCP
import mimetypes
import tempfile

# Build an absolute path to the .env file
# This ensures it's found regardless of the script's working directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Server version
__version__ = "3.6.0"

# Initialize MCP server
mcp = FastMCP("Gemini MCP Server", version=__version__)

# Initialize Gemini with new unified SDK
try:
    from google import genai
    from google.genai import types
    
    # Get API key from environment
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        GEMINI_AVAILABLE = False
        GEMINI_ERROR = "GEMINI_API_KEY not set in environment or .env file"
        client = None
    else:
        # Initialize the modern client
        client = genai.Client(api_key=API_KEY)
        GEMINI_AVAILABLE = True
        GEMINI_ERROR = None
except Exception as e:
    GEMINI_AVAILABLE = False
    GEMINI_ERROR = str(e)
    client = None

def call_gemini(prompt: str, temperature: float = 0.5, model: str = "gemini-2.0-flash-001") -> str:
    """Call Gemini using the new unified SDK and return response"""
    if not GEMINI_AVAILABLE or not client:
        return f"Gemini not available: {GEMINI_ERROR}"
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=8192,
            )
        )
        return response.text
    except Exception as e:
        return f"Error calling Gemini: {str(e)}"

@mcp.tool()
def ask_gemini(prompt: str, temperature: float = 0.5) -> str:
    """Ask Gemini a general question and get a direct response for collaboration between AI assistants.

    Use this tool when you need Gemini's perspective, analysis, or expertise on any topic that doesn't
    fit the specialized tools below. This is ideal for:
    - General knowledge questions and explanations
    - Getting a second opinion on technical decisions or approaches
    - Exploring alternative viewpoints or methodologies
    - Discussing best practices, patterns, or architectural choices
    - Asking about technologies, frameworks, or concepts
    - Seeking creative solutions to problems
    - Collaborative problem-solving where two AI perspectives are valuable

    This is the most flexible tool - use it when other specialized tools (code_review, debug,
    brainstorm, research) don't fit your specific need. Think of this as asking a colleague for
    their input or expertise.

    Args:
        prompt: The question or prompt for Gemini. Be specific and provide context for best results.
        temperature: Controls randomness in responses (0.0-1.0, default: 0.5).
                    Lower values (0.2-0.4) = more focused/deterministic responses.
                    Higher values (0.6-0.8) = more creative/varied responses.
    """
    result = call_gemini(prompt, temperature)
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_code_review(code: str, focus_areas: Optional[List[str]] = None) -> str:
    """Request a comprehensive code review from Gemini with detailed feedback on quality, security, and best practices.

    Use this tool specifically when you need expert code analysis and review. This is NOT for debugging
    errors (use gemini_debug for that). Instead, use this when you want to:
    - Get a thorough code quality assessment before committing or deploying
    - Identify potential security vulnerabilities (SQL injection, XSS, auth issues, etc.)
    - Find performance bottlenecks or optimization opportunities
    - Ensure code follows best practices and design patterns
    - Improve code readability, maintainability, and documentation
    - Catch logic bugs, edge cases, or potential runtime issues
    - Get suggestions for refactoring or architectural improvements
    - Review code for compliance with coding standards

    Gemini will provide specific, actionable feedback on issues found, explain WHY they're problems,
    and suggest concrete improvements. The review uses lower temperature (0.2) for consistent,
    analytical feedback.

    Args:
        code: The code snippet or full file to review. Include enough context for meaningful analysis.
        focus_areas: Optional list to narrow the review scope. Examples:
                    ["security"] - Focus only on security vulnerabilities
                    ["performance", "readability"] - Focus on speed and clarity
                    ["best practices", "bugs"] - Focus on correctness and patterns
                    If omitted, provides a comprehensive review of all aspects.
    """
    focus = ", ".join(focus_areas) if focus_areas else "general code quality"
    
    prompt = f"""Please review this code with a focus on {focus}:

```
{code}
```

Provide specific, actionable feedback on:
1. Potential issues or bugs
2. Security concerns (if applicable)
3. Performance optimizations
4. Best practices
5. Code clarity and maintainability

Please be thorough but concise in your analysis."""
    
    result = call_gemini(prompt, 0.2)  # Lower temperature for analytical tasks
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_brainstorm(topic: str, context: str = "") -> str:
    """Engage Gemini in creative brainstorming to generate innovative ideas, solutions, and alternatives.

    Use this tool when you need creative, out-of-the-box thinking and want to explore multiple
    approaches or solutions. This is perfect for:
    - Generating multiple solution approaches to a problem
    - Exploring architectural options and trade-offs for a new feature
    - Coming up with creative naming ideas for projects, functions, or variables
    - Brainstorming test cases, edge cases, or scenarios to consider
    - Thinking through user experience flows and alternatives
    - Generating ideas for improving existing systems or workflows
    - Exploring "what if" scenarios and their implications
    - Finding creative ways to work around constraints or limitations
    - Discovering novel approaches to challenging technical problems

    This tool uses higher temperature (0.7) to encourage diverse, creative responses. Gemini will
    provide multiple alternatives, consider various angles, and think innovatively rather than
    converging on a single "correct" answer.

    Args:
        topic: The specific topic or problem to brainstorm about. Be clear about what you need ideas for.
        context: Additional background information, constraints, or requirements to guide the brainstorming.
                Include things like: current situation, limitations, goals, preferences, or related context
                that will help generate more relevant and practical ideas.
    """
    prompt = f"Let's brainstorm about: {topic}"
    if context:
        prompt += f"\n\nContext: {context}"
    prompt += "\n\nProvide creative ideas, alternatives, and considerations. Think outside the box and offer innovative solutions."
    
    result = call_gemini(prompt, 0.7)  # Higher temperature for creativity
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_debug(error_message: str, code_snippet: str = "", context: str = "") -> str:
    """Get expert debugging assistance from Gemini to diagnose errors, find root causes, and get fix recommendations.

    Use this tool specifically when you encounter runtime errors, exceptions, or unexpected behavior
    that needs diagnosis. This is NOT for code review (use gemini_code_review for that). Use this when:
    - You have an error message or exception that needs analysis
    - Your code is failing and you need to identify the root cause
    - You're getting unexpected behavior and need help diagnosing why
    - Stack traces are confusing and you need help interpreting them
    - You need step-by-step guidance on fixing a specific bug
    - You want to understand WHY an error is occurring, not just how to fix it
    - You're stuck debugging and need a fresh perspective on the problem

    Gemini will systematically analyze the error, identify the root cause, pinpoint the problematic
    code, provide a fix, and suggest preventive measures. Uses lower temperature (0.2) for precise,
    analytical debugging.

    Args:
        error_message: The complete error message, exception, or stack trace. Include ALL details:
                      exception type, message, line numbers, and full stack trace if available.
        code_snippet: The relevant code that's causing the error. Include surrounding context (5-10 lines
                     before/after) so Gemini can understand how the code is being used.
        context: Additional details about the error situation:
                - When does the error occur? (startup, specific user action, certain inputs)
                - What were you trying to do when it failed?
                - What have you already tried?
                - Any relevant environment details (OS, versions, configuration)
                - Does it happen consistently or intermittently?
    """
    prompt = f"""I'm encountering a programming error and need help debugging.

Error Message:
---
{error_message}
---"""

    if code_snippet:
        prompt += f"""

Code Snippet:
---
{code_snippet}
---"""

    if context:
        prompt += f"""

Additional Context:
---
{context}
---"""

    prompt += """

Based on the error message and the provided information, please do the following:
1. **Analyze the Root Cause**: Explain what you believe is the most likely cause of this error.
2. **Identify the Problematic Code**: Pinpoint the specific line(s) or code block(s) that are causing the issue.
3. **Suggest a Solution**: Provide a corrected version of the code or clear, step-by-step instructions on how to fix the bug.
4. **Prevention**: Suggest how to prevent similar errors in the future."""
    
    result = call_gemini(prompt, 0.2)  # Lower temperature for systematic analysis
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_research(topic: str) -> str:
    """Conduct fact-based research using Gemini with Google Search grounding for current, verified information.

    Use this tool when you need factual, up-to-date information that's grounded in real-world sources.
    This is NOT for general questions (use ask_gemini) or creative brainstorming. Use this when you need:
    - Current information about recent events, technologies, or developments
    - Factual research on specific topics, products, or technologies
    - Verification of claims or statements with web sources
    - Information about latest versions, releases, or updates
    - Market research, trends, or industry analysis
    - Documentation or specifications that are published online
    - Comparative analysis of tools, frameworks, or approaches based on real data
    - Finding examples, case studies, or real-world implementations
    - Getting information that changes frequently (pricing, features, availability)

    This tool uses Google Search grounding to ensure responses are backed by current web information
    rather than just training data. Responses will reference real sources when possible. Uses lower
    temperature (0.3) for factual accuracy.

    IMPORTANT: This requires Gemini's grounding features to be enabled on your API key. If grounding
    is not available, it will fall back to regular Gemini (still useful, but without live search).

    Args:
        topic: The specific topic or question to research. Be clear and specific about what information
              you need. Include relevant context like: technology names, version numbers, timeframes,
              or specific aspects you're interested in.
    """
    if not GEMINI_AVAILABLE or not client:
        return f"Gemini not available: {GEMINI_ERROR}"
    
    try:
        # Use the new SDK grounding functionality
        # Note: Grounding may require specific model and API access
        grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",  # Model that supports grounding
            contents=topic,
            config=types.GenerateContentConfig(
                tools=[grounding_tool],
                temperature=0.3,  # Lower temperature for factual research
            )
        )
        
        return f"🤖 GEMINI RESEARCH RESPONSE:\n\n{response.text}"
    except Exception as e:
        # Fallback to regular content generation if grounding fails
        result = call_gemini(f"Research and provide current information about: {topic}", 0.3)
        return f"🤖 GEMINI RESEARCH RESPONSE (fallback):\n\n{result}\n\n[Note: Used fallback mode - grounding may not be available]"

def is_image_url(url: str) -> bool:
    """Check if a string is a valid image URL"""
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    # Check if URL ends with common image extensions
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
    return any(url.lower().endswith(ext) for ext in image_extensions) or 'image' in url.lower()

def is_base64_image(data: str) -> bool:
    """Check if a string is a base64-encoded image (starts with data:image/)"""
    return data.startswith("data:image/")

@mcp.tool()
def interpret_image(
    image_path: Union[str, List[str]],
    prompt: str = "Describe this image in detail",
    temperature: float = 0.5
) -> str:
    """Analyze and interpret images using Gemini's advanced vision capabilities to understand visual content.

    Use this tool when you need to extract information from images, understand visual content, or analyze
    screenshots, diagrams, charts, or photos. Supports single or multiple images (up to 3,600 per request).
    Perfect for:
    - Describing what's visible in photos, screenshots, or diagrams
    - Reading and extracting text from images (OCR functionality)
    - Analyzing UI/UX designs and providing feedback
    - Understanding charts, graphs, or data visualizations
    - Identifying objects, people, or elements in images
    - Comparing multiple images to find differences or similarities
    - Analyzing code screenshots or error messages shown visually
    - Understanding architectural diagrams, flowcharts, or technical drawings
    - Examining design mockups or wireframes
    - Analyzing medical images, scientific diagrams, or specialized visuals (within Gemini's capabilities)

    This tool automatically handles different image sources and sizes:
    - Local files are read directly (files >20MB use file upload API)
    - URLs are fetched and processed automatically
    - Base64-encoded images are decoded inline
    - Multiple images can be analyzed together for comparison or combined analysis

    Args:
        image_path: Can be ONE of:
                   - Single image: str (file path, URL, or base64-encoded)
                   - Multiple images: List[str] (mix of any supported formats)

                   Supported formats:
                   - Local file path: "/path/to/image.jpg", "./screenshot.png"
                   - Direct URL: "https://example.com/image.png"
                   - Base64-encoded: "data:image/jpeg;base64,/9j/4AAQ..."

                   Supported image types: jpg, jpeg, png, gif, webp, bmp

        prompt: What you want to know about the image(s). Be specific for best results:
                Single image examples:
                - "What text is visible in this screenshot?"
                - "Describe the architecture shown in this diagram"
                - "What errors or issues can you identify in this code screenshot?"

                Multiple image examples:
                - "Compare these two designs and list the differences"
                - "Which of these UI mockups follows better design principles?"
                - "Analyze the progression shown across these images"

        temperature: Controls response creativity (0.0-1.0, default: 0.5)
                    Lower (0.2-0.4) for factual descriptions, OCR, or technical analysis
                    Higher (0.6-0.8) for creative interpretations or subjective analysis

    Returns:
        Gemini's detailed analysis of the image(s), including descriptions, text extraction,
        observations, and answers to your specific questions.

    Examples:
        # Analyze a single screenshot
        interpret_image("/path/to/error.png", "What error is shown and how can I fix it?")

        # Compare multiple designs
        interpret_image(
            ["/path/to/design_v1.png", "/path/to/design_v2.png"],
            "Compare these two designs. Which is more user-friendly and why?"
        )

        # Extract text from an image
        interpret_image("https://example.com/document.jpg", "Extract all text from this image")

        # Mix of local and remote images
        interpret_image(
            ["/path/to/local.jpg", "https://example.com/remote.png"],
            "What are the common themes across these images?"
        )
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    try:
        # Normalize input to list (support both single and multiple images)
        image_paths = [image_path] if isinstance(image_path, str) else image_path

        # Validate image count (Gemini supports up to 3,600 images)
        if len(image_paths) > 3600:
            return f"🤖 GEMINI RESPONSE:\n\nError: Too many images ({len(image_paths)}). Maximum is 3,600 images per request."

        # Build contents array with all images
        contents = []
        image_info = []
        uploaded_files = []  # Track uploaded files for cleanup

        for idx, img_path in enumerate(image_paths, 1):
            # Handle base64-encoded images
            if is_base64_image(img_path):
                header, base64_data = img_path.split(',', 1)
                mime_type = header.split(';')[0].split(':')[1]
                image_data = base64.b64decode(base64_data)
                file_size_mb = len(image_data) / (1024 * 1024)

                contents.append(types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type
                ))
                image_info.append(f"Image {idx}: Base64 ({file_size_mb:.1f}MB)")

            # Handle image URLs
            elif is_image_url(img_path):
                import urllib.request
                with urllib.request.urlopen(img_path) as url_response:
                    image_data = url_response.read()

                mime_type = url_response.headers.get_content_type()
                if not mime_type or not mime_type.startswith('image/'):
                    mime_type, _ = mimetypes.guess_type(img_path)
                    if not mime_type:
                        mime_type = 'image/jpeg'

                file_size_mb = len(image_data) / (1024 * 1024)
                contents.append(types.Part.from_bytes(
                    data=image_data,
                    mime_type=mime_type
                ))
                image_info.append(f"Image {idx}: URL ({file_size_mb:.1f}MB)")

            # Handle local file paths
            else:
                if not os.path.exists(img_path):
                    return f"🤖 GEMINI RESPONSE:\n\nError: Image {idx} not found: '{img_path}'"

                file_path = Path(img_path)
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if not mime_type or not mime_type.startswith('image/'):
                    return f"🤖 GEMINI RESPONSE:\n\nError: Image {idx} is not a valid image file: '{img_path}' (detected type: {mime_type})"

                file_size = file_path.stat().st_size
                file_size_mb = file_size / (1024 * 1024)

                # For files > 20MB, use File API
                if file_size_mb > 20:
                    uploaded_file = client.files.upload(
                        file=str(file_path),
                        config=types.UploadFileConfig(display_name=file_path.name)
                    )
                    uploaded_files.append(uploaded_file)

                    contents.append(types.Part.from_uri(
                        file_uri=uploaded_file.uri,
                        mime_type=mime_type
                    ))
                    image_info.append(f"Image {idx}: {file_path.name} ({file_size_mb:.1f}MB, uploaded)")
                else:
                    with open(file_path, 'rb') as f:
                        image_data = f.read()

                    contents.append(types.Part.from_bytes(
                        data=image_data,
                        mime_type=mime_type
                    ))
                    image_info.append(f"Image {idx}: {file_path.name} ({file_size_mb:.1f}MB)")

        # Add the prompt to contents
        contents.append(prompt)

        # Send all images to Gemini in one request
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=8192,
            )
        )

        # Clean up uploaded files
        for uploaded_file in uploaded_files:
            client.files.delete(name=uploaded_file.name)

        # Format response
        image_count = len(image_paths)
        if image_count == 1:
            header = f"🤖 GEMINI IMAGE ANALYSIS ({image_info[0].replace('Image 1: ', '')}):"
        else:
            header = f"🤖 GEMINI MULTI-IMAGE ANALYSIS ({image_count} images):\n" + "\n".join(f"  • {info}" for info in image_info) + "\n"

        return f"{header}\n\n{response.text}"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError analyzing image(s): {str(e)}"

@mcp.tool()
def server_info() -> str:
    """Check Gemini MCP server status, connectivity, and configuration information.

    Use this tool to verify that the Gemini MCP server is properly configured and operational.
    This is helpful for:
    - Diagnosing connection issues with the Gemini API
    - Checking if the API key is properly configured
    - Verifying the server version
    - Troubleshooting when other Gemini tools are not working
    - Getting basic health check information

    Returns information about server version, Gemini API connectivity, and any error messages
    if the service is not available.
    """
    if GEMINI_AVAILABLE:
        return f"🤖 GEMINI RESPONSE:\n\nServer v{__version__} - Gemini connected and ready! Using modern unified Google Gen AI SDK."
    else:
        return f"🤖 GEMINI RESPONSE:\n\nServer v{__version__} - Gemini error: {GEMINI_ERROR}"

@mcp.tool()
def check_file_status(file_name: str) -> str:
    """Check the processing status of an uploaded file in Gemini.

    Use this tool to verify if an uploaded file (video, image, document) is ready for use
    in Gemini API calls. This is essential for large files that require processing time.

    Perfect for:
    - Checking if a large video file has finished processing
    - Verifying file upload success before analysis
    - Debugging file upload issues
    - Monitoring processing progress for multiple files
    - Reusing previously uploaded files

    File States:
    - PROCESSING: File is being uploaded/indexed (not ready yet)
    - ACTIVE: File is ready for use in generate_content calls ✅
    - FAILED: File processing failed ❌
    - STATE_UNSPECIFIED: Unknown state

    Args:
        file_name: File identifier from upload (format: "files/abc123xyz").
                  This is returned when you upload a file or can be found in
                  previous upload responses.

    Returns:
        JSON-formatted string with:
        - state: Current processing state
        - ready: Boolean indicating if file is ready for use
        - file_name: File identifier
        - display_name: Human-readable name (if available)
        - size_bytes: File size in bytes
        - size_mb: File size in megabytes
        - mime_type: File MIME type
        - create_time: Upload timestamp
        - uri: File URI for API calls

    Example:
        # After uploading a large video
        status = check_file_status("files/abc123xyz")
        # Returns: {"state": "ACTIVE", "ready": true, "size_mb": 450, ...}
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    try:
        # Get file metadata
        file_info = client.files.get(name=file_name)

        # Determine if file is ready
        is_ready = file_info.state == "ACTIVE"

        # Build comprehensive status response
        status = {
            "state": file_info.state,
            "ready": is_ready,
            "file_name": file_info.name,
            "display_name": getattr(file_info, 'display_name', 'N/A'),
            "size_bytes": getattr(file_info, 'size_bytes', 0),
            "size_mb": round(getattr(file_info, 'size_bytes', 0) / (1024 * 1024), 2),
            "mime_type": getattr(file_info, 'mime_type', 'unknown'),
            "create_time": str(getattr(file_info, 'create_time', 'N/A')),
            "uri": file_info.uri,
        }

        # Add friendly message based on state
        if file_info.state == "ACTIVE":
            message = "✅ File is ready for use!"
        elif file_info.state == "PROCESSING":
            message = "⏳ File is still processing. Check again in a few seconds."
        elif file_info.state == "FAILED":
            message = "❌ File processing failed. Please try uploading again."
        else:
            message = f"⚠️ File state: {file_info.state}"

        status["message"] = message

        import json
        return f"🤖 GEMINI FILE STATUS:\n\n{json.dumps(status, indent=2)}"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError checking file status: {str(e)}\n\nMake sure the file_name is correct (format: 'files/abc123xyz')"

@mcp.tool()
def list_uploaded_files(
    filter_mime_type: Optional[str] = None,
    sort_by: str = "upload_date",
    max_results: int = 20
) -> str:
    """List all files currently stored in Gemini cloud storage for browsing and selection.

    This tool enables the primary AI assistant (Claude Code) to help users discover,
    browse, and select from their uploaded files. Essential for conversational workflows
    where users want to see what's available before choosing which file to analyze.

    **IMPORTANT: 48-Hour File Retention**
    - All uploaded files are automatically deleted after 48 hours
    - This tool shows expiration times to help prioritize analysis
    - Files marked "expires_soon" have less than 6 hours remaining

    **Use this tool when users ask:**
    - "What videos do I have uploaded?"
    - "Show me my uploaded files"
    - "Which files are about to expire?"
    - "Do I have any old uploads I should clean up?"
    - "What was I working on yesterday?"

    **Perfect for:**
    - Helping users choose which file to analyze from multiple uploads
    - Identifying files that are about to expire (< 6 hours remaining)
    - Storage management and cleanup decisions
    - Finding files by type (videos, images, documents)
    - Showing upload history and timeline

    **Storage Limits:**
    - 20 GB total per project
    - 2 GB maximum per individual file
    - Files auto-delete after 48 hours

    Args:
        filter_mime_type: Filter by MIME type pattern. Examples:
                         - "video/*" - Only show videos
                         - "video/mp4" - Only MP4 videos
                         - "image/*" - Only show images
                         - "application/pdf" - Only PDFs
                         - None - Show all files (default)

        sort_by: Sort order for results. Options:
                - "upload_date" - Newest first (default, most useful)
                - "size" - Largest files first
                - "name" - Alphabetical by display name
                - "expiring" - Files expiring soonest first

        max_results: Maximum number of files to return (default: 20, max: 100).
                    For large storage, use pagination by calling multiple times.

    Returns:
        JSON-formatted string containing:
        - total_files: Total count of files in storage
        - filtered_count: Count after applying mime_type filter
        - storage_used_mb: Total storage used in megabytes
        - files: List of file objects with metadata
        - expiring_soon_count: Files with < 6 hours remaining

        Each file object includes:
        - file_name: Gemini file identifier (use with other tools)
        - display_name: Human-readable filename
        - state: "ACTIVE", "PROCESSING", or "FAILED"
        - mime_type: File type (video/mp4, image/jpeg, etc.)
        - size_mb: File size in megabytes
        - uploaded: ISO timestamp of upload
        - age_hours: Hours since upload
        - expires_in_hours: Hours until auto-deletion (48hr limit)
        - ready_for_analysis: Boolean - can be analyzed now?

    Example Workflows:
        # User: "What videos do I have?"
        list_uploaded_files(filter_mime_type="video/*")
        # Claude shows: "You have 3 videos: athena_recording.mp4 (12hr old),
        #                demo_video.mp4 (40hr old, expires in 8hr)..."

        # User: "Show me files that are about to expire"
        list_uploaded_files(sort_by="expiring")
        # Claude shows: "2 files expiring soon: demo.mp4 in 3 hours..."

        # User: "What's in my storage?"
        list_uploaded_files()
        # Claude shows: "You have 5 files using 1.2GB..."
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    import json
    from datetime import datetime, timezone

    try:
        # List all files
        all_files = list(client.files.list(config={'page_size': max_results}))

        # Filter by mime type if specified
        if filter_mime_type:
            if filter_mime_type.endswith("/*"):
                # Wildcard filter (e.g., "video/*")
                prefix = filter_mime_type[:-2]
                filtered_files = [f for f in all_files if getattr(f, 'mime_type', '').startswith(prefix)]
            else:
                # Exact match
                filtered_files = [f for f in all_files if getattr(f, 'mime_type', '') == filter_mime_type]
        else:
            filtered_files = all_files

        # Build file list with metadata
        file_list = []
        total_size = 0
        expiring_soon_count = 0

        for f in filtered_files:
            # Calculate age and expiration
            create_time = getattr(f, 'create_time', None)
            if create_time:
                # Parse ISO timestamp
                if isinstance(create_time, str):
                    uploaded_dt = datetime.fromisoformat(create_time.replace('Z', '+00:00'))
                else:
                    uploaded_dt = create_time

                now = datetime.now(timezone.utc)
                age_delta = now - uploaded_dt
                age_hours = age_delta.total_seconds() / 3600
                expires_in_hours = 48 - age_hours
            else:
                age_hours = 0
                expires_in_hours = 48

            size_bytes = getattr(f, 'size_bytes', 0)
            size_mb = round(size_bytes / (1024 * 1024), 2)
            total_size += size_bytes

            is_expiring_soon = expires_in_hours < 6
            if is_expiring_soon:
                expiring_soon_count += 1

            file_info = {
                "file_name": f.name,
                "display_name": getattr(f, 'display_name', f.name),
                "state": f.state,
                "mime_type": getattr(f, 'mime_type', 'unknown'),
                "size_mb": size_mb,
                "uploaded": str(create_time) if create_time else "N/A",
                "age_hours": round(age_hours, 1),
                "expires_in_hours": round(expires_in_hours, 1),
                "expires_soon": is_expiring_soon,
                "ready_for_analysis": f.state == "ACTIVE"
            }
            file_list.append(file_info)

        # Sort files
        if sort_by == "upload_date":
            file_list.sort(key=lambda x: x['age_hours'])  # Newest first
        elif sort_by == "size":
            file_list.sort(key=lambda x: x['size_mb'], reverse=True)
        elif sort_by == "name":
            file_list.sort(key=lambda x: x['display_name'])
        elif sort_by == "expiring":
            file_list.sort(key=lambda x: x['expires_in_hours'])

        # Build response
        result = {
            "total_files": len(all_files),
            "filtered_count": len(filtered_files),
            "storage_used_mb": round(total_size / (1024 * 1024), 2),
            "expiring_soon_count": expiring_soon_count,
            "files": file_list,
            "storage_info": {
                "retention_policy": "48 hours",
                "max_storage_gb": 20,
                "max_file_size_gb": 2
            }
        }

        if filter_mime_type:
            result["filter_applied"] = filter_mime_type

        return f"🤖 GEMINI STORAGE LISTING:\n\n{json.dumps(result, indent=2)}"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError listing files: {str(e)}"

@mcp.tool()
def get_last_uploaded_video() -> str:
    """Get the most recently uploaded video file from Gemini storage.

    This is a convenience tool for quick access to the user's latest video upload
    without having to browse through all files. Specifically filters for video
    files and returns only the most recent one.

    **Use this tool when users ask:**
    - "What was the last video I uploaded?"
    - "Is my recent video upload ready?"
    - "Can I analyze that video I just uploaded?"
    - "Show me my latest upload"
    - "What video was I working on?"

    **Perfect for:**
    - Quick access to most recent video without listing all files
    - Checking if a recent upload is ready for analysis
    - Continuing work from a previous session
    - Verifying upload success
    - Getting file URI for immediate analysis

    **Returns information about:**
    - File identifier (for use with watch_video or check_file_status)
    - Processing state (ACTIVE, PROCESSING, FAILED)
    - Upload time and age
    - Expiration time (48-hour limit)
    - Size and format
    - Whether it's ready for analysis

    Returns:
        JSON-formatted string containing:
        - found: Boolean - whether a video was found
        - file_name: Gemini file identifier (e.g., "files/abc123")
        - display_name: Human-readable filename
        - state: Current processing state
        - ready: Boolean - ready for analysis?
        - mime_type: Video format
        - size_mb: File size in megabytes
        - uploaded: ISO timestamp
        - age_hours: Hours since upload
        - expires_in_hours: Hours until auto-deletion
        - uri: File URI for API calls
        - suggestion: Message for Claude to relay to user

    Example Workflows:
        # User: "Is my latest video ready?"
        get_last_uploaded_video()
        # Returns: {"found": true, "state": "ACTIVE", "ready": true, ...}
        # Claude: "Yes! Your athena_recording.mp4 is ready. Would you like
        #          me to analyze it?"

        # User: "What was I working on yesterday?"
        get_last_uploaded_video()
        # Returns: {"found": true, "age_hours": 36, ...}
        # Claude: "Your last video was demo.mp4, uploaded 36 hours ago.
        #          It expires in 12 hours."

        # No videos found
        get_last_uploaded_video()
        # Returns: {"found": false, "message": "No videos in storage"}
        # Claude: "You don't have any videos uploaded currently."
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    import json
    from datetime import datetime, timezone

    try:
        # List all files
        all_files = list(client.files.list(config={'page_size': 100}))

        # Filter for videos only
        video_files = [f for f in all_files if getattr(f, 'mime_type', '').startswith('video/')]

        if not video_files:
            return f"🤖 GEMINI RESPONSE:\n\n{json.dumps({'found': False, 'message': 'No videos found in storage. Upload a video first with watch_video().'}, indent=2)}"

        # Get most recent video (by create_time)
        video_files.sort(key=lambda f: getattr(f, 'create_time', ''), reverse=True)
        latest_video = video_files[0]

        # Calculate metadata
        create_time = getattr(latest_video, 'create_time', None)
        if create_time:
            if isinstance(create_time, str):
                uploaded_dt = datetime.fromisoformat(create_time.replace('Z', '+00:00'))
            else:
                uploaded_dt = create_time

            now = datetime.now(timezone.utc)
            age_delta = now - uploaded_dt
            age_hours = age_delta.total_seconds() / 3600
            expires_in_hours = 48 - age_hours
        else:
            age_hours = 0
            expires_in_hours = 48

        size_bytes = getattr(latest_video, 'size_bytes', 0)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        is_ready = latest_video.state == "ACTIVE"

        # Build suggestion message
        if is_ready:
            suggestion = f"✅ This video is ready for analysis. Call: watch_video(file_uri='{latest_video.name}', prompt='...')"
        elif latest_video.state == "PROCESSING":
            suggestion = f"⏳ Video is still processing. Check status with: check_file_status('{latest_video.name}')"
        else:
            suggestion = f"❌ Video processing failed (state: {latest_video.state}). Try uploading again."

        result = {
            "found": True,
            "file_name": latest_video.name,
            "display_name": getattr(latest_video, 'display_name', latest_video.name),
            "state": latest_video.state,
            "ready": is_ready,
            "mime_type": getattr(latest_video, 'mime_type', 'unknown'),
            "size_mb": size_mb,
            "uploaded": str(create_time) if create_time else "N/A",
            "age_hours": round(age_hours, 1),
            "expires_in_hours": round(expires_in_hours, 1),
            "expires_soon": expires_in_hours < 6,
            "uri": latest_video.uri,
            "suggestion": suggestion
        }

        return f"🤖 GEMINI LAST VIDEO:\n\n{json.dumps(result, indent=2)}"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError getting last video: {str(e)}"

@mcp.tool()
def delete_uploaded_file(file_name: str, confirmed: bool = False) -> str:
    """Delete a specific file from Gemini cloud storage.

    ⚠️ **DESTRUCTIVE OPERATION** - Requires explicit confirmation via the `confirmed` parameter.

    This tool enables manual cleanup of uploaded files to free storage space or remove
    files that are no longer needed. Files are automatically deleted after 48 hours,
    but this tool allows earlier manual deletion.

    **IMPORTANT: Safety Measures**
    - Requires `confirmed=True` to actually delete
    - First call without confirmation returns file info for review
    - Cannot be undone - deleted files are permanently removed
    - User should be asked to confirm before setting confirmed=True

    **Use this tool when users ask:**
    - "Delete that old video"
    - "Remove the demo file"
    - "Clean up my uploads"
    - "I don't need that file anymore"
    - "Free up storage space"

    **Perfect for:**
    - Cleaning up test uploads
    - Removing files no longer needed
    - Freeing storage space before hitting 20GB limit
    - Deleting failed or corrupted uploads
    - Managing storage proactively

    **Typical Workflow:**
    1. User requests deletion: "Delete the demo video"
    2. Claude calls: delete_uploaded_file("files/abc123", confirmed=False)
    3. Tool returns file info for confirmation
    4. Claude asks user: "This will delete demo.mp4 (450MB). Confirm?"
    5. User confirms: "Yes, delete it"
    6. Claude calls: delete_uploaded_file("files/abc123", confirmed=True)
    7. File is permanently deleted

    Args:
        file_name: File identifier to delete (format: "files/abc123xyz").
                  Get this from list_uploaded_files() or get_last_uploaded_video().

        confirmed: Safety flag - must be True to actually delete the file.
                  - False (default): Returns file info for review, does NOT delete
                  - True: Permanently deletes the file (cannot be undone)

    Returns:
        JSON-formatted string containing:
        - If confirmed=False:
          - action: "confirmation_required"
          - file details for review
          - warning message about permanent deletion

        - If confirmed=True:
          - action: "deleted"
          - deleted_file: Name of deleted file
          - success: true/false
          - freed_storage_mb: Storage space freed

    Example Workflows:
        # Step 1: User wants to delete
        # User: "Delete that old demo video"
        # Claude first lists to identify: list_uploaded_files()
        # Claude identifies: "files/xyz" is the demo video

        # Step 2: Claude checks what will be deleted
        delete_uploaded_file("files/xyz", confirmed=False)
        # Returns: {"action": "confirmation_required", "file_name": "demo.mp4",
        #           "size_mb": 450, "warning": "This will permanently delete..."}

        # Step 3: Claude asks user
        # Claude: "This will permanently delete demo.mp4 (450MB). Confirm?"
        # User: "Yes"

        # Step 4: Claude deletes
        delete_uploaded_file("files/xyz", confirmed=True)
        # Returns: {"action": "deleted", "success": true, "freed_storage_mb": 450}
        # Claude: "Deleted demo.mp4 and freed 450MB of storage."

    Safety Notes:
        - Always call with confirmed=False first to verify what will be deleted
        - Ask user to explicitly confirm before calling with confirmed=True
        - Consider showing file details (name, size, age) before deletion
        - Cannot recover deleted files - make sure user is certain
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    import json

    try:
        # First, get file info
        file_info = client.files.get(name=file_name)
        size_bytes = getattr(file_info, 'size_bytes', 0)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        display_name = getattr(file_info, 'display_name', file_name)

        # If not confirmed, return info for review
        if not confirmed:
            result = {
                "action": "confirmation_required",
                "file_name": file_name,
                "display_name": display_name,
                "size_mb": size_mb,
                "mime_type": getattr(file_info, 'mime_type', 'unknown'),
                "warning": "⚠️ This will PERMANENTLY delete this file. It cannot be recovered.",
                "message": f"To confirm deletion, call: delete_uploaded_file('{file_name}', confirmed=True)"
            }
            return f"🤖 GEMINI DELETE CONFIRMATION:\n\n{json.dumps(result, indent=2)}"

        # Confirmed - actually delete the file
        client.files.delete(name=file_name)

        result = {
            "action": "deleted",
            "success": True,
            "deleted_file": file_name,
            "display_name": display_name,
            "freed_storage_mb": size_mb,
            "message": f"✅ Successfully deleted {display_name} and freed {size_mb}MB of storage."
        }

        return f"🤖 GEMINI FILE DELETED:\n\n{json.dumps(result, indent=2)}"

    except Exception as e:
        error_result = {
            "action": "error",
            "success": False,
            "file_name": file_name,
            "error": str(e),
            "message": "Failed to delete file. It may have already been deleted or expired (48hr limit)."
        }
        return f"🤖 GEMINI RESPONSE:\n\n{json.dumps(error_result, indent=2)}"

def is_youtube_url(url: str) -> bool:
    """Check if a string is a valid YouTube URL"""
    return (url.startswith("http://") or url.startswith("https://")) and ("youtube.com" in url or "youtu.be" in url)

@mcp.tool()
def watch_video(
    input_path: Optional[str] = None,
    prompt: str = "",
    model: str = "gemini-2.0-flash-001",
    file_uri: Optional[str] = None,
    auto_analyze: bool = True,
    max_wait_seconds: int = 300,
    poll_interval: int = 2
) -> str:
    """Analyze video content from YouTube or local files using Gemini's multimodal capabilities.

    **THREE USAGE MODES:**

    **Mode 1: Full Auto (Default)** - Upload, poll, and analyze automatically
    ```python
    watch_video("/path/to/video.mp4", "Summarize this video")
    # Handles everything: upload → wait → analyze → return results
    ```

    **Mode 2: Upload Only** - Upload and return file info for manual status checking
    ```python
    result = watch_video("/path/to/video.mp4", auto_analyze=False)
    # Returns: {"file_name": "files/abc123", "state": "PROCESSING", ...}
    # Then use check_file_status("files/abc123") to monitor progress
    # Finally: watch_video(file_uri="files/abc123", prompt="Analyze this")
    ```

    **Mode 3: Use Pre-Uploaded File** - Analyze an already-uploaded file
    ```python
    watch_video(file_uri="files/abc123", prompt="Extract key points")
    # Skips upload, checks status once, then analyzes
    ```

    Perfect for:
    - Summarizing video content and key points
    - Extracting specific information from tutorial or educational videos
    - Analyzing presentations, demos, or conference talks
    - Understanding what happens in a video without watching it
    - Transcribing or extracting dialogue from videos
    - Analyzing specific time ranges or segments of longer videos
    - Getting insights from recorded meetings, lectures, or screencasts
    - Identifying actions, objects, or events shown in video footage
    - Comparing content across different parts of a video

    The tool automatically handles different video sources:
    - YouTube URLs are processed directly (no download needed)
    - Local files <20MB are sent inline (no upload/polling needed)
    - Local files >20MB use Gemini's File API with automatic polling
    - Supports common video formats (mp4, mov, avi, etc.)

    Args:
        input_path: Video source - either a YouTube URL or path to a local video file.
                   Required unless file_uri is provided.
                   YouTube examples:
                   - "https://www.youtube.com/watch?v=VIDEO_ID"
                   - "https://youtu.be/VIDEO_ID"
                   Local file examples:
                   - "/path/to/recording.mp4"
                   - "./screencast.mov"

        prompt: What you want to know about the video. Required for analysis.
               General analysis:
               - "Summarize this video in 3-5 key points"
               - "What is this video about?"
               Time-specific analysis:
               - "Summarize from 1:00 to 1:30"
               - "What happens at the 5-minute mark?"
               Specific extraction:
               - "What code examples are shown in this tutorial?"
               - "List all the commands demonstrated in this video"

        model: Gemini model to use (default: gemini-2.0-flash-001).

        file_uri: Use an already-uploaded file instead of uploading a new one.
                 Format: "files/abc123xyz"
                 If provided, input_path is ignored.

        auto_analyze: If True (default), automatically poll for file readiness and analyze.
                     If False, upload file and return file info without analyzing.
                     Useful for large files when you want manual control over timing.

        max_wait_seconds: Maximum time to wait for file processing (default: 300 = 5 minutes).
                         Only applies when auto_analyze=True for large files.

        poll_interval: How often to check file status in seconds (default: 2).
                      Only applies when auto_analyze=True for large files.

    Returns:
        - If auto_analyze=True: Full video analysis from Gemini
        - If auto_analyze=False: JSON with file info {"file_name": "...", "state": "...", ...}
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    import json
    import time

    try:
        # MODE 3: Use pre-uploaded file
        if file_uri:
            # Check file status once
            file_info = client.files.get(name=file_uri)

            if file_info.state != "ACTIVE":
                return f"🤖 GEMINI RESPONSE:\n\nFile {file_uri} is not ready (state: {file_info.state}). Use check_file_status('{file_uri}') to monitor progress."

            if not prompt:
                return f"🤖 GEMINI RESPONSE:\n\nError: 'prompt' parameter is required when analyzing a video."

            # File is ready, analyze it
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_uri(
                        file_uri=file_info.uri,
                        mime_type=file_info.mime_type
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=8192,
                )
            )
            return f"🤖 GEMINI VIDEO ANALYSIS (Pre-uploaded: {file_uri}):\n\n{response.text}"

        # Validate input_path is provided
        if not input_path:
            return f"🤖 GEMINI RESPONSE:\n\nError: Either 'input_path' or 'file_uri' must be provided."

        # Handle YouTube URLs
        if is_youtube_url(input_path):
            if not prompt:
                return f"🤖 GEMINI RESPONSE:\n\nError: 'prompt' parameter is required when analyzing a video."

            # For YouTube videos, include URL in the prompt
            full_prompt = f"{prompt}\n\nAnalyze this YouTube video: {input_path}"

            response = client.models.generate_content(
                model=model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=8192,
                )
            )
            return f"🤖 GEMINI VIDEO ANALYSIS (YouTube):\n\n{response.text}"

        # Handle local video files
        elif os.path.exists(input_path):
            file_path = Path(input_path)

            # Check if it's a video file
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type or not mime_type.startswith('video/'):
                return f"🤖 GEMINI RESPONSE:\n\nError: File '{input_path}' is not a valid video file (detected type: {mime_type})"

            # Get file size to determine upload method
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            # For files > 20MB, use the File API with polling
            if file_size_mb > 20:
                # Upload the file first
                uploaded_file = client.files.upload(
                    file=str(file_path),
                    config=types.UploadFileConfig(display_name=file_path.name)
                )

                # MODE 2: Upload only (return file info without analyzing)
                if not auto_analyze:
                    upload_info = {
                        "mode": "upload_only",
                        "file_name": uploaded_file.name,
                        "file_uri": uploaded_file.uri,
                        "state": uploaded_file.state,
                        "size_mb": file_size_mb,
                        "message": f"File uploaded. Use check_file_status('{uploaded_file.name}') to monitor processing, then call watch_video(file_uri='{uploaded_file.name}', prompt='...') when ready."
                    }
                    return f"🤖 GEMINI FILE UPLOAD:\n\n{json.dumps(upload_info, indent=2)}"

                # MODE 1: Auto-analyze (poll until ready)
                if not prompt:
                    return f"🤖 GEMINI RESPONSE:\n\nError: 'prompt' parameter is required when auto_analyze=True."

                # Poll for file readiness
                elapsed_time = 0
                file_obj = uploaded_file

                while file_obj.state == "PROCESSING" and elapsed_time < max_wait_seconds:
                    time.sleep(poll_interval)
                    elapsed_time += poll_interval
                    file_obj = client.files.get(name=uploaded_file.name)

                # Check final state
                if file_obj.state == "FAILED":
                    return f"🤖 GEMINI RESPONSE:\n\nError: File processing failed. Please try uploading again."

                if file_obj.state != "ACTIVE":
                    return f"🤖 GEMINI RESPONSE:\n\nTimeout: File is still processing after {elapsed_time} seconds (state: {file_obj.state}). Use check_file_status('{uploaded_file.name}') to continue monitoring."

                # File is ready, analyze it
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_uri(
                            file_uri=file_obj.uri,
                            mime_type=mime_type
                        ),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.5,
                        max_output_tokens=8192,
                    )
                )

                # Clean up the uploaded file
                client.files.delete(name=file_obj.name)

                return f"🤖 GEMINI VIDEO ANALYSIS (Local file: {file_path.name}, {file_size_mb:.1f}MB, processed in {elapsed_time}s):\n\n{response.text}"

            else:
                # For smaller files, include inline (no upload/polling needed)
                if not prompt:
                    return f"🤖 GEMINI RESPONSE:\n\nError: 'prompt' parameter is required when analyzing a video."

                with open(file_path, 'rb') as f:
                    video_data = f.read()

                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(
                            data=video_data,
                            mime_type=mime_type
                        ),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.5,
                        max_output_tokens=8192,
                    )
                )

                return f"🤖 GEMINI VIDEO ANALYSIS (Local file: {file_path.name}, {file_size_mb:.1f}MB, inline):\n\n{response.text}"

        else:
            return f"🤖 GEMINI RESPONSE:\n\nError: Input '{input_path}' is neither a valid YouTube URL nor an existing file path"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError analyzing video: {str(e)}"

if __name__ == "__main__":
    mcp.run()