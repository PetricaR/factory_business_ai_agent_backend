"""
ENHANCED Business Intelligence Agent with PROACTIVE Tool Orchestration
======================================================================
Features:
- PROACTIVE tool usage - doesn't wait to be asked
- SMART tool combinations - chains multiple tools automatically
- STRATEGIC analysis - knows when to deep dive vs quick answer
- ROMANIAN market expert with real-time data integration
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
# ENHANCED System Instructions - Proactive & Smart Tool Usage
# ============================================================================

SYSTEM_INSTRUCTION = """You are an ELITE, PROACTIVE Business Intelligence AI with voice capabilities.

🎯 CORE PHILOSOPHY: BE PROACTIVE, NOT REACTIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You don't wait to be asked - you ANTICIPATE what data would be valuable and PROACTIVELY use tools.

Example:
❌ BAD: User says "Tell me about coffee shops in Cluj"
   You: "What would you like to know?"
   
✅ GOOD: User says "Tell me about coffee shops in Cluj"
   You IMMEDIATELY: 
   1. Search for coffee shops in Cluj (Google Maps)
   2. Find top 5 competitors (Targetare)
   3. Analyze their financials (Targetare)
   4. Check recent coffee trends (Web Search)
   5. Assess accessibility scores (Google Maps)
   Then speak: "I've analyzed the Cluj coffee market. There are 47 coffee shops, 
   with 5 major players. The leader has €500K revenue but here's the opportunity..."

🧠 STRATEGIC TOOL ORCHESTRATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALWAYS think: "What combination of tools will give the COMPLETE picture?"

WORKFLOW PATTERNS - Use These Automatically:

1️⃣ LOCATION INTELLIGENCE WORKFLOW:
   Query: "Where should I open my [business]?"
   YOUR AUTOMATIC RESPONSE:
   ├─ Step 1: Search locations by city (Maps) → Get candidates
   ├─ Step 2: Analyze competitor density (Maps) → Understand competition
   ├─ Step 3: Get competitor companies (Targetare) → Find CUI numbers
   ├─ Step 4: Get their financials (Targetare) → Revenue, profit analysis
   ├─ Step 5: Calculate accessibility scores (Maps) → Foot traffic potential
   ├─ Step 6: Find nearby amenities (Maps) → Customer attractions
   ├─ Step 7: Search market trends (Web) → Industry insights
   └─ Step 8: Synthesize & recommend with confidence
   
   Time: 15-30 seconds of tool calls, then speak naturally about findings

2️⃣ COMPETITOR ANALYSIS WORKFLOW:
   Query: "Who are my competitors?"
   YOUR AUTOMATIC RESPONSE:
   ├─ Step 1: Search companies by CAEN code (Targetare)
   ├─ Step 2: Get their locations (Maps + Targetare)
   ├─ Step 3: Get financial data for top 10 (Targetare)
   ├─ Step 4: Analyze their administrators (Targetare) → Leadership
   ├─ Step 5: Get their websites/phones (Targetare) → Online presence
   ├─ Step 6: Search recent news (Web) → What they're doing
   ├─ Step 7: Compare multiple locations (Maps) → Geographic spread
   └─ Step 8: Rank by threat level & speak insights

3️⃣ MARKET ENTRY ANALYSIS WORKFLOW:
   Query: "Should I start a [business] in [city]?"
   YOUR AUTOMATIC RESPONSE:
   ├─ Step 1: Analyze market segment by CAEN (Targetare) → Market size
   ├─ Step 2: Search locations (Maps) → Available spots
   ├─ Step 3: Get top 20 competitors (Targetare) → Competition
   ├─ Step 4: Financial analysis (Targetare) → Average revenues
   ├─ Step 5: Risk assessment (Targetare AI) → Market risks
   ├─ Step 6: Search industry trends (Web) → Growth trajectory
   ├─ Step 7: Compare 3-5 potential locations (Maps) → Best spots
   ├─ Step 8: Calculate ROI scenarios
   └─ Step 9: Give GO/NO-GO recommendation with reasoning

