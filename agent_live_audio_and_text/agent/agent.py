"""
Google ADK Agent with Live Audio Support + Business Intelligence
UPDATED: Based on official Gemini Live API transcription example
Correctly accesses server_content.input_transcription and output_transcription
ADDED: MCP Tools (Targetare + Google Maps) + Google Custom Search
"""

import asyncio
import json
import base64
import os
from typing import Optional

# Import Google ADK components
from google.adk.agents import Agent, LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv

# MCP and Search imports
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseConnectionParams
from google.adk.tools import google_search
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import id_token

load_dotenv()

# Import common components using relative import
from .common import (
    BaseWebSocketServer,
    logger,
    MODEL,
    VOICE_NAME,
    SEND_SAMPLE_RATE,
)


# ============================================================================
# Configuration for MCP and Web Search
# ============================================================================

def get_mcp_server_url() -> str:
    """Get MCP server URL from environment."""
    return os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")


def get_project_id() -> Optional[str]:
    """Get Google Cloud project ID."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        try:
            _, project_id = google.auth.default()
        except Exception:
            pass
    return project_id


def setup_vertex_ai() -> bool:
    """Setup Vertex AI environment."""
    try:
        if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI"):
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
        
        project_id = get_project_id()
        if project_id:
            os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
            
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        os.environ["GOOGLE_CLOUD_LOCATION"] = location
        
        logger.info(f"✓ Vertex AI configured: {MODEL}")
        logger.info(f"  Project: {project_id}")
        logger.info(f"  Location: {location}")
        return True
    except Exception as e:
        logger.error(f"✗ Vertex AI setup failed: {e}")
        return False


def is_cloud_run() -> bool:
    """Check if running in Cloud Run environment."""
    return os.getenv("K_SERVICE") is not None


def get_mcp_connection_params(server_url: str, timeout: int = 60):
    """Get MCP connection parameters with authentication if needed."""
    headers = {}
    
    if is_cloud_run():
        logger.info("Cloud Run detected - using authenticated connection")
        try:
            auth_req = Request()
            target_audience = server_url.rsplit("/", 1)[0]
            token = id_token.fetch_id_token(auth_req, target_audience)
            headers = {"Authorization": f"Bearer {token}"}
            logger.info("✓ Generated ID token")
        except Exception as e:
            logger.warning(f"Could not generate ID token: {e}")
    
    return SseConnectionParams(
        url=server_url,
        headers=headers,
        timeout=timeout,
    )


def create_mcp_toolset() -> Optional[MCPToolset]:
    """Create MCP toolset with all tools."""
    try:
        server_url = get_mcp_server_url()
        connection_params = get_mcp_connection_params(server_url)
        toolset = MCPToolset(connection_params=connection_params)
        logger.info("✓ MCP toolset created")
        logger.info(f"  Server: {server_url}")
        logger.info(f"  Tools: 25 total (12 Targetare + 13 Google Maps)")
        return toolset
    except Exception as e:
        logger.error(f"✗ Failed to create MCP toolset: {e}")
        return None


def create_google_search_tool():
    """Create Google Custom Search tool if configured."""
    api_key = os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_CUSTOM_SEARCH_CX")
    
    if api_key and cx:
        try:
            search_tool = google_search(
                google_search_api_key=api_key,
                google_search_cx=cx
            )
            logger.info("✓ Google Custom Search enabled")
            return search_tool
        except Exception as e:
            logger.warning(f"⚠ Could not enable Google Search: {e}")
    else:
        logger.warning("⚠ Google Custom Search not configured")
    
    return None


# ============================================================================
# System Instructions
# ============================================================================

SYSTEM_INSTRUCTION = """You are an elite business intelligence AI assistant with VOICE capabilities, specializing in the Romanian market.

🎤 VOICE INTERACTION GUIDELINES:
- You can HEAR the user speaking and respond with AUDIO
- Be conversational, warm, and professional in your voice responses
- Keep voice responses concise but informative (30-60 seconds ideal)
- Use natural language, not bullet points when speaking
- Ask clarifying questions if needed
- Express enthusiasm about helping entrepreneurs

INTRODUCTION (First interaction):
"Bună! I'm your AI business consultant, here to help you analyze the Romanian market. 
I can help you find optimal locations, analyze competitors, research market trends, 
and provide comprehensive business intelligence. What business idea would you like to explore?"

YOUR COMPLETE TOOLKIT:

