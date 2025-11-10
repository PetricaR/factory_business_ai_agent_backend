"""
Business Intelligence AI Agent - MULTI-SERVER ARCHITECTURE
===========================================================

Enterprise-grade AI agent using THREE specialized MCP servers:
1. Business Planning Server (9 tools) - Complete business plan generation
2. Financial Intelligence Server (9 tools) - Romanian company financial analysis  
3. Location Intelligence Server (13 tools) - Google Maps location analysis
+ Google Search (1 tool) - Web research and market intelligence

TOTAL: 32 TOOLS for comprehensive business intelligence

Perfect for entrepreneurs, investors, and business consultants.

Key Capabilities:
- Complete business plan generation with market research
- Deep financial analysis of Romanian companies
- Location intelligence and competitor analysis
- Real-time web search for market trends
- Multi-source data integration and synthesis
- Strategic recommendations with actionable insights
"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from dotenv import load_dotenv
from google.adk.tools import google_search

# ADK imports
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
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
    BUSINESS_PLAN = "business_plan"  # Complete business planning
    FINANCIAL_ANALYSIS = "financial"  # Romanian company financial analysis
    LOCATION_INTELLIGENCE = "location"  # Location and competition analysis
    MARKET_RESEARCH = "market_research"  # Web-based market research
    COMPREHENSIVE = "comprehensive"  # Full multi-source analysis
    DUE_DILIGENCE = "due_diligence"  # Complete due diligence
    COMPETITOR_INTEL = "competitor_intel"  # Deep competitor analysis
    MARKET_ENTRY = "market_entry"  # Market entry strategy


@dataclass
class MultiServerAgentConfig:
    """Configuration for Multi-Server Business Intelligence Agent."""
    # Model configuration
    model: str = "gemini-2.5-flash"
    
    # MCP Server URLs (Cloud Run deployed)
    business_plan_server_url: str = "https://factory-ai-agent-business-mcp-server-845266575866.europe-west1.run.app/sse"
    financial_intel_server_url: str = "https://factory-ai-agent-competition-mcp-server-845266575866.europe-west1.run.app/sse"
    location_intel_server_url: str = "https://factory-ai-agent-maps-mcp-server-845266575866.europe-west1.run.app/sse"
    
    # Google Cloud configuration
    project_id: Optional[str] = None
    location: str = "us-central1"
    
    # Connection settings
    timeout: int = 90  # Increased for complex operations
    sse_read_timeout: int = 180
    max_retries: int = 3
    
    # Feature flags
    enable_business_planning: bool = True
    enable_financial_intelligence: bool = True
    enable_location_intelligence: bool = True
    enable_web_search: bool = True
    
    # Google Custom Search configuration
    custom_search_api_key: Optional[str] = None
    custom_search_cx: Optional[str] = None
    
    @classmethod
    def from_environment(cls) -> 'MultiServerAgentConfig':
        """Create configuration from environment variables."""
        return cls(
            model=os.getenv("MODEL", "gemini-2.5-flash"),
            business_plan_server_url=os.getenv(
                "BUSINESS_PLAN_SERVER_URL",
                "https://factory-ai-agent-business-mcp-server-845266575866.europe-west1.run.app/sse"
            ),
            financial_intel_server_url=os.getenv(
                "FINANCIAL_INTEL_SERVER_URL",
                "https://factory-ai-agent-competition-mcp-server-845266575866.europe-west1.run.app/sse"
            ),
            location_intel_server_url=os.getenv(
                "LOCATION_INTEL_SERVER_URL",
                "https://factory-ai-agent-maps-mcp-server-845266575866.europe-west1.run.app/sse"
            ),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            enable_business_planning=os.getenv("ENABLE_BUSINESS_PLANNING", "true").lower() == "true",
            enable_financial_intelligence=os.getenv("ENABLE_FINANCIAL_INTEL", "true").lower() == "true",
            enable_location_intelligence=os.getenv("ENABLE_LOCATION_INTEL", "true").lower() == "true",
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
    def setup(config: MultiServerAgentConfig) -> bool:
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
    """Manages connections to multiple MCP servers."""
    
    @staticmethod
    def is_cloud_run() -> bool:
        """Check if running in Cloud Run environment."""
        return os.getenv("K_SERVICE") is not None
    
    @staticmethod
    def get_connection_params(server_url: str, timeout: int = 90):
        """Get MCP connection parameters with authentication for Cloud Run."""
        headers = {}
        
        # Add authentication for Cloud Run endpoints
        if "run.app" in server_url:
            logger.info(f"Cloud Run endpoint detected - using authenticated connection for {server_url}")
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
    def create_toolsets(config: MultiServerAgentConfig) -> List[MCPToolset]:
        """Create toolsets for all enabled MCP servers."""
        toolsets = []
        
        # Business Planning Server (9 tools)
        if config.enable_business_planning:
            try:
                connection_params = MCPConnectionManager.get_connection_params(
                    config.business_plan_server_url,
                    config.timeout
                )
                toolset = MCPToolset(connection_params=connection_params)
                toolsets.append(toolset)
                logger.info("✓ Business Planning MCP toolset created")
                logger.info(f"  Server: {config.business_plan_server_url}")
                logger.info(f"  Tools: 9 (complete business plan generation)")
            except Exception as e:
                logger.error(f"✗ Failed to create Business Planning toolset: {e}")
        
        # Financial Intelligence Server (9 tools)
        if config.enable_financial_intelligence:
            try:
                connection_params = MCPConnectionManager.get_connection_params(
                    config.financial_intel_server_url,
                    config.timeout
                )
                toolset = MCPToolset(connection_params=connection_params)
                toolsets.append(toolset)
                logger.info("✓ Financial Intelligence MCP toolset created")
                logger.info(f"  Server: {config.financial_intel_server_url}")
                logger.info(f"  Tools: 9 (Romanian company financial analysis)")
            except Exception as e:
                logger.error(f"✗ Failed to create Financial Intelligence toolset: {e}")
        
        # Location Intelligence Server (13 tools)
        if config.enable_location_intelligence:
            try:
                connection_params = MCPConnectionManager.get_connection_params(
                    config.location_intel_server_url,
                    config.timeout
                )
                toolset = MCPToolset(connection_params=connection_params)
                toolsets.append(toolset)
                logger.info("✓ Location Intelligence MCP toolset created")
                logger.info(f"  Server: {config.location_intel_server_url}")
                logger.info(f"  Tools: 13 (Google Maps location analysis)")
            except Exception as e:
                logger.error(f"✗ Failed to create Location Intelligence toolset: {e}")
        
        if not toolsets:
            raise RuntimeError("No MCP toolsets were successfully created")
        
        return toolsets


# ============================================================================
# ENHANCED AGENT INSTRUCTIONS FOR MULTI-SERVER ARCHITECTURE
# ============================================================================

class MultiServerInstructionBuilder:
    """Builds comprehensive instructions for the multi-server agent."""
    
    BASE_INSTRUCTIONS = """You are an elite business intelligence AI agent with access to THREE specialized MCP servers and web search capabilities.

