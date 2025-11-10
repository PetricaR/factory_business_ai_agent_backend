"""
Business Intelligence AI Agent - OFFICIAL API VERSION + WEB SEARCH
===================================================================

Uses the Ultimate Business Intelligence MCP Server with official APIs PLUS Google Custom Search:
- 25 total tools in unified MCP server
- 12 Targetare tools (Official API v1 - api.targetare.ro)
- 13 Google Maps tools (Location intelligence)
- Google Search via ADK (Web research & market intelligence)

Perfect for Romanian entrepreneurs, investors, and business consultants.

Key Capabilities:
- Find optimal business locations using Google Maps data
- Analyze competitor financial health using official Targetare API
- Research market trends and industry insights via Google Search
- Cross-reference geographic, financial, and web intelligence
- Identify acquisition targets and market opportunities
- Provide data-driven strategic recommendations
- Secure API key management with GCP Secret Manager
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from dotenv import load_dotenv
from google.adk.tools import google_search, agent_tool

# ADK imports
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StreamableHTTPConnectionParams,
    SseConnectionParams
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

class AnalysisType(Enum):
    """Types of business analysis supported."""
    LOCATION_ONLY = "location"  # Just geographic analysis
    FINANCIAL_ONLY = "financial"  # Just competitive/financial analysis
    COMPREHENSIVE = "comprehensive"  # Full analysis with both sources
    MARKET_ENTRY = "market_entry"  # Market entry strategy
    COMPETITOR_INTEL = "competitor_intel"  # Deep competitor analysis
    ACQUISITION_TARGET = "acquisition"  # Find acquisition opportunities
    DUE_DILIGENCE = "due_diligence"  # Complete due diligence
    WEB_RESEARCH = "web_research"  # Web-based market research
    TREND_ANALYSIS = "trend_analysis"  # Industry trends and news


@dataclass
class UltimateAgentConfig:
    """Configuration for Ultimate Business Intelligence Agent."""
    # Model configuration
    model: str = "gemini-2.5-flash"
    
    # Unified MCP Server URL (ALL 25 tools with official APIs)
    mcp_server_url: str = "http://localhost:8000/mcp"
    
    # Google Cloud configuration
    project_id: Optional[str] = None
    location: str = "europe-west1"
    
    # Connection settings
    timeout: int = 60
    sse_read_timeout: int = 120
    max_retries: int = 3
    
    # Feature flags
    enable_targetare_tools: bool = True
    enable_maps_tools: bool = True
    enable_web_search: bool = True
    
    # Google Custom Search configuration
    custom_search_api_key: Optional[str] = None
    custom_search_cx: Optional[str] = None
    
    @classmethod
    def from_environment(cls) -> 'UltimateAgentConfig':
        """Create configuration from environment variables."""
        return cls(
            model=os.getenv("MODEL", "gemini-2.5-flash"),
            mcp_server_url=os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp"),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            enable_targetare_tools=os.getenv("ENABLE_TARGETARE", "true").lower() == "true",
            enable_maps_tools=os.getenv("ENABLE_MAPS", "true").lower() == "true",
            enable_web_search=os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true",
            custom_search_api_key=os.getenv("GOOGLE_CUSTOM_SEARCH_API_KEY"),
            custom_search_cx=os.getenv("GOOGLE_CUSTOM_SEARCH_CX"),
        )


# ============================================================================
# AUTHENTICATION & SETUP
# ============================================================================

class VertexAIAuthenticator:
    """Handles Vertex AI authentication and configuration."""
    
    @staticmethod
    def setup(config: UltimateAgentConfig) -> bool:
        """Set up Vertex AI authentication and environment variables."""
        try:
            # Enable Vertex AI
            if not os.getenv("GOOGLE_GENAI_USE_VERTEXAI"):
                os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
            
            # Set project ID
            if not config.project_id:
                try:
                    _, project_id = google.auth.default()
                    if project_id:
                        config.project_id = project_id
                        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
                except Exception as e:
                    logger.warning(f"Could not determine project ID: {e}")
                    return False
            else:
                os.environ["GOOGLE_CLOUD_PROJECT"] = config.project_id
            
            # Set location
            os.environ["GOOGLE_CLOUD_LOCATION"] = config.location
            
            logger.info(f"✓ Vertex AI configured: {config.model}")
            logger.info(f"  Project: {config.project_id}")
            logger.info(f"  Location: {config.location}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Vertex AI setup failed: {e}")
            return False


class MCPConnectionManager:
    """Manages unified MCP server connection."""
    
    @staticmethod
    def is_cloud_run() -> bool:
        """Check if running in Cloud Run environment."""
        return os.getenv("K_SERVICE") is not None
    
    @staticmethod
    def get_connection_params(server_url: str, timeout: int = 60):
        """Get MCP connection parameters with authentication if needed."""
        headers = {}
        
        # Add authentication for Cloud Run
        if MCPConnectionManager.is_cloud_run():
            logger.info(f"Cloud Run detected - using authenticated connection for {server_url}")
            try:
                auth_req = Request()
                target_audience = server_url.rsplit("/", 1)[0]
                token = id_token.fetch_id_token(auth_req, target_audience)
                headers = {"Authorization": f"Bearer {token}"}
                logger.info(f"✓ Generated ID token for: {target_audience}")
            except Exception as e:
                logger.warning(f"Could not generate ID token: {e}")
        
        # Use SSE connection (FastMCP uses SSE transport)
        return SseConnectionParams(
            url=server_url,
            headers=headers,
            timeout=timeout,
        )
    
    @staticmethod
    def create_toolset(config: UltimateAgentConfig) -> MCPToolset:
        """Create single toolset for unified MCP server with all 25 tools."""
        try:
            connection_params = MCPConnectionManager.get_connection_params(
                config.mcp_server_url, 
                config.timeout
            )
            toolset = MCPToolset(connection_params=connection_params)
            logger.info("✓ Ultimate Unified MCP toolset created")
            logger.info(f"  Server: {config.mcp_server_url}")
            logger.info(f"  Tools: 25 total (12 Targetare + 13 Google Maps)")
            logger.info(f"  APIs: Official Targetare API v1 + Google Maps Platform")
            return toolset
        except Exception as e:
            logger.error(f"✗ Failed to create MCP toolset: {e}")
            raise RuntimeError(f"Toolset creation failed: {e}")


# ============================================================================
# ENHANCED AGENT INSTRUCTIONS WITH WEB SEARCH
# ============================================================================

class UltimateInstructionBuilder:
    """Builds comprehensive instructions for the Ultimate agent."""
    
    BASE_INSTRUCTIONS = """You are an elite business intelligence AI agent specializing in the Romanian market, with access to official APIs AND web search for comprehensive analysis.

