#!/usr/bin/env python3
"""
Gemini MCP Server v3.3.0
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
__version__ = "3.3.0"

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
    """Ask Gemini a question and get the response directly in the assistant's context
    
    Args:
        prompt: The question or prompt for Gemini
        temperature: Temperature for response (0.0-1.0, default: 0.5)
    """
    result = call_gemini(prompt, temperature)
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_code_review(code: str, focus_areas: Optional[List[str]] = None) -> str:
    """Have Gemini review code and return feedback directly to the assistant
    
    Args:
        code: The code to review
        focus_areas: Specific focus areas (e.g., ["security", "performance", "readability", "best practices", "bugs"])
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
    """Brainstorm solutions with Gemini, response visible to the assistant
    
    Args:
        topic: The topic to brainstorm about
        context: Additional context to guide the brainstorming
    """
    prompt = f"Let's brainstorm about: {topic}"
    if context:
        prompt += f"\n\nContext: {context}"
    prompt += "\n\nProvide creative ideas, alternatives, and considerations. Think outside the box and offer innovative solutions."
    
    result = call_gemini(prompt, 0.7)  # Higher temperature for creativity
    return f"🤖 GEMINI RESPONSE:\n\n{result}"

@mcp.tool()
def gemini_debug(error_message: str, code_snippet: str = "", context: str = "") -> str:
    """Analyze an error message and code context to find the root cause and suggest a fix
    
    Args:
        error_message: The full error message, including stack trace
        code_snippet: The relevant code snippet that is causing the error
        context: Additional context about when/how the error occurs
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
    """
    Ask Gemini a question and get a response grounded with Google Search results.
    This tool uses the new unified SDK with proper grounding support.
    
    Args:
        topic: The topic to research using Google Search grounding
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
def interpret_image(image_path: str, prompt: str = "Describe this image in detail", temperature: float = 0.5) -> str:
    """Analyze and interpret an image file using Gemini Vision

    Args:
        image_path: Can be one of:
                   - Local file path (supports jpg, jpeg, png, gif, webp, bmp)
                   - Direct image URL (http/https)
                   - Base64-encoded image string (data:image/jpeg;base64,...)
        prompt: Analysis prompt (default: "Describe this image in detail")
        temperature: Temperature for response (0.0-1.0, default: 0.5)

    Returns:
        Gemini's interpretation of the image
    """
    if not GEMINI_AVAILABLE or not client:
        return f"🤖 GEMINI RESPONSE:\n\nGemini not available: {GEMINI_ERROR}"

    try:
        # Handle base64-encoded images
        if is_base64_image(image_path):
            # Parse data URI: data:image/jpeg;base64,<base64_data>
            header, base64_data = image_path.split(',', 1)
            mime_type = header.split(';')[0].split(':')[1]  # Extract mime type from data:image/jpeg

            # Decode base64 to bytes
            image_data = base64.b64decode(base64_data)
            file_size_mb = len(image_data) / (1024 * 1024)

            # Send to Gemini
            response = client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=[
                    types.Part.from_bytes(
                        data=image_data,
                        mime_type=mime_type
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=8192,
                )
            )

            return f"🤖 GEMINI IMAGE ANALYSIS (Base64, {file_size_mb:.1f}MB):\n\n{response.text}"

        # Handle image URLs (HTTP/HTTPS)
        if is_image_url(image_path):
            # For image URLs, we need to download and process them
            import urllib.request

            # Download the image
            with urllib.request.urlopen(image_path) as url_response:
                image_data = url_response.read()

            # Determine MIME type from URL or content
            mime_type = url_response.headers.get_content_type()
            if not mime_type or not mime_type.startswith('image/'):
                # Try to guess from URL
                mime_type, _ = mimetypes.guess_type(image_path)
                if not mime_type:
                    mime_type = 'image/jpeg'  # Default fallback

            file_size_mb = len(image_data) / (1024 * 1024)

            # For URLs, always use inline data (already downloaded)
            response = client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=[
                    types.Part.from_bytes(
                        data=image_data,
                        mime_type=mime_type
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=8192,
                )
            )

            return f"🤖 GEMINI IMAGE ANALYSIS (URL: {image_path}, {file_size_mb:.1f}MB):\n\n{response.text}"

        # Handle local file paths
        if not os.path.exists(image_path):
            return f"🤖 GEMINI RESPONSE:\n\nError: Image file '{image_path}' not found"

        file_path = Path(image_path)

        # Check if it's an image file
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type or not mime_type.startswith('image/'):
            return f"🤖 GEMINI RESPONSE:\n\nError: File '{image_path}' is not a valid image file (detected type: {mime_type})"

        # Get file size to determine upload method
        file_size = file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # For files > 20MB, use the File API
        if file_size_mb > 20:
            # Upload the file first
            uploaded_file = client.files.upload(
                path=str(file_path),
                display_name=file_path.name
            )

            # Generate content with the uploaded file
            response = client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=[
                    types.Part.from_uri(
                        file_uri=uploaded_file.uri,
                        mime_type=mime_type
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=8192,
                )
            )

            # Clean up the uploaded file
            client.files.delete(name=uploaded_file.name)

        else:
            # For smaller files, include inline
            with open(file_path, 'rb') as f:
                image_data = f.read()

            response = client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=[
                    types.Part.from_bytes(
                        data=image_data,
                        mime_type=mime_type
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=8192,
                )
            )

        return f"🤖 GEMINI IMAGE ANALYSIS ({file_path.name}, {file_size_mb:.1f}MB):\n\n{response.text}"

    except Exception as e:
        return f"🤖 GEMINI RESPONSE:\n\nError analyzing image: {str(e)}"

@mcp.tool()
def server_info() -> str:
    """Get server status and error information"""
    if GEMINI_AVAILABLE:
        return f"🤖 GEMINI RESPONSE:\n\nServer v{__version__} - Gemini connected and ready! Using modern unified Google Gen AI SDK."
    else:
        return f"🤖 GEMINI RESPONSE:\n\nServer v{__version__} - Gemini error: {GEMINI_ERROR}"

def is_youtube_url(url: str) -> bool:
    """Check if a string is a valid YouTube URL"""
    return (url.startswith("http://") or url.startswith("https://")) and ("youtube.com" in url or "youtu.be" in url)

@mcp.tool()
def watch_video(input_path: str, prompt: str, model: str = "gemini-2.0-flash-001") -> str:
    """Analyze a YouTube video or local video file using Gemini
    
    Args:
        input_path: YouTube URL or local video file path
        prompt: Analysis prompt (can include time ranges like "Summarize from 1:00 to 1:30")
        model: Gemini model to use (default: gemini-2.0-flash-001)
    
    Returns:
        Gemini's analysis of the video content
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