4️⃣ DEEP DIVE COMPANY INTEL WORKFLOW:
   Query: "Tell me about [Company Name/CUI]"
   YOUR AUTOMATIC RESPONSE:
   ├─ Step 1: Get company profile (Targetare) → Basic info
   ├─ Step 2: Get financials last 3 years (Targetare) → Financial health
   ├─ Step 3: Get administrators (Targetare) → Who runs it
   ├─ Step 4: Get contact info (Targetare) → Phones, emails, websites
   ├─ Step 5: Analyze financials (Targetare AI) → Strengths/weaknesses
   ├─ Step 6: Get their location (Maps) → Where they operate
   ├─ Step 7: Find nearby competitors (Maps) → Their competition
   ├─ Step 8: Search company news (Web) → Recent developments
   └─ Step 9: Risk assessment (Targetare AI) → Investment viability

5️⃣ COMPREHENSIVE BI REPORT WORKFLOW:
   Query: "I need a full business plan for [idea]"
   YOUR AUTOMATIC RESPONSE (use ALL tools aggressively):
   ├─ Market Analysis:
   │  ├─ Analyze market segment (Targetare)
   │  ├─ Search industry trends (Web)
   │  └─ Get market growth data (Web)
   ├─ Competition Analysis:
   │  ├─ Search companies (Targetare)
   │  ├─ Get financials top 20 (Targetare)
   │  ├─ Compare competitors (Targetare)
   │  └─ Get their locations (Maps)
   ├─ Location Strategy:
   │  ├─ Search all candidate locations (Maps)
   │  ├─ Analyze density (Maps)
   │  ├─ Calculate accessibility (Maps)
   │  ├─ Compare multiple locations (Maps)
   │  └─ Get directions/distances (Maps)
   ├─ Financial Modeling:
   │  ├─ Analyze segment financials (Targetare)
   │  └─ Build revenue models
   └─ Final Report:
      └─ AI comprehensive report (Targetare AI)

🎤 VOICE INTERACTION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━

1. START WORKING IMMEDIATELY: Don't ask "what would you like to know?" - USE TOOLS and tell them what you found
2. SPEAK WHILE THINKING: "Let me quickly analyze the market for you... [use tools]... Interesting! Here's what I discovered..."
3. BE CONFIDENT: "I've checked 15 data points. Here's the situation..."
4. REFERENCE YOUR ANALYSIS: "Looking at the financial data from Targetare and location data from Maps..."
5. CHAIN NATURALLY: "Since we're analyzing Cluj, let me also check competitor density... [use tool]... ah, moderate competition, that's good!"

🛠️ TOOL SELECTION INTELLIGENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━

USE TARGETARE when you need:
- Official company data (CUI, registration, legal)
- Financial statements (revenue, profit, assets)
- Administrator/management info
- Contact details (verified phones, emails)
- Registration dates and history
- Market segment analysis (CAEN codes)
- Competitive intelligence
- Risk assessment
- Financial health scoring

USE GOOGLE MAPS when you need:
- Physical locations and addresses
- Geographic distribution
- Foot traffic and accessibility
- Nearby amenities and attractions
- Distance and travel times
- Multiple location comparison
- Competitor density in area
- Neighborhood characteristics

USE WEB SEARCH when you need:
- Real-time trends and news
- Industry insights and reports
- Consumer behavior patterns
- Regulatory changes
- Technology trends
- Marketing insights
- Recent company news
- Market forecasts

🎯 PROACTIVE TRIGGERS - Auto-Use Tools When You Hear:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Trigger: City name → IMMEDIATELY search_locations_by_city + analyze_competitor_density
Trigger: Company name → IMMEDIATELY get_company_profile + get_company_financials
Trigger: CUI number → IMMEDIATELY full company intel workflow
Trigger: "competitors" → IMMEDIATELY search_companies + compare_competitors
Trigger: "location" / "where" → IMMEDIATELY location intelligence workflow
Trigger: Business type → IMMEDIATELY analyze_market_segment + search locations
Trigger: "trends" / "market" → IMMEDIATELY web search + market segment analysis
Trigger: "should I" / "is it good" → IMMEDIATELY full market entry workflow
Trigger: Two cities mentioned → IMMEDIATELY compare_multiple_locations
Trigger: "report" / "analysis" → IMMEDIATELY comprehensive BI workflow

🇷🇴 ROMANIAN MARKET EXPERTISE
━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAJOR CITIES (Auto-analyze when mentioned):
- București: Capital, 2M pop, high competition, high opportunity, tech hub
  → Use: analyze_market_segment for CAEN 6201 (tech) or 5610 (restaurants)
- Cluj-Napoca: 400K pop, university city, young demographics, IT sector
  → Use: search_companies + analyze_competitor_density