YOUR COMPLETE TOOLKIT:

🏢 TARGETARE OFFICIAL API TOOLS (12 tools):
1. get_company_profile - Complete company intelligence from official Targetare API v1
2. get_company_financials - Official financial statements and metrics
3. get_company_phones - Official phone numbers
4. get_company_emails - Official email addresses  
5. get_company_administrators - Management and administrators
6. get_company_websites - Online presence and social media
7. search_companies_by_registration_date - Find companies by registration date
8. analyze_company_financials - Advanced financial analysis with metrics
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

🔍 WEB SEARCH & RESEARCH (Google Search Tool):
- Real-time market trends and industry insights
- Competitor news and developments
- Industry reports and analysis
- Consumer trends and preferences
- Regulatory changes and updates
- Success stories and case studies
- Economic indicators and forecasts
- Technology trends affecting industries

DATA SOURCES:
- Targetare API: Official Romanian company data from onrc.ro, mfinante.ro, anaf.ro
- Google Maps: Real-time location and business intelligence
- Web Search: Current market trends, news, and industry insights
- GCP Secret Manager: Secure API key management

ENHANCED ANALYSIS FRAMEWORK:

When conducting market research, ALWAYS combine:
1. Official company data (Targetare)
2. Location intelligence (Google Maps)
3. Current market trends (Web Search)

For COMPREHENSIVE business analysis:

STEP 1 - Gather Official Data:
- Use Targetare API for company financials
- Get competitor profiles and financial health
- Analyze market segment by CAEN code

STEP 2 - Location Intelligence:
- Find optimal locations using Google Maps
- Analyze competitor density in areas
- Calculate accessibility scores
- Compare multiple potential locations

STEP 3 - Market Research (WEB SEARCH):
- Research current industry trends
- Find news about competitors
- Look for consumer preferences
- Check for regulatory changes
- Identify success stories in the industry
- Gather economic indicators

STEP 4 - Synthesis:
- Cross-reference all data sources
- Identify patterns and opportunities
- Provide actionable recommendations
- Include risk assessment
- Cite all sources

WEB SEARCH BEST PRACTICES:

✓ DO use web search for:
- Current market trends and forecasts
- Recent news about industry or competitors
- Consumer behavior and preferences
- Technology trends
- Regulatory updates
- Case studies and best practices
- Economic indicators
- Industry reports and analyses

✓ Search queries should be:
- Specific and targeted
- Include location (Romania, București, etc.)
- Include industry or business type
- Use current year for trends (2025)
- In English for broader results, Romanian for local insights

Example search queries:
- "coffee shop trends Romania 2025"
- "Cluj-Napoca startup ecosystem"
- "Romanian restaurant industry analysis"
- "București real estate commercial trends"
- "technology adoption Romania SME"

RESPONSE GUIDELINES:

✓ DO:
- Use all three data sources (Targetare, Maps, Web Search)
- Validate Romanian tax IDs (CUI/CIF format)
- Provide specific, actionable recommendations
- Show calculations and methodology
- Cite sources for all claims (specify: Targetare, Google Maps, or Web Search)
- Handle both Romanian and English queries
- Use proper Romanian business terminology
- Consider financial, geographic, AND market trend factors
- Include recent news and trends in analysis

✗ DON'T:
- Rely on only one data source
- Make assumptions without data
- Ignore location factors for physical businesses
- Overlook competitor analysis
- Forget to check data freshness
- Skip web research for dynamic markets
- Ignore current trends and news

ROMANIAN MARKET SPECIFICS:

Tax ID Formats:
- Clean format: 12345678 (2-10 digits)
- With prefix: RO12345678 or CUI 12345678
- All formats are automatically validated

CAEN Codes (Industry Classification):
- 6201: Computer programming
- 4711: Retail in non-specialized stores
- 5610: Restaurants
- 5621: Event catering
- 4634: Beverage wholesale
- And many more (ask Targetare for specific codes)

Major Cities & Characteristics:
- București (Bucharest) - Capital, largest market, highest competition, strong purchasing power
- Cluj-Napoca - Tech hub, young demographics, university city, growing market
- Timișoara - Western gate, EU proximity, international connections, industrial base
- Iași - Eastern capital, education center, growing tech scene
- Brașov - Tourism, mountain region, manufacturing, expatriate community
- Constanța - Port city, tourism, logistics hub

ANALYSIS WORKFLOW EXAMPLES:

1. MARKET ENTRY ANALYSIS:
   a. Research industry trends (Web Search: "restaurant trends Romania 2025")
   b. Analyze competitor financials (Targetare: compare top competitors)
   c. Find optimal locations (Google Maps: competitor density + accessibility)
   d. Synthesize insights and recommend strategy

2. COMPETITOR INTELLIGENCE:
   a. Get official company data (Targetare: profile, financials)
   b. Find competitor locations (Google Maps: business locations)
   c. Research recent news (Web Search: company news, market position)
   d. Assess risks and opportunities

3. DUE DILIGENCE:
   a. Complete financial analysis (Targetare: financials + risk assessment)
   b. Location analysis (Google Maps: property values, accessibility)
   c. Market position research (Web Search: reputation, news, trends)
   d. Comprehensive report with recommendations

4. TREND ANALYSIS:
   a. Industry trends (Web Search: current trends, forecasts)
   b. Market data (Targetare: segment analysis by CAEN)
   c. Geographic opportunities (Google Maps: underserved areas)
   d. Strategy recommendations

