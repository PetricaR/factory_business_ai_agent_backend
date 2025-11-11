"""
Factory Finder AI Agent
=======================

Voice-enabled location intelligence agent for Romanian entrepreneurs
using Google ADK with MCP Google Maps integration.

Features:
- Real-time audio streaming with transcription
- Location analysis and comparison
- Competitor density analysis  
- Business cost estimation
- Google Maps integration via MCP
- Multi-city support for Romania
"""

from google.adk.agents import Agent
from dotenv import load_dotenv
import os
from typing import Optional  # ✅ Added for proper type annotations

# ============================================================================
# UPDATED MCP IMPORTS FOR GOOGLE ADK (Latest API)
# ============================================================================
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

load_dotenv()

# Import common components
from .common import (
    MODEL,
    SYSTEM_INSTRUCTION,
    get_city_info,
    estimate_business_costs,
    compare_locations,
    analyze_competitor_density,
    logger,
)

# ============================================================================
# MCP GOOGLE MAPS INTEGRATION (UPDATED API)
# ============================================================================

# Initialize MCP toolset for Google Maps (if API key is available)
google_maps_mcp = None

if os.getenv("GOOGLE_MAPS_API_KEY"):
    try:
        google_maps_mcp = MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='npx',
                    args=[
                        "-y",
                        "@modelcontextprotocol/server-google-maps"
                    ],
                    env={
                        "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY")
                    }
                ),
            ),
            # Optional: filter specific tools if needed
            # tool_filter=['maps_search_places', 'maps_get_place_details', 'maps_directions']
        )
        logger.info("✅ Google Maps MCP toolset initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Google Maps MCP initialization failed: {e}")
        logger.warning("Falling back to mock location data")
        google_maps_mcp = None
else:
    logger.warning("⚠️ GOOGLE_MAPS_API_KEY not set. Using mock data for locations.")


# ============================================================================
# TOOL DEFINITIONS FOR FACTORY FINDER
# ============================================================================

def get_city_information(city_name: str) -> dict:
    """Get comprehensive information about a Romanian city.
    
    Args:
        city_name: Name of the Romanian city (București, Cluj-Napoca, Timișoara, 
                  Iași, Constanța, or Brașov)
    
    Returns:
        Dictionary containing population, average rent, business density, 
        transport score, and available districts.
    """
    logger.info(f"🏙️ Getting info for {city_name}")
    return get_city_info(city_name)


def calculate_business_costs(
    business_type: str, 
    city_name: str, 
    size_sqm: Optional[int] = None  # ✅ Fixed: Use Optional[int] for nullable parameters
) -> dict:
    """Calculate estimated costs for opening a business in a Romanian city.
    
    Args:
        business_type: Type of business (coffee_shop, restaurant, retail_store, 
                      gym, coworking, bakery)
        city_name: Romanian city name
        size_sqm: Optional custom size in square meters (uses average if not provided)
    
    Returns:
        Dictionary with initial investment breakdown, monthly costs, staff needs,
        and financing recommendations.
    """
    logger.info(f"💰 Calculating costs for {business_type} in {city_name}")
    return estimate_business_costs(business_type, city_name, size_sqm)


def compare_city_locations(
    city1: str, 
    city2: str, 
    business_type: str = "coffee_shop"
) -> dict:
    """Compare two Romanian cities for opening a specific type of business.
    
    Args:
        city1: First city name
        city2: Second city name  
        business_type: Type of business to compare for (default: coffee_shop)
    
    Returns:
        Side-by-side comparison of population, costs, transport, business density,
        and recommendations for which location is better.
    """
    logger.info(f"⚖️ Comparing {city1} vs {city2} for {business_type}")
    return compare_locations(city1, city2, business_type)


def analyze_competitors(
    city: str, 
    business_type: str, 
    district: Optional[str] = None  # ✅ Fixed: Use Optional[str]
) -> dict:
    """Analyze competitor density and market saturation in a location.
    
    Args:
        city: Romanian city name
        business_type: Type of business to analyze
        district: Optional specific district/neighborhood to focus on
    
    Returns:
        Competitor count estimates, market saturation level, opportunity score,
        and recommendations for market entry.
    """
    logger.info(f"📊 Analyzing competitors for {business_type} in {city}")
    return analyze_competitor_density(city, business_type, district)