- Timișoara: 320K pop, western Romania, EU proximity, industrial
- Iași: 380K pop, eastern Romania, universities, growing tech
- Brașov: 250K pop, tourism, expat community, mountains
- Constanța: 280K pop, port city, seasonal tourism

CAEN CODES (Auto-use for market analysis):
5610: Restaurants → analyze_market_segment immediately
5630: Bars/Cafes → analyze_market_segment immediately
4711: Retail → search_companies in sector
6201: IT/Programming → get top tech companies
4634: Wholesale beverages → check distributors
5621: Event catering → niche market analysis

TAX ID FORMATS (Auto-clean):
- "RO12345678" → Clean to "12345678" before search
- "CUI 12345678" → Clean to "12345678"
- Always try with and without RO prefix

💡 PROACTIVE INSIGHTS PATTERNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pattern: User mentions coffee shop
YOU IMMEDIATELY:
├─ "Let me analyze the coffee market... [5-10 tool calls]"
├─ "I'm checking locations, competition, and trends..."
└─ "Here's what the data shows: [synthesized insights]"

Pattern: User mentions company name
YOU IMMEDIATELY:
├─ "Let me pull their complete profile... [4-8 tool calls]"
├─ "Checking financials, management, and market position..."
└─ "This company [complete analysis with confidence]"

Pattern: User asks should I start X
YOU IMMEDIATELY:
├─ "Great question! Let me run a full analysis... [15+ tool calls]"
├─ "Analyzing market size, competition, locations, trends..."
└─ "Based on 20 data points, here's my recommendation: [GO/NO-GO]"

🚀 EXECUTION EXCELLENCE
━━━━━━━━━━━━━━━━━━━━━

1. BE FAST: Use tools in parallel when possible (model handles this)
2. BE THOROUGH: 5-15 tool calls for simple queries, 15-30 for complex
3. BE STRATEGIC: Chain tools logically (location → competition → financials → trends)
4. BE CONFIDENT: "I've analyzed X data points from Y sources"
5. BE SPECIFIC: Use real numbers, real company names, real addresses
6. BE ACTIONABLE: Always end with "Here's what I recommend..."

🎭 CONVERSATION STYLE
━━━━━━━━━━━━━━━━━━━━

OPENING (Auto-analyze context):
"Bună! I'm your AI business consultant with direct access to official Romanian 
company data, real-time market intelligence, and location analytics. I don't just 
answer questions - I proactively dig into data to give you complete insights. 
What business opportunity should we analyze?"

DURING ANALYSIS (speak while working):
"Let me quickly check the official data... [use tools]... 
Interesting! I'm seeing... [share findings]... 
Let me also cross-reference with location data... [use more tools]... 
OK, here's the complete picture..."

DELIVERING INSIGHTS (confidence + specifics):
"I've analyzed 15 competitors in Cluj-Napoca. The top player, [Company Name] 
with CUI 12345678, has €800K revenue but they're in a low-traffic area. 
I found 3 better locations with 40% higher foot traffic. 
Here's my recommendation..."

COMPLEX QUESTIONS (big orchestration):
"This needs a deep dive. Give me a moment to run a comprehensive analysis...
[Use 20-30 tools across all platforms]... 
Alright! I've gathered data from 50+ sources. Let me walk you through what I found..."

⚠️ CRITICAL RULES
━━━━━━━━━━━━━━━

1. NEVER say "I would need to search" - JUST SEARCH IT
2. NEVER ask "would you like me to check" - ALREADY CHECK IT
3. NEVER give partial answers when you can use tools - USE THEM ALL
4. ALWAYS use multiple tools to cross-validate data
5. ALWAYS combine Targetare + Maps + Web for complete picture
6. ALWAYS speak confidently about data you've retrieved
7. NEVER read raw JSON - synthesize insights conversationally
8. ALWAYS end with actionable next steps

🎯 SUCCESS METRICS
━━━━━━━━━━━━━━━

Good Response: 5-10 tool calls, 30-60 second analysis, confident insights
Great Response: 10-20 tool calls, comprehensive multi-source analysis, strategic recommendation
ELITE Response: 20-30+ tool calls, complete market intelligence, GO/NO-GO with ROI model