Remember: You have access to OFFICIAL APIs with real data PLUS current web intelligence. Use this comprehensive toolkit to provide the most accurate, timely, and valuable insights possible.

For every analysis, aim to:
1. Use multiple data sources
2. Validate with current web research
3. Provide specific recommendations
4. Include both opportunities and risks
5. Cite all sources clearly"""

    @staticmethod
    def build(web_search_enabled: bool = True) -> str:
        """Build complete agent instructions."""
        instructions = UltimateInstructionBuilder.BASE_INSTRUCTIONS
        
        if not web_search_enabled:
            instructions += "\n\nNOTE: Web search is currently disabled. Using only Targetare and Google Maps data."
        
        return instructions


# ============================================================================
# AGENT BUILDER WITH WEB SEARCH
# ============================================================================

class UltimateAgentBuilder:
    """Builds the Ultimate Business Intelligence Agent with web search."""
    
    @staticmethod
    def create(config: Optional[UltimateAgentConfig] = None) -> Agent:
        """Create the ultimate business intelligence agent with web search."""
        if config is None:
            config = UltimateAgentConfig.from_environment()
        
        logger.info("=" * 70)
        logger.info("ULTIMATE BUSINESS INTELLIGENCE AI - Official API + Web Search")
        logger.info("=" * 70)
        
        # Setup authentication
        if not VertexAIAuthenticator.setup(config):
            raise RuntimeError("Failed to setup Vertex AI authentication")
        
        # Prepare tools list
        tools = []
        
        # Add MCP toolset (Targetare + Google Maps)
        try:
            toolset = MCPConnectionManager.create_toolset(config)
            tools.append(toolset)
            logger.info(f"✓ Created unified MCP toolset with 25 tools")
            logger.info(f"  - 12 Targetare tools (Official API v1)")
            logger.info(f"  - 13 Google Maps tools (Location intelligence)")
            
        except Exception as e:
            logger.error(f"✗ Failed to create toolset: {e}")
            raise RuntimeError(f"Toolset creation failed: {e}")
        
        # Add Google Search tool if enabled and configured
        web_search_enabled = False
        if config.enable_web_search:
            if config.custom_search_api_key and config.custom_search_cx:
                try:
                    # Configure Google Search with Custom Search Engine
                    search_tool = google_search(
                        google_search_api_key=config.custom_search_api_key,
                        google_search_cx=config.custom_search_cx
                    )
                    tools.append(search_tool)
                    web_search_enabled = True
                    logger.info(f"✓ Google Custom Search enabled")
                    logger.info(f"  - API Key: {'*' * 8}{config.custom_search_api_key[-4:]}")
                    logger.info(f"  - Search Engine ID: {config.custom_search_cx}")
                except Exception as e:
                    logger.warning(f"⚠ Could not enable Google Search: {e}")
                    logger.warning("  Continuing without web search capabilities")
            else:
                logger.warning(f"⚠ Google Custom Search not configured")
                logger.warning("  Missing: GOOGLE_CUSTOM_SEARCH_API_KEY or GOOGLE_CUSTOM_SEARCH_CX")
                logger.warning("  Web search capabilities will be limited")
        else:
            logger.info(f"ℹ Web search disabled by configuration")
        
        # Build agent instructions
        instructions = UltimateInstructionBuilder.build(web_search_enabled)
        
        # Create agent
        try:        
            agent = Agent(
                name="ultimate_business_intelligence_agent_with_search",
                model=config.model,
                description="Ultimate business intelligence combining official Romanian company data (Targetare API v1), location intelligence (Google Maps), and real-time web search for comprehensive market analysis",
                instruction=instructions,
                tools=tools,
            )
            
            logger.info("✓ Agent created successfully")
            logger.info("=" * 70)
            logger.info("ULTIMATE AGENT READY - FULL INTELLIGENCE SUITE!")
            logger.info(f"  Model: {config.model}")
            logger.info(f"  MCP Server: {config.mcp_server_url}")
            logger.info(f"  Total Tools: {25 + (1 if web_search_enabled else 0)}")
            logger.info(f"    ├─ Targetare: 12 tools (Official API)")
            logger.info(f"    ├─ Google Maps: 13 tools")
            logger.info(f"    └─ Web Search: {'✓ Enabled' if web_search_enabled else '✗ Disabled'}")
            logger.info(f"  APIs: api.targetare.ro + Google Maps + {'Google Custom Search' if web_search_enabled else 'N/A'}")
            logger.info(f"  Security: GCP Secret Manager integration")
            logger.info(f"  Environment: {'Cloud Run' if MCPConnectionManager.is_cloud_run() else 'Local'}")
            logger.info("=" * 70)
            
            return agent
            
        except Exception as e:
            logger.error(f"✗ Failed to create agent: {e}")
            raise RuntimeError(f"Agent creation failed: {e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def create_business_intelligence_agent(config: Optional[UltimateAgentConfig] = None) -> Agent:
    """
    Main entry point to create the ultimate business intelligence agent with web search.
    
    Args:
        config: Optional configuration (uses environment variables if None)
        
    Returns:
        Configured Agent instance ready to use
        
    Example:
        >>> agent = create_business_intelligence_agent()
        >>> result = agent.query("Complete due diligence on Romanian company CUI 35790107")
        >>> result = agent.query("Should I open a cafe in Cluj-Napoca? Analyze locations, competitors, and current trends")
        >>> result = agent.query("Research coffee shop trends in Romania and recommend best location")
    """
    return UltimateAgentBuilder.create(config)


# Create the agent instance for export
try:
    root_agent = create_business_intelligence_agent()
    logger.info("✓ root_agent exported successfully")
except Exception as e:
    logger.error(f"✗ Failed to create root_agent: {e}")
    logger.error("  Please check your configuration and MCP server")
    logger.error(f"  Expected MCP server at: http://localhost:8000/mcp")
    logger.error("  Run: python ultimate_business_intelligence_complete.py")
    root_agent = None


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ULTIMATE BUSINESS INTELLIGENCE AI AGENT")
    print("Official APIs + Web Search • Complete Market Intelligence")
    print("=" * 80)
    
    # Display configuration
    config = UltimateAgentConfig.from_environment()
    print(f"\n📋 CONFIGURATION:")
    print(f"  Model: {config.model}")
    print(f"  Project: {config.project_id or 'Not set'}")
    print(f"  Location: {config.location}")
    print(f"  Environment: {'Cloud Run' if MCPConnectionManager.is_cloud_run() else 'Local Development'}")
    
    print(f"\n🔌 DATA SOURCES:")
    print(f"  ✓ MCP Server: {config.mcp_server_url}")
    print(f"    ├─ Targetare: 12 tools (Official API v1)")
    print(f"    ├─ Google Maps: 13 tools (Platform APIs)")
    print(f"    └─ Total MCP: 25 tools")
    
    web_search_configured = bool(config.custom_search_api_key and config.custom_search_cx)
    print(f"  {'✓' if web_search_configured else '✗'} Google Custom Search: {'Configured' if web_search_configured else 'Not configured'}")
    if web_search_configured:
        print(f"    └─ Search Engine ID: {config.custom_search_cx}")
    
    print(f"\n🎯 ENHANCED USE CASES:")
    print(f"  • Market Entry Analysis - locations + financials + trends")
    print(f"  • Competitor Intelligence - data + geography + news")
    print(f"  • Due Diligence - complete picture with web research")
    print(f"  • Trend Analysis - combine official data with market trends")
    print(f"  • Strategic Planning - all intelligence sources combined")
    
    print(f"\n💬 EXAMPLE QUERIES:")
    print(f"  1. 'Research coffee shop trends in Romania and find best location in Cluj'")
    print(f"  2. 'Complete analysis of CUI 35790107 including news and market position'")
    print(f"  3. 'Should I open a restaurant in București? Include current trends'")
    print(f"  4. 'Find tech startups in Cluj-Napoca with recent funding news'")
    print(f"  5. 'Market entry strategy for bakery in Timișoara with trend analysis'")
    
    print("\n" + "=" * 80)
    print("Agent ready with complete intelligence capabilities!")
    print("Official Data • Location Intelligence • Web Research")
    print("=" * 80 + "\n")