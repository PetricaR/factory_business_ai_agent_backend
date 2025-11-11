"""
FastAPI Application with LIVE AUDIO Streaming Support
Updated with latest ADK practices (October 2025)
FIXED: MCP session initialization timeout issues
"""

import os
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk.cli.fast_api import get_fast_api_app
# load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get port from Cloud Run environment
PORT = int(os.getenv("PORT", "8082"))

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure GOOGLE_MAPS_API_KEY is set
if not os.getenv("GOOGLE_MAPS_API_KEY"):
    logger.warning(
        "GOOGLE_MAPS_API_KEY not set. MCP Google Maps integration will fail. "
        "Please set the environment variable: export GOOGLE_MAPS_API_KEY='your-key-here'"
    )

# Session service URI (using SQLite for local development)
# ADK automatically manages sessions with Cloud Storage in production
SESSION_SERVICE_URI = "sqlite:///./sessions.db"

# CORS origins - configure based on your deployment
ALLOWED_ORIGINS = [
    "http://localhost:8081",
    "http://localhost:3000",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:3000",
    "*"  # Remove this in production!
]

# Enable web UI for testing
SERVE_WEB_INTERFACE = True

try:
    # Create FastAPI app with ADK agent
    # ADK automatically configures WebSocket routes for Live API models
    app: FastAPI = get_fast_api_app(
        agents_dir=AGENT_DIR,
        session_service_uri=SESSION_SERVICE_URI,
        allow_origins=ALLOWED_ORIGINS,
        web=SERVE_WEB_INTERFACE,
    )
    
    logger.info(f"Successfully initialized ADK FastAPI app from {AGENT_DIR}")
    
except Exception as e:
    logger.error(f"Failed to initialize ADK FastAPI app: {e}")
    logger.error(
        "Make sure agent.py exists in the same directory as main.py and "
        "GOOGLE_MAPS_API_KEY environment variable is set"
    )
    raise

# Additional CORS configuration for broader compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Factory Finder AI Agent",
        "version": "2.1",
        "status": "running",
        "model": "gemini-2.5-flash-preview",
        "features": [
            "live_audio_streaming",
            "bidirectional_communication",
            "voice_activity_detection",
            "natural_interruptions",
            "mcp_google_maps_integration",
            "location_intelligence",
            "fixed_mcp_timeout_issue"
        ],
        "endpoints": {
            "web_ui": f"http://localhost:{PORT}",
            "api_docs": f"http://localhost:{PORT}/docs",
            "health": f"http://localhost:{PORT}/health"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for Cloud Run and monitoring.
    Returns detailed status about the agent and its capabilities.
    """
    google_maps_configured = bool(os.getenv("GOOGLE_MAPS_API_KEY"))
    
    return {
        "status": "healthy",
        "service": "factory-finder-agent",
        "version": "2.1",
        "google_maps_api_configured": google_maps_configured,
        "model": {
            "name": "gemini-2.5-flash-preview",
            "type": "live_api",
            "generation": "2.5",
            "capabilities": [
                "audio_input",
                "audio_output",
                "video_input",
                "text_input",
                "text_output",
                "function_calling",
                "code_execution",
                "search_grounding"
            ]
        },
        "streaming": {
            "enabled": True,
            "protocol": "websocket",
            "bidirectional": True,
            "vad_enabled": True,
            "interruption_support": True
        },
        "tools": {
            "mcp_integration": True,
            "google_maps_api": google_maps_configured,
            "mcp_timeout": "60s"
        }
    }


@app.get("/info")
async def agent_info():
    """
    Information about the agent and its capabilities.
    Useful for debugging and understanding what the agent can do.
    """
    return {
        "agent": {
            "name": "Factory Finder AI",
            "purpose": "Location intelligence for Romanian entrepreneurs",
            "target_users": "Factory by Raiffeisen Bank applicants"
        },
        "supported_cities": [
            "București",
            "Cluj-Napoca",
            "Timișoara",
            "Iași",
            "Constanța",
            "Brașov"
        ],
        "capabilities": [
            "Competitor density analysis",
            "Accessibility scoring",
            "Location comparison",
            "Demographic insights",
            "Cost estimation",
            "Real-time voice interaction"
        ],
        "usage": {
            "voice": "Click microphone in Web UI and speak naturally",
            "text": "Type your query in the chat interface",
            "api": "Use /docs for API documentation"
        },
        "fixes": [
            "MCP session timeout increased to 60 seconds",
            "Better error handling for MCP initialization",
            "Improved WebSocket stability"
        ]
    }


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🎤 Factory Finder Agent - LIVE AUDIO STREAMING")
    print("   Fixed MCP Timeout Issues (October 2025)")
    print("=" * 70)
    print(f"\n📍 Endpoints:")
    print(f"   🌐 Web UI:      http://localhost:{PORT}")
    print(f"   📚 API Docs:    http://localhost:{PORT}/docs")
    print(f"   ❤️  Health:      http://localhost:{PORT}/health")
    print(f"   ℹ️  Info:        http://localhost:{PORT}/info")
    print(f"\n🎙️  Audio Features:")
    print(f"   ✓ Bidirectional streaming (WebSocket)")
    print(f"   ✓ Voice Activity Detection (VAD)")
    print(f"   ✓ Natural interruptions")
    print(f"   ✓ Low-latency responses")
    print(f"\n🗺️  Location Intelligence:")
    print(f"   ✓ Google Maps via MCP")
    print(f"   ✓ Competitor analysis")
    print(f"   ✓ Accessibility scoring")
    print(f"   ✓ Multi-location comparison")
    print(f"\n🔧 Fixes Applied:")
    print(f"   ✓ MCP timeout increased to 60s (was 5s)")
    print(f"   ✓ Better error handling")
    print(f"   ✓ Improved session management")
    print("=" * 70)
    print("\n💡 Quick Start:")
    print("   1. Set GOOGLE_MAPS_API_KEY environment variable:")
    print("      export GOOGLE_MAPS_API_KEY='your-api-key-here'")
    print("   2. Open http://localhost:8081 in your browser")
    print("   3. Click the microphone icon 🎤")
    print("   4. Grant microphone permissions")
    print("   5. Start speaking about your business idea!")
    print("\n💬 Example queries:")
    print("   • 'I want to open a coffee shop in Cluj-Napoca'")
    print("   • 'What's the competition like in București?'")
    print("   • 'Compare locations in Timișoara'")
    print("   • 'Find accessible areas in Iași'")
    
    if not os.getenv("GOOGLE_MAPS_API_KEY"):
        print("\n⚠️  WARNING: GOOGLE_MAPS_API_KEY not set!")
        print("   Google Maps features will not work.")
        print("   Set it with: export GOOGLE_MAPS_API_KEY='your-key'")
    
    print("=" * 70 + "\n")
    
    # Start server with optimized settings for Live API
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        # WebSocket configuration for stable connections
        ws_ping_interval=20,  # Keep connections alive
        ws_ping_timeout=20,
        # Performance optimization
        timeout_keep_alive=75,
    )