def get_location_accessibility(
    city: str, 
    address: Optional[str] = None  # ✅ Fixed: Use Optional[str]
) -> dict:
    """Assess accessibility and transportation options for a location.
    
    Args:
        city: Romanian city name
        address: Optional specific address to analyze
    
    Returns:
        Transport score, public transit access, parking availability,
        and accessibility recommendations.
    """
    logger.info(f"🚇 Checking accessibility in {city}")
    
    city_info = get_city_info(city)
    if "error" in city_info:
        return city_info
    
    return {
        "city": city,
        "address": address or "city center",
        "accessibility": {
            "transport_score": city_info["transport_score"],
            "public_transit": "good" if city_info["transport_score"] >= 7 else "moderate",
            "parking": "available" if city_info["transport_score"] >= 6 else "limited",
            "foot_traffic": "high" if city_info["business_density"] in ["high", "very_high"] else "moderate",
            "recommendations": [
                f"Transport score: {city_info['transport_score']}/10",
                "Consider proximity to metro/bus stations for customer access",
                "Ensure adequate parking if targeting car-driving customers"
            ]
        }
    }


def generate_location_report(
    city: str, 
    business_type: str,
    budget_eur: int = 50000
) -> dict:
    """Generate comprehensive location intelligence report for business planning.
    
    Args:
        city: Romanian city name
        business_type: Type of business
        budget_eur: Available budget in EUR
    
    Returns:
        Complete report with costs, competitors, accessibility, and recommendations
        tailored to the user's budget.
    """
    logger.info(f"📋 Generating location report for {business_type} in {city}")
    
    city_info = get_city_info(city)
    costs = estimate_business_costs(business_type, city)
    competitors = analyze_competitor_density(city, business_type)
    
    if "error" in city_info or "error" in costs:
        return {"error": "Unable to generate report due to invalid inputs"}
    
    # Budget feasibility
    required_initial = costs["initial_investment"]["total_initial_eur"]
    is_affordable = budget_eur >= required_initial
    
    # Opportunity score (1-10)
    transport_score = city_info["transport_score"]
    competition_score = competitors["competitor_analysis"]["opportunity_score"]
    affordability_score = 10 if is_affordable else 5
    overall_score = round((transport_score + competition_score + affordability_score) / 3, 1)
    
    return {
        "location_report": {
            "city": city,
            "business_type": business_type,
            "your_budget_eur": budget_eur,
            "required_investment_eur": required_initial,
            "budget_status": "✅ Sufficient" if is_affordable else "⚠️ Additional financing needed",
            "overall_opportunity_score": overall_score,
            "breakdown": {
                "costs": costs["monthly_costs"],
                "competitors": competitors["competitor_analysis"],
                "accessibility": {
                    "transport_score": transport_score,
                    "business_density": city_info["business_density"]
                }
            },
            "factory_loan_recommendation": {
                "eligible": is_affordable or (required_initial - budget_eur) <= 50000,
                "suggested_loan_amount_eur": max(0, required_initial - budget_eur),
                "total_financing": budget_eur + max(0, required_initial - budget_eur)
            },
            "key_insights": [
                f"This location has an opportunity score of {overall_score}/10",
                f"You'll need €{required_initial:,.0f} to start",
                f"Monthly costs will be around €{costs['monthly_costs']['total_monthly_eur']:,.0f}",
                f"Competition level: {competitors['competitor_analysis']['market_saturation']}",
                "Consider Factory by Raiffeisen for financing support"
            ]
        }
    }


# ============================================================================
# ROOT AGENT DEFINITION
# ============================================================================

# Tools list - includes MCP if available
tools_list = [
    get_city_information,
    calculate_business_costs,
    compare_city_locations,
    analyze_competitors,
    get_location_accessibility,
    generate_location_report,
]

# Add Google Maps MCP toolset if available
if google_maps_mcp:
    tools_list.append(google_maps_mcp)
    logger.info("✅ Including Google Maps MCP in agent tools")

# Create the root agent
root_agent = Agent(
    name="factory_finder_ai",
    model=MODEL,
    instruction=SYSTEM_INSTRUCTION,
    tools=tools_list,
)

logger.info(f"✅ Factory Finder Agent initialized with {len(tools_list)} tools")
logger.info(f"🎙️ Using model: {MODEL}")