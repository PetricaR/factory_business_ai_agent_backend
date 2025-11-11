"""
FastAPI Application with Gemini 2.5 Flash LIVE AUDIO (Native Audio) Support
Enhanced with cutting-edge native audio functionality
Updated November 2025
"""

import os
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.adk.cli.fast_api import get_fast_api_app
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get port from Cloud Run environment
PORT = int(os.getenv("PORT", "8000"))

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure GOOGLE_MAPS_API_KEY is set
if not os.getenv("GOOGLE_MAPS_API_KEY"):
    logger.warning(
        "⚠️ GOOGLE_MAPS_API_KEY not set. MCP Google Maps integration will use mock data. "
        "Set it with: export GOOGLE_MAPS_API_KEY='your-key-here'"
    )

# Session service URI (using SQLite for local development)
SESSION_SERVICE_URI = "sqlite:///./sessions.db"

# CORS origins - configure based on your deployment
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:8081",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:3000",
    "*"  # Remove this in production!
]

# Enable web UI for testing
SERVE_WEB_INTERFACE = True

try:
    # Create FastAPI app with ADK agent
    app: FastAPI = get_fast_api_app(
        agents_dir=AGENT_DIR,
        session_service_uri=SESSION_SERVICE_URI,
        allow_origins=ALLOWED_ORIGINS,
        web=SERVE_WEB_INTERFACE,
    )
    
    logger.info(f"✅ Successfully initialized ADK FastAPI app from {AGENT_DIR}")
    
except Exception as e:
    logger.error(f"❌ Failed to initialize ADK FastAPI app: {e}")
    logger.error(
        "Make sure agent.py exists in the agent/ directory and "
        "all dependencies are properly installed"
    )
    raise