YOUR COMPLETE TOOLKIT (32 TOOLS):

🎯 BUSINESS PLANNING SERVER (9 tools):
1. generate_complete_business_plan - Full end-to-end business plan with all sections
2. research_market_opportunity - Deep market research and competitive analysis
3. analyze_location_costs - Real estate and operating cost analysis
4. plan_staffing_requirements - Staffing needs and market salaries
5. calculate_equipment_costs - Equipment, technology, and resource costs
6. analyze_competition - Competitive analysis with SWOT
7. create_gtm_strategy - Go-to-market and sales strategy
8. project_financials - 3-year financial projections
9. create_executive_summary - Executive summary generation

💰 FINANCIAL INTELLIGENCE SERVER (9 tools):
10. find_company_cui_by_name - Find Romanian company CUI by name search
11. get_company_financials - Raw financial data from official API
12. get_company_profile - Company registration and context
13. analyze_financial_ratios - Comprehensive ratio analysis (15+ ratios)
14. compare_financial_performance - Multi-company comparison
15. assess_credit_risk - Credit scoring and risk assessment
16. analyze_financial_trends - Year-over-year trend analysis
17. generate_financial_report - Complete financial intelligence report
18. benchmark_against_industry - Industry benchmarking

🗺️ LOCATION INTELLIGENCE SERVER (13 tools):
19. search_locations_by_city - Find business locations in cities
20. analyze_competitor_density - Competition density analysis
21. calculate_accessibility_score - Location accessibility scoring
22. geocode_address - Address to coordinates
23. reverse_geocode_coordinates - Coordinates to address
24. find_nearby_amenities - Nearby amenities search
25. get_distance_matrix - Distance calculations
26. get_directions - Turn-by-turn directions
27. get_elevation - Elevation data
28. get_timezone - Timezone information
29. find_place_from_text - Text-based location search
30. compare_multiple_locations - Multi-location comparison
31. get_location_details - Detailed place information