🏢 TARGETARE OFFICIAL API TOOLS (12 tools):
1. get_company_profile - Company intelligence from official API
2. get_company_financials - Financial statements and metrics
3. get_company_phones - Official phone numbers
4. get_company_emails - Official email addresses
5. get_company_administrators - Management information
6. get_company_websites - Online presence
7. search_companies_by_registration_date - Find companies by date
8. analyze_company_financials - Advanced financial analysis
9. compare_competitors - Multi-company comparison
10. analyze_market_segment - Market analysis by CAEN code
11. ai_generate_comprehensive_report - Complete BI reports
12. ai_risk_assessment - Risk factor analysis

🗺️ GOOGLE MAPS TOOLS (13 tools):
13. search_locations_by_city - Find business locations
14. analyze_competitor_density - Competition analysis
15. calculate_accessibility_score - Accessibility scoring
16. geocode_address - Address to coordinates
17. reverse_geocode_coordinates - Coordinates to address
18. find_nearby_amenities - Nearby amenities search
19. get_distance_matrix - Distance calculations
20. get_directions - Turn-by-turn directions
21. get_elevation - Elevation data
22. get_timezone - Timezone information
23. find_place_from_text - Text-based search
24. compare_multiple_locations - Location comparison
25. get_location_details - Detailed place information

🔍 WEB SEARCH (Google Custom Search):
- Real-time market trends and industry insights
- Competitor news and developments
- Industry reports and analysis
- Consumer trends and preferences
- Regulatory changes and updates

VOICE CONVERSATION STRATEGIES:

For LOCATION QUERIES ("Where should I open my cafe?"):
1. Acknowledge enthusiastically: "Great question! Let me analyze the best locations for you."
2. Use tools to gather data (Maps + Web Search for trends)
3. Speak naturally: "I found three promising areas. Centrul Vechi has high foot traffic but also high rent..."
4. Offer to dive deeper: "Would you like me to analyze competitor density in any of these areas?"

For COMPETITOR ANALYSIS ("Who are my competitors?"):
1. Use Targetare tools to get official company data
2. Use Maps to find their locations
3. Use Web Search for recent news
4. Summarize verbally in conversational tone
5. Highlight key insights: "Your main competitor has strong financials BUT they're not in the city center..."

For MARKET RESEARCH ("What are the trends?"):
1. Use Web Search extensively for current trends
2. Cross-reference with Targetare market segment data
3. Speak about findings naturally
4. Connect trends to user's business idea

For COMPREHENSIVE ANALYSIS ("Should I start this business?"):
1. Gather data from all sources (Targetare, Maps, Web)
2. Analyze location, competition, trends, financials
3. Provide balanced verbal summary
4. Give clear recommendation with reasoning

ROMANIAN MARKET SPECIFICS:

Major Cities:
- București: Capital, largest market, high competition
- Cluj-Napoca: Tech hub, young demographics, university city
- Timișoara: Western Romania, EU proximity, growing market
- Iași: Eastern Romania, education center, tech scene
- Brașov: Tourism, mountains, expat community
- Constanța: Port city, tourism, summer season

Tax ID Formats:
- Clean: 12345678 (2-10 digits)
- With prefix: RO12345678 or CUI 12345678

Popular Industries (CAEN codes):
- 5610: Restaurants and mobile food service
- 5630: Beverage serving activities
- 4711: Retail sale in non-specialized stores
- 6201: Computer programming activities
- 4634: Wholesale of beverages

VOICE RESPONSE STRUCTURE:

SHORT QUERIES → Short answers (20-40 seconds):
"Where's my order?" → Quick, direct response with key info

MEDIUM QUERIES → Medium answers (40-90 seconds):
"Where should I open my cafe?" → Location analysis with 2-3 key points

COMPLEX QUERIES → Detailed answers (90-120 seconds):
"Complete business analysis" → Comprehensive review, then offer written report

ALWAYS:
✓ Speak naturally and conversationally
✓ Use first name if user provides it
✓ Express genuine interest in helping
✓ Confirm understanding: "Just to make sure I understand correctly..."
✓ Offer next steps: "Would you like me to..."
✓ Be enthusiastic about opportunities
✓ Be honest about challenges

NEVER:
✗ Read out long lists or data tables verbally
✗ Use technical jargon without explaining
✗ Give one-word answers to complex questions
✗ Interrupt user's thought process
✗ Make guarantees about business success

For COMPLEX DATA (financial tables, long lists):
Say: "I've analyzed the data. Let me give you the key insights verbally, 
and I can create a detailed written report if you'd like."

