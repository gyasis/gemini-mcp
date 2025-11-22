#!/usr/bin/env python3
"""
Gemini MCP Server v3.4.0
Enables a primary AI assistant to collaborate with Google's Gemini AI using the modern unified Google Gen AI SDK
"""

import os
import base64
from typing import Optional, List, Union
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import mimetypes
import tempfile

# Build an absolute path to the .env file
# This ensures it's found regardless of the script's working directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Server version
__version__ = "3.4.0"

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
                        path=str(file_path),
                        display_name=file_path.name
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

def is_youtube_url(url: str) -> bool:
    """Check if a string is a valid YouTube URL"""
    return (url.startswith("http://") or url.startswith("https://")) and ("youtube.com" in url or "youtu.be" in url)

@mcp.tool()
def watch_video(input_path: str, prompt: str, model: str = "gemini-2.0-flash-001") -> str:
    """Analyze video content from YouTube or local files using Gemini's multimodal capabilities.

    Use this tool when you need to understand, analyze, or extract information from video content.
    Works with both YouTube videos (via URL) and local video files. Perfect for:
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
    - Local files <20MB are sent inline
    - Local files >20MB use Gemini's File API for upload
    - Supports common video formats (mp4, mov, avi, etc.)

    Args:
        input_path: Video source - either a YouTube URL or path to a local video file:
                   YouTube examples:
                   - "https://www.youtube.com/watch?v=VIDEO_ID"
                   - "https://youtu.be/VIDEO_ID"

                   Local file examples:
                   - "/path/to/recording.mp4"
                   - "./screencast.mov"

        prompt: What you want to know about the video. Be specific for best results:
               General analysis:
               - "Summarize this video in 3-5 key points"
               - "What is this video about?"
               - "List the main topics covered in this video"

               Time-specific analysis:
               - "Summarize from 1:00 to 1:30"
               - "What happens at the 5-minute mark?"
               - "Describe the section between 2:30 and 4:00"

               Specific information extraction:
               - "What code examples are shown in this tutorial?"
               - "List all the commands demonstrated in this video"
               - "What are the speaker's main arguments?"

        model: Gemini model to use (default: gemini-2.0-flash-001). The default model supports
              video analysis. Use this parameter only if you need a different model variant.

    Returns:
        Gemini's detailed analysis of the video content, including summaries, transcriptions,
        observations, and answers to your specific questions about the video.
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"
    
    try:
        # Handle YouTube URLs
        if is_youtube_url(input_path):
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
            
            # For files > 20MB, use the File API
            if file_size_mb > 20:
                # Upload the file first
                with open(file_path, 'rb') as f:
                    uploaded_file = client.files.upload(
                        path=str(file_path),
                        display_name=file_path.name
                    )
                
                # Wait for file to be processed
                file_obj = uploaded_file
                
                # Generate content with the uploaded file
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
                
            else:
                # For smaller files, include inline
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
            
            return f"🤖 GEMINI VIDEO ANALYSIS (Local file: {file_path.name}, {file_size_mb:.1f}MB):\n\n{response.text}"
        
        else:
            return f"🤖 GEMINI RESPONSE:\n\nError: Input '{input_path}' is neither a valid YouTube URL nor an existing file path"
            
    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError analyzing video: {str(e)}"

if __name__ == "__main__":
    mcp.run()