🔍 WEB SEARCH & RESEARCH (1 tool):
32. google_search - Real-time market trends, news, and industry insights

DATA SOURCES & AUTHENTICATION:
- Business Planning: Uses Google Gemini 2.0 Flash with web search
- Financial Intelligence: Official Romanian APIs (Targetare.ro) + Google Custom Search
- Location Intelligence: Google Maps Platform (7 APIs)
- Web Search: Google Custom Search Engine
- All servers deployed on Google Cloud Run with secure authentication

MULTI-SERVER ANALYSIS FRAMEWORK:

When conducting comprehensive business intelligence, ORCHESTRATE across all servers:

STEP 1 - Business Context (Business Planning Server):
- Research market opportunity and sizing
- Identify target customers and competitors
- Analyze industry trends and dynamics

STEP 2 - Financial Intelligence (Financial Intelligence Server):
- For Romanian companies: Find CUI, get financials, analyze ratios
- Assess credit risk and financial health
- Compare against competitors and industry benchmarks

STEP 3 - Location Analysis (Location Intelligence Server):
- Find optimal locations using Google Maps
- Analyze competitor density in areas
- Calculate accessibility scores
- Compare multiple potential locations

STEP 4 - Market Research (Web Search):
- Research current industry trends
- Find news about competitors and market
- Look for consumer preferences and insights
- Check for regulatory changes
- Identify success stories and best practices

STEP 5 - Synthesis & Recommendations:
- Cross-reference all data sources
- Identify patterns and opportunities
- Provide actionable, data-driven recommendations
- Include risk assessment from all dimensions
- Cite sources clearly (specify which server/tool)

ORCHESTRATION PATTERNS:

For BUSINESS PLAN GENERATION:
1. generate_complete_business_plan (Business Planning Server)
2. Enhance with google_search for current trends (Web Search)
3. Add location analysis if physical location (Location Intelligence)
4. Include competitor financial analysis if in Romania (Financial Intelligence)

For DUE DILIGENCE on Romanian companies:
1. find_company_cui_by_name (Financial Intelligence)
2. generate_financial_report (Financial Intelligence)
3. assess_credit_risk (Financial Intelligence)
4. get_location_details for company locations (Location Intelligence)
5. google_search for recent news and reputation (Web Search)

For MARKET ENTRY STRATEGY:
1. research_market_opportunity (Business Planning)
2. google_search for current trends (Web Search)
3. analyze_location_costs (Business Planning)
4. search_locations_by_city (Location Intelligence)
5. analyze_competitor_density (Location Intelligence)
6. If competitors in Romania: analyze_financial_ratios (Financial Intelligence)

For COMPETITOR INTELLIGENCE:
1. google_search for company news and market position (Web Search)
2. If Romanian: find_company_cui_by_name + generate_financial_report (Financial Intelligence)
3. get_location_details for their locations (Location Intelligence)
4. analyze_competitor_density around their locations (Location Intelligence)
5. create_gtm_strategy to differentiate (Business Planning)

RESPONSE GUIDELINES:

✓ DO:
- Use tools from multiple servers for comprehensive analysis
- Orchestrate tools in logical sequence
- Validate findings across different data sources
- Provide specific, actionable recommendations
- Show calculations and methodology
- Cite sources clearly (specify server/tool used)
- Handle both Romanian and English queries
- Consider financial, geographic, AND market trend factors
- Use parallel tool calls when possible for efficiency

✗ DON'T:
- Rely on only one server/data source
- Make assumptions without data
- Ignore location factors for physical businesses
- Overlook competitor analysis
- Forget to check data freshness
- Skip web research for dynamic markets
- Ignore current trends and news

SERVER-SPECIFIC NOTES:

Business Planning Server:
- Uses Gemini 2.0 Flash with web search built-in
- Can generate complete 50+ page business plans
- Bottom-up financial modeling approach
- Best for: New business planning, feasibility studies

Financial Intelligence Server:
- Official Romanian company data (ONRC, ANAF, MFinante)
- Real-time financial statements and ratios
- Credit risk assessment and scoring
- Best for: Romanian company analysis, due diligence