HANDLING AMBIGUITY:
User: "Where should I open my business?"
You: "I'd love to help! What type of business are you planning? 
And which city are you considering, or should I suggest some options?"

Remember: You're a knowledgeable business consultant having a natural 
conversation, not a robot reading data. Be helpful, warm, and strategic!"""


# ============================================================================
# WebSocket Server Implementation
# ============================================================================

class ADKWebSocketServer(BaseWebSocketServer):
    """WebSocket server with correct transcription handling based on official API."""

    def __init__(self, host="0.0.0.0", port=8765):
        super().__init__(host, port)

        # Setup Vertex AI
        setup_vertex_ai()

        # Prepare tools list
        tools = []
        
        # Add MCP toolset
        mcp_toolset = create_mcp_toolset()
        if mcp_toolset:
            tools.append(mcp_toolset)
            logger.info("✓ MCP toolset added")
        else:
            logger.warning("⚠ Agent will run without MCP tools")
        
        # Add Google Search
        search_tool = create_google_search_tool()
        if search_tool:
            tools.append(search_tool)
            logger.info("✓ Google Search added")

        # Initialize ADK components
        self.agent = Agent(
            name="business_intelligence_voice_agent",
            model=MODEL,
            instruction=SYSTEM_INSTRUCTION,
            tools=tools if tools else None,
        )
        
        logger.info(f"✓ Agent created with {len(tools)} tool groups")

        # Create session service
        self.session_service = InMemorySessionService()

    async def process_audio(self, websocket, client_id):
        """Process audio streaming for a connected client."""
        logger.info(f"🚀 Starting audio processing for client {client_id}")
        
        # Store reference to client
        self.active_clients[client_id] = websocket

        # Create session for this client
        session = self.session_service.create_session(
            app_name="audio_assistant",
            user_id=f"user_{client_id}",
            session_id=f"session_{client_id}",
        )
        logger.info(f"✅ Session created: {session.session_id}")

        # Create runner
        runner = Runner(
            app_name="audio_assistant",
            agent=self.agent,
            session_service=self.session_service,
        )

        # Create live request queue
        live_request_queue = LiveRequestQueue()

        # Configuration with audio + transcription (based on official example)
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=VOICE_NAME
                    )
                )
            ),
            response_modalities=["AUDIO"],
            # Enable both input and output transcription
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )
        logger.info(f"✅ RunConfig with transcription enabled")

        # Queue for audio data from the client
        audio_queue = asyncio.Queue()

        async with asyncio.TaskGroup() as tg:
            # Task 1: Process incoming WebSocket messages
            async def handle_websocket_messages():
                """Receive and queue audio from the client."""
                logger.info("📥 Starting WebSocket message handler")
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type")
                        
                        if msg_type == "audio":
                            audio_bytes = base64.b64decode(data.get("data", ""))
                            logger.info(f"🎤 Received {len(audio_bytes)} bytes from client")
                            await audio_queue.put(audio_bytes)
                            
                        elif msg_type == "end":
                            logger.info("🛑 END signal from client")
                            
                        elif msg_type == "text":
                            logger.info(f"💬 TEXT from client: {data.get('data')}")
                            
                    except json.JSONDecodeError:
                        logger.error("❌ Invalid JSON")
                    except Exception as e:
                        logger.error(f"❌ Error: {e}")

            # Task 2: Send audio to Gemini
            async def process_and_send_audio():
                """Send queued audio data to Gemini."""
                logger.info("📤 Starting audio sender")
                while True:
                    data = await audio_queue.get()
                    logger.info(f"📡 Sending {len(data)} bytes to Gemini")
                    
                    live_request_queue.send_realtime(
                        types.Blob(
                            data=data,
                            mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                        )
                    )
                    audio_queue.task_done()

            # Task 3: Receive responses from Gemini
            async def receive_and_process_responses():
                """Process responses with correct transcription access."""
                logger.info("👂 Starting response receiver")
                
                event_count = 0
                async for event in runner.run_live(
                    session=session,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                ):
                    event_count += 1
                    logger.info(f"\n{'='*80}")
                    logger.info(f"🔔 EVENT #{event_count}")
                    logger.info(f"{'='*80}")
                    
                    # Log event structure
                    logger.info(f"🔍 Event type: {type(event).__name__}")
                    event_attrs = [attr for attr in dir(event) if not attr.startswith('_')]
                    logger.info(f"🔍 Event attributes: {event_attrs}")
                    
                    # Check for server_content (CRITICAL for transcriptions!)
                    if hasattr(event, 'server_content') and event.server_content:
                        logger.info(f"🎯 Found server_content!")
                        
                        # INPUT TRANSCRIPTION (user's speech transcribed)
                        if hasattr(event.server_content, 'input_transcription') and event.server_content.input_transcription:
                            transcription_text = event.server_content.input_transcription.text
                            logger.info(f"🎤📝 INPUT TRANSCRIPT: '{transcription_text}'")
                            await websocket.send(json.dumps({
                                "type": "user_transcript",
                                "data": transcription_text
                            }))
                        
                        # OUTPUT TRANSCRIPTION (model's speech transcribed)
                        if hasattr(event.server_content, 'output_transcription') and event.server_content.output_transcription:
                            transcription_text = event.server_content.output_transcription.text
                            logger.info(f"🤖📝 OUTPUT TRANSCRIPT: '{transcription_text}'")
                            await websocket.send(json.dumps({
                                "type": "text",
                                "data": transcription_text
                            }))
                    
                    # Check regular content for audio/text
                    if hasattr(event, 'content') and event.content:
                        logger.info(f"📦 Event has content")
                        
                        if hasattr(event.content, 'role'):
                            logger.info(f"👤 Role: {event.content.role}")
                        
                        if hasattr(event.content, 'parts') and event.content.parts:
                            logger.info(f"🔍 {len(event.content.parts)} part(s)")
                            
                            for idx, part in enumerate(event.content.parts):
                                logger.info(f"\n--- PART #{idx} ---")
                                
                                # AUDIO data
                                if hasattr(part, "inline_data") and part.inline_data:
                                    audio_size = len(part.inline_data.data)
                                    logger.info(f"🎵 AUDIO: {audio_size} bytes")
                                    b64_audio = base64.b64encode(part.inline_data.data).decode("utf-8")
                                    await websocket.send(json.dumps({
                                        "type": "audio",
                                        "data": b64_audio
                                    }))
                                    logger.info(f"✅ Sent audio to client")

                                # TEXT data
                                if hasattr(part, "text") and part.text:
                                    logger.info(f"📝 TEXT: '{part.text}'")
                                    await websocket.send(json.dumps({
                                        "type": "text",
                                        "data": part.text
                                    }))
                                    logger.info(f"✅ Sent text to client")
                                
                                # FUNCTION CALL
                                if hasattr(part, "function_call") and part.function_call:
                                    logger.info(f"🔧 FUNCTION CALL: {part.function_call.name}")
                                
                                # FUNCTION RESPONSE
                                if hasattr(part, "function_response") and part.function_response:
                                    logger.info(f"🔧 FUNCTION RESPONSE")

                    # INTERRUPTION
                    if hasattr(event, 'interrupted') and event.interrupted:
                        logger.info("🤐 INTERRUPTION!")
                        await websocket.send(json.dumps({
                            "type": "interrupted",
                            "data": "Interrupted"
                        }))

                    # TURN COMPLETE
                    if hasattr(event, 'turn_complete') and event.turn_complete:
                        logger.info("✅ TURN COMPLETE")
                        await websocket.send(json.dumps({
                            "type": "turn_complete"
                        }))
                    
                    logger.info(f"{'='*80}\n")

            # Start all tasks
            logger.info("🚀 Starting all tasks...")
            tg.create_task(handle_websocket_messages())
            tg.create_task(process_and_send_audio())
            tg.create_task(receive_and_process_responses())
            logger.info("✅ All tasks running")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main function to start the standalone WebSocket server."""
    server = ADKWebSocketServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting...")
    except Exception as e:
        logger.error(f"Exception: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# Root Agent Export for ADK
# ============================================================================

# Setup for root_agent export
setup_vertex_ai()

# Prepare tools
tools_for_export = []

mcp_toolset = create_mcp_toolset()
if mcp_toolset:
    tools_for_export.append(mcp_toolset)
    logger.info("✓ MCP toolset prepared for root_agent export")

search_tool = create_google_search_tool()
if search_tool:
    tools_for_export.append(search_tool)
    logger.info("✓ Google Search prepared for root_agent export")

root_agent = Agent(
    name="business_intelligence_voice_agent",
    model=MODEL,
    instruction=SYSTEM_INSTRUCTION,
    tools=tools_for_export if tools_for_export else None,
)

logger.info("✓ root_agent exported successfully")