# Additional CORS configuration
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
        "version": "2.2",
        "status": "running",
        "model": "gemini-live-2.5-flash-preview-native-audio",
        "native_audio_features": {
            "enhanced_audio_quality": "Dramatically improved - feels like speaking with a person",
            "voice_quality": "30 HD voices in 24 languages",
            "proactive_audio": "Model responds only when relevant",
            "affective_dialog": "Understands and responds to emotional expressions",
            "improved_barge_in": "Natural interruptions even in noisy environments",
            "robust_function_calling": "Improved triggering rate for tool use",
            "accurate_transcription": "Significantly enhanced audio-to-text",
            "seamless_multilingual": "Effortless language switching without pre-configuration"
        },
        "features": [
            "live_audio_streaming_native",
            "bidirectional_communication",
            "voice_activity_detection",
            "natural_interruptions",
            "mcp_google_maps_integration",
            "location_intelligence",
            "romanian_business_insights"
        ],
        "endpoints": {
            "web_ui": f"http://localhost:{PORT}",
            "api_docs": f"http://localhost:{PORT}/docs",
            "health": f"http://localhost:{PORT}/health",
            "info": f"http://localhost:{PORT}/info"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run and monitoring"""
    google_maps_configured = bool(os.getenv("GOOGLE_MAPS_API_KEY"))
    
    return {
        "status": "healthy",
        "service": "factory-finder-agent",
        "version": "2.2",
        "google_maps_api_configured": google_maps_configured,
        "model": {
            "name": "gemini-live-2.5-flash-preview-native-audio",
            "type": "live_api_native_audio",
            "generation": "2.5",
            "capabilities": [
                "audio_input",
                "audio_output_hd",
                "video_input",
                "text_input",
                "text_output",
                "function_calling",
                "proactive_audio",
                "affective_dialog",
                "multilingual_seamless"
            ]
        },
        "streaming": {
            "enabled": True,
            "protocol": "websocket",
            "bidirectional": True,
            "vad_enabled": True,
            "interruption_support": True,
            "audio_format": {
                "input": "Raw 16-bit PCM at 16kHz",
                "output": "Raw 16-bit PCM at 24kHz"
            }
        },
        "tools": {
            "mcp_integration": True,
            "google_maps_api": google_maps_configured,
            "mcp_timeout": "60s",
            "location_analysis": True,
            "cost_estimation": True,
            "competitor_analysis": True
        }
    }


@app.get("/info")
async def agent_info():
    """Information about the agent and its capabilities"""
    return {
        "agent": {
            "name": "Factory Finder AI",
            "purpose": "Location intelligence for Romanian entrepreneurs",
            "target_users": "Factory by Raiffeisen Bank applicants",
            "language_support": ["Romanian", "English", "Multilingual (24 languages)"]
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
            "Real-time voice interaction (Native Audio)",
            "Emotional understanding (Affective Dialog)",
            "Natural multilingual conversations"
        ],
        "usage": {
            "voice": "Click microphone in Web UI and speak naturally in any supported language",
            "text": "Type your query in the chat interface",
            "api": "Use /docs for API documentation",
            "interruption": "You can interrupt the agent naturally at any time"
        },
        "native_audio_enhancements": [
            "Enhanced audio quality - sounds like a real person",
            "30 HD voices to choose from",
            "Understands emotional context in your voice",
            "More reliable interruptions",
            "Better function calling",
            "More accurate transcriptions",
            "Seamless language switching"
        ]
    }


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🎤 Factory Finder Agent - GEMINI 2.5 FLASH NATIVE AUDIO")
    print("   Enhanced with Cutting-Edge Native Audio Features")
    print("=" * 70)
    print(f"\n📍 Endpoints:")
    print(f"   🌐 Web UI:      http://localhost:{PORT}")
    print(f"   📚 API Docs:    http://localhost:{PORT}/docs")
    print(f"   ❤️  Health:      http://localhost:{PORT}/health")
    print(f"   ℹ️  Info:        http://localhost:{PORT}/info")
    print(f"\n🎙️  Native Audio Features:")
    print(f"   ✨ Enhanced audio quality - dramatically improved")
    print(f"   🗣️  30 HD voices in 24 languages")
    print(f"   🎯 Proactive Audio - responds only when relevant")
    print(f"   😊 Affective Dialog - understands emotions")
    print(f"   🔊 Improved barge-in - interrupt naturally")
    print(f"   🔧 Robust function calling")
    print(f"   📝 Accurate transcription")
    print(f"   🌍 Seamless multilingual support")
    print(f"\n🗺️  Location Intelligence:")
    print(f"   ✓ Google Maps via MCP")
    print(f"   ✓ Competitor analysis")
    print(f"   ✓ Accessibility scoring")
    print(f"   ✓ Multi-location comparison")
    print(f"   ✓ Romanian market insights")
    print("=" * 70)
    print("\n💡 Quick Start:")
    print("   1. Set GOOGLE_MAPS_API_KEY environment variable:")
    print("      export GOOGLE_MAPS_API_KEY='your-api-key-here'")
    print(f"   2. Open http://localhost:{PORT} in your browser")
    print("   3. Click the microphone icon 🎤")
    print("   4. Grant microphone permissions")
    print("   5. Start speaking naturally in Romanian, English, or any language!")
    print("\n💬 Example queries:")
    print("   • 'Vreau să deschid o cafenea în Cluj-Napoca'")
    print("   • 'I want to open a coffee shop in Cluj-Napoca'")
    print("   • 'Cum e competiția în București?'")
    print("   • 'Compare locations in Timișoara'")
    print("   • 'Cât costă să deschid un restaurant în Iași?'")
    
    if not os.getenv("GOOGLE_MAPS_API_KEY"):
        print("\n⚠️  WARNING: GOOGLE_MAPS_API_KEY not set!")
        print("   Google Maps features will use mock data.")
        print("   Set it with: export GOOGLE_MAPS_API_KEY='your-key'")
    
    print("=" * 70 + "\n")
    
    # Start server with optimized settings for Live API
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        # WebSocket configuration for stable connections
        ws_ping_interval=20,
        ws_ping_timeout=20,
        # Performance optimization
        timeout_keep_alive=75,
    )