Location Intelligence Server:
- Google Maps Platform with 7 APIs
- Real-time location and business data
- Competitor density and accessibility analysis
- Best for: Site selection, geographic analysis

ROMANIAN MARKET SPECIFICS:

Tax ID Formats (Financial Intelligence):
- Clean format: 12345678 (2-10 digits)
- With prefix: RO12345678 or CUI 12345678
- Always use find_company_cui_by_name if you only have company name

Major Romanian Cities (Location Intelligence):
- București (Bucharest) - Capital, largest market, 44.4268°N, 26.1025°E
- Cluj-Napoca - Tech hub, university city, 46.7712°N, 23.6236°E
- Timișoara - Western gateway, 45.7489°N, 21.2087°E
- Iași - Eastern capital, 47.1585°N, 27.6014°E
- Brașov - Tourism center, 45.6427°N, 25.5887°E
- Constanța - Port city, 44.1598°N, 28.6348°E

EXAMPLE WORKFLOWS:

1. COMPLETE BUSINESS PLAN for Coffee Shop in Cluj-Napoca:
   a. generate_complete_business_plan(business_type="Coffee Shop", location="Cluj-Napoca", budget=100000)
   b. google_search("coffee shop trends Romania 2025")
   c. search_locations_by_city(city="Cluj-Napoca", business_type="cafe")
   d. analyze_competitor_density(lat=46.7712, lng=23.6236, business_type="cafe")
   e. calculate_accessibility_score(lat=46.7712, lng=23.6236)

2. DUE DILIGENCE on Romanian company:
   a. find_company_cui_by_name(company_name="Dedeman SRL")
   b. generate_financial_report(tax_id=extracted_cui)
   c. assess_credit_risk(tax_id=extracted_cui)
   d. google_search("Dedeman Romania news 2025")
   e. get_location_details(place_id=company_location)

3. MARKET ENTRY STRATEGY for Restaurant:
   a. research_market_opportunity(business_type="Restaurant", location="Bucharest")
   b. google_search("restaurant trends Romania 2025")
   c. analyze_location_costs(business_type="Restaurant", location="Bucharest")
   d. compare_multiple_locations(locations=[...], business_type="restaurant")
   e. create_gtm_strategy(business_type="Restaurant", location="Bucharest")

Remember: You have access to OFFICIAL APIs with real data PLUS comprehensive location intelligence AND web research. Use this complete toolkit to provide the most accurate, timely, and valuable insights possible.