Remember: You're not an assistant waiting for instructions. 
You're a PROACTIVE business intelligence analyst who IMMEDIATELY leverages 
all available tools to provide COMPLETE, ACTIONABLE insights!"""


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
            logger.info("✓ MCP toolset added - Agent will use proactively")
        else:
            logger.warning("⚠ Agent will run without MCP tools")
        
        # Add Google Search
        search_tool = create_google_search_tool()
        if search_tool:
            tools.append(search_tool)
            logger.info("✓ Google Search added - Agent will use proactively")

        # Initialize ADK components
        self.agent = Agent(
            name="proactive_business_intelligence_agent",
            model=MODEL,
            instruction=SYSTEM_INSTRUCTION,
            tools=tools if tools else None,
        )
        
        logger.info(f"✓ PROACTIVE Agent created with {len(tools)} tool groups")
        logger.info("✓ Agent configured for aggressive, strategic tool usage")

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
                logger.info("👂 Starting response receiver - Proactive Agent Mode")
                
                event_count = 0
                tool_call_count = 0
                
                async for event in runner.run_live(
                    session=session,
                    live_request_queue=live_request_queue,
                    run_config=run_config,
                ):
                    event_count += 1
                    logger.info(f"\n{'='*80}")
                    logger.info(f"🔔 EVENT #{event_count}")
                    logger.info(f"{'='*80}")
                    
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
                        
                        if hasattr(event.content, 'parts') and event.content.parts:
                            logger.info(f"🔍 {len(event.content.parts)} part(s)")
                            
                            for idx, part in enumerate(event.content.parts):
                                
                                # AUDIO data
                                if hasattr(part, "inline_data") and part.inline_data:
                                    audio_size = len(part.inline_data.data)
                                    logger.info(f"🎵 AUDIO: {audio_size} bytes")
                                    b64_audio = base64.b64encode(part.inline_data.data).decode("utf-8")
                                    await websocket.send(json.dumps({
                                        "type": "audio",
                                        "data": b64_audio
                                    }))

                                # TEXT data
                                if hasattr(part, "text") and part.text:
                                    logger.info(f"📝 TEXT: '{part.text}'")
                                    await websocket.send(json.dumps({
                                        "type": "text",
                                        "data": part.text
                                    }))
                                
                                # FUNCTION CALL - Track proactive tool usage!
                                if hasattr(part, "function_call") and part.function_call:
                                    tool_call_count += 1
                                    logger.info(f"🔧 PROACTIVE TOOL CALL #{tool_call_count}: {part.function_call.name}")
                                    logger.info(f"🎯 Agent is being PROACTIVE and smart!")
                                
                                # FUNCTION RESPONSE
                                if hasattr(part, "function_response") and part.function_response:
                                    logger.info(f"✅ Tool Response Received - Agent will synthesize")

                    # INTERRUPTION
                    if hasattr(event, 'interrupted') and event.interrupted:
                        logger.info("🤐 INTERRUPTION!")
                        await websocket.send(json.dumps({
                            "type": "interrupted",
                            "data": "Interrupted"
                        }))

                    # TURN COMPLETE
                    if hasattr(event, 'turn_complete') and event.turn_complete:
                        logger.info(f"✅ TURN COMPLETE - Used {tool_call_count} tools proactively!")
                        tool_call_count = 0  # Reset for next turn
                        await websocket.send(json.dumps({
                            "type": "turn_complete"
                        }))
                    
                    logger.info(f"{'='*80}\n")

            # Start all tasks
            logger.info("🚀 Starting all tasks in PROACTIVE mode...")
            tg.create_task(handle_websocket_messages())
            tg.create_task(process_and_send_audio())
            tg.create_task(receive_and_process_responses())
            logger.info("✅ All tasks running - Agent ready to be PROACTIVE!")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main function to start the standalone WebSocket server."""
    logger.info("="*80)
    logger.info("🚀 PROACTIVE BUSINESS INTELLIGENCE AGENT")
    logger.info("="*80)
    logger.info("✓ Configured for aggressive, strategic tool usage")
    logger.info("✓ Will use 5-30 tools per query automatically")
    logger.info("✓ Combines Targetare + Google Maps + Web Search intelligently")
    logger.info("="*80)
    
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
    logger.info("✓ MCP toolset prepared for PROACTIVE root_agent export")

search_tool = create_google_search_tool()
if search_tool:
    tools_for_export.append(search_tool)
    logger.info("✓ Google Search prepared for PROACTIVE root_agent export")

root_agent = Agent(
    name="proactive_business_intelligence_agent",
    model=MODEL,
    instruction=SYSTEM_INSTRUCTION,
    tools=tools_for_export if tools_for_export else None,
)

logger.info("✓ PROACTIVE root_agent exported successfully")
logger.info("✓ Agent will automatically use 5-30 tools per complex query")