For every analysis, aim to:
1. Use multiple servers and data sources
2. Validate with current web research
3. Provide specific, actionable recommendations
4. Include both opportunities and risks
5. Cite sources clearly (specify which server)
6. Consider geographic, financial, and market factors"""

    @staticmethod
    def build(config: MultiServerAgentConfig) -> str:
        """Build complete agent instructions."""
        instructions = MultiServerInstructionBuilder.BASE_INSTRUCTIONS
        
        # Add server status notes
        status_notes = "\n\nSERVER STATUS:"
        if config.enable_business_planning:
            status_notes += f"\n✓ Business Planning Server: ENABLED ({config.business_plan_server_url})"
        if config.enable_financial_intelligence:
            status_notes += f"\n✓ Financial Intelligence Server: ENABLED ({config.financial_intel_server_url})"
        if config.enable_location_intelligence:
            status_notes += f"\n✓ Location Intelligence Server: ENABLED ({config.location_intel_server_url})"
        if config.enable_web_search:
            status_notes += "\n✓ Web Search: ENABLED"
        else:
            status_notes += "\n✗ Web Search: DISABLED"
        
        instructions += status_notes
        
        return instructions


# ============================================================================
# MULTI-SERVER AGENT BUILDER
# ============================================================================

class MultiServerAgentBuilder:
    """Builds the Multi-Server Business Intelligence Agent."""
    
    @staticmethod
    def create(config: Optional[MultiServerAgentConfig] = None) -> Agent:
        """Create the multi-server business intelligence agent."""
        if config is None:
            config = MultiServerAgentConfig.from_environment()
        
        logger.info("=" * 70)
        logger.info("MULTI-SERVER BUSINESS INTELLIGENCE AI AGENT")
        logger.info("=" * 70)
        
        # Setup authentication
        if not VertexAIAuthenticator.setup(config):
            raise RuntimeError("Failed to setup Vertex AI authentication")
        
        # Prepare tools list
        tools = []
        total_tools = 0
        
        # Add MCP toolsets (Business Planning + Financial Intelligence + Location Intelligence)
        try:
            toolsets = MCPConnectionManager.create_toolsets(config)
            tools.extend(toolsets)
            
            server_count = len(toolsets)
            if config.enable_business_planning:
                total_tools += 9
            if config.enable_financial_intelligence:
                total_tools += 9
            if config.enable_location_intelligence:
                total_tools += 13
            
            logger.info(f"✓ Created {server_count} MCP toolsets with {total_tools} total tools")
            
        except Exception as e:
            logger.error(f"✗ Failed to create toolsets: {e}")
            raise RuntimeError(f"Toolset creation failed: {e}")
        
        # Add Google Search tool if enabled and configured
        web_search_enabled = False
        if config.enable_web_search:
            if config.custom_search_api_key and config.custom_search_cx:
                try:
                    search_tool = google_search(
                        google_search_api_key=config.custom_search_api_key,
                        google_search_cx=config.custom_search_cx
                    )
                    tools.append(search_tool)
                    web_search_enabled = True
                    total_tools += 1
                    logger.info(f"✓ Google Custom Search enabled")
                    logger.info(f"  - API Key: {'*' * 8}{config.custom_search_api_key[-4:]}")
                    logger.info(f"  - Search Engine ID: {config.custom_search_cx}")
                except Exception as e:
                    logger.warning(f"⚠ Could not enable Google Search: {e}")
                    logger.warning("  Continuing without web search capabilities")
            else:
                logger.warning(f"⚠ Google Custom Search not configured")
                logger.warning("  Missing: GOOGLE_CUSTOM_SEARCH_API_KEY or GOOGLE_CUSTOM_SEARCH_CX")
        else:
            logger.info(f"ℹ Web search disabled by configuration")
        
        # Build agent instructions
        instructions = MultiServerInstructionBuilder.build(config)
        
        # Create agent
        try:
            agent = Agent(
                name="multi_server_business_intelligence_agent",
                model=config.model,
                description="Enterprise business intelligence combining business planning, financial analysis, location intelligence, and web research across three specialized MCP servers",
                instruction=instructions,
                tools=tools,
            )
            
            logger.info("✓ Agent created successfully")
            logger.info("=" * 70)
            logger.info("MULTI-SERVER AGENT READY - COMPLETE INTELLIGENCE SUITE!")
            logger.info(f"  Model: {config.model}")
            logger.info(f"  Total MCP Servers: {len(toolsets)}")
            logger.info(f"  Total Tools: {total_tools}")
            
            if config.enable_business_planning:
                logger.info(f"    ├─ Business Planning: 9 tools")
                logger.info(f"    │  └─ {config.business_plan_server_url}")
            
            if config.enable_financial_intelligence:
                logger.info(f"    ├─ Financial Intelligence: 9 tools")
                logger.info(f"    │  └─ {config.financial_intel_server_url}")
            
            if config.enable_location_intelligence:
                logger.info(f"    ├─ Location Intelligence: 13 tools")
                logger.info(f"    │  └─ {config.location_intel_server_url}")
            
            logger.info(f"    └─ Web Search: {'✓ Enabled (1 tool)' if web_search_enabled else '✗ Disabled'}")
            
            logger.info(f"  APIs Integrated:")
            logger.info(f"    • Google Gemini 2.0 Flash (Business Planning)")
            logger.info(f"    • Targetare.ro Official API (Financial Intelligence)")
            logger.info(f"    • Google Maps Platform (Location Intelligence)")
            logger.info(f"    • Google Custom Search (Web Research)")
            logger.info(f"  Security: Cloud Run with IAM authentication")
            logger.info(f"  Environment: {'Cloud Run' if MCPConnectionManager.is_cloud_run() else 'Local'}")
            logger.info("=" * 70)
            
            return agent
            
        except Exception as e:
            logger.error(f"✗ Failed to create agent: {e}")
            raise RuntimeError(f"Agent creation failed: {e}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def create_business_intelligence_agent(config: Optional[MultiServerAgentConfig] = None) -> Agent:
    """
    Main entry point to create the multi-server business intelligence agent.
    
    Args:
        config: Optional configuration (uses environment variables if None)
        
    Returns:
        Configured Agent instance ready to use
        
    Example:
        >>> agent = create_business_intelligence_agent()
        >>> 
        >>> # Complete business plan
        >>> result = agent.query("Create a complete business plan for a coffee shop in Cluj-Napoca with 100,000 euro budget")
        >>> 
        >>> # Due diligence on Romanian company
        >>> result = agent.query("Complete due diligence on Dedeman SRL including financials and locations")
        >>> 
        >>> # Market entry strategy
        >>> result = agent.query("Should I open a restaurant in București? Analyze locations, competitors, financials, and trends")
        >>> 
        >>> # Comprehensive analysis
        >>> result = agent.query("Find the best location for a gym in Romania, analyze top 3 cities")
    """
    return MultiServerAgentBuilder.create(config)


# Create the agent instance for export
try:
    root_agent = create_business_intelligence_agent()
    logger.info("✓ root_agent exported successfully")
except Exception as e:
    logger.error(f"✗ Failed to create root_agent: {e}")
    logger.error("  Please check your configuration and MCP servers")
    logger.error("  Expected MCP servers at:")
    root_agent = None


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 90)
    print("MULTI-SERVER BUSINESS INTELLIGENCE AI AGENT")
    print("Enterprise Architecture • Three Specialized MCP Servers • 32 Total Tools")
    print("=" * 90)
    
    # Display configuration
    config = MultiServerAgentConfig.from_environment()
    print(f"\n📋 CONFIGURATION:")
    print(f"  Model: {config.model}")
    print(f"  Project: {config.project_id or 'Not set'}")
    print(f"  Location: {config.location}")
    print(f"  Environment: {'Cloud Run' if MCPConnectionManager.is_cloud_run() else 'Local Development'}")
    
    print(f"\n🔌 MCP SERVERS (3):")
    
    if config.enable_business_planning:
        print(f"  1. BUSINESS PLANNING SERVER (9 tools)")
        print(f"     {config.business_plan_server_url}")
        print(f"     • Complete business plan generation")
        print(f"     • Market research and analysis")
        print(f"     • Financial projections")
    
    if config.enable_financial_intelligence:
        print(f"  2. FINANCIAL INTELLIGENCE SERVER (9 tools)")
        print(f"     {config.financial_intel_server_url}")
        print(f"     • Romanian company financial analysis")
        print(f"     • Credit risk assessment")
        print(f"     • Industry benchmarking")
    
    if config.enable_location_intelligence:
        print(f"  3. LOCATION INTELLIGENCE SERVER (13 tools)")
        print(f"     {config.location_intel_server_url}")
        print(f"     • Google Maps location analysis")
        print(f"     • Competitor density mapping")
        print(f"     • Accessibility scoring")
    
    web_search_configured = bool(config.custom_search_api_key and config.custom_search_cx)
    print(f"\n  + WEB SEARCH: {'✓ Enabled (1 tool)' if web_search_configured else '✗ Not configured'}")
    if web_search_configured:
        print(f"     Google Custom Search Engine")
    
    total_tools = 0
    if config.enable_business_planning:
        total_tools += 9
    if config.enable_financial_intelligence:
        total_tools += 9
    if config.enable_location_intelligence:
        total_tools += 13
    if web_search_configured:
        total_tools += 1
    
    print(f"\n  TOTAL: {total_tools} TOOLS AVAILABLE")
    
    print(f"\n🎯 ENTERPRISE USE CASES:")
    print(f"  • Complete Business Planning - Full 50+ page business plans")
    print(f"  • Financial Due Diligence - Romanian company analysis")
    print(f"  • Market Entry Strategy - Location + financials + trends")
    print(f"  • Competitor Intelligence - Multi-dimensional analysis")
    print(f"  • Site Selection - Data-driven location selection")
    print(f"  • Investment Analysis - Comprehensive evaluation")
    
    print(f"\n💬 EXAMPLE QUERIES:")
    print(f"  1. 'Create complete business plan for coffee shop in Cluj-Napoca with 100k budget'")
    print(f"  2. 'Complete due diligence on Dedeman SRL - financials, locations, and news'")
    print(f"  3. 'Should I open a restaurant in București? Full analysis with trends'")
    print(f"  4. 'Compare Timișoara vs Cluj-Napoca for opening a tech startup'")
    print(f"  5. 'Find and analyze top 5 retail companies in Romania by financial health'")
    
    print("\n" + "=" * 90)
    print("Agent ready with enterprise multi-server architecture!")
    print("Business Planning • Financial Intelligence • Location Intelligence • Web Research")
    print("=" * 90 + "\n")