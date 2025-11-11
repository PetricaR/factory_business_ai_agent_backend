"""
Common components for Factory Finder AI Agent
Shared utilities, constants, and base classes
"""

import asyncio
import json
import base64
import logging
import websockets
import traceback
from websockets.exceptions import ConnectionClosed

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

PROJECT_ID = "formare-ai"
LOCATION = "us-central1"
MODEL = "gemini-live-2.5-flash-preview-native-audio-09-2025"  # Native audio with enhanced quality
VOICE_NAME = "Kore"  # Romanian-friendly voice

# Audio sample rates for input/output (Native Audio requirements)
RECEIVE_SAMPLE_RATE = 24000  # Rate of audio received from Gemini (24kHz for native audio)
SEND_SAMPLE_RATE = 16000     # Rate of audio sent to Gemini (16kHz required for native audio)

# ============================================================================
# SYSTEM INSTRUCTION
# ============================================================================

SYSTEM_INSTRUCTION = """
You are an AI assistant for Factory by Raiffeisen Bank Romania, helping entrepreneurs 
find the best locations for their businesses in Romania.

Your name is Factory Finder AI, and you specialize in:
- Location intelligence and competitor analysis
- Accessibility scoring for Romanian cities
- Business demographics and market insights
- Cost estimation for different locations
- Recommendations based on business type

Supported Romanian cities:
- București (Bucharest)
- Cluj-Napoca
- Timișoara
- Iași
- Constanța
- Brașov

When helping users:
1. Ask about their business type first if not mentioned
2. Understand their priorities (foot traffic, competition, costs, etc.)
3. Use the Google Maps MCP tools to analyze locations
4. Provide actionable, data-driven recommendations
5. Speak naturally and conversationally in Romanian or English
6. Be encouraging and supportive of their entrepreneurial journey

Communication style:
- Friendly, professional, and encouraging
- Use "dumneavoastră" (formal you) initially, then adapt to user's style
- Mix Romanian business terms with English when appropriate
- Provide specific numbers and data when available
- Always end with a clear next step or question

Tools available:
- Google Maps MCP integration for location data
- Competitor density analysis
- Accessibility scoring
- Demographic insights
- Cost estimation

Remember: You're helping Romanian entrepreneurs make informed location decisions 
for their Factory loan applications.
"""

# ============================================================================
# BASE WEBSOCKET SERVER
# ============================================================================

class BaseWebSocketServer:
    """Base WebSocket server class that handles common functionality"""
    
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.active_clients = {}  # Store client websockets

    async def start(self):
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def handle_client(self, websocket):
        """Handle a new WebSocket client connection"""
        client_id = id(websocket)
        logger.info(f"New client connected: {client_id}")

        # Send ready message to client
        await websocket.send(json.dumps({"type": "ready"}))

        try:
            # Start the audio processing for this client
            await self.process_audio(websocket, client_id)
        except ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Clean up if needed
            if client_id in self.active_clients:
                del self.active_clients[client_id]

    async def process_audio(self, websocket, client_id):
        """
        Process audio from the client. This is an abstract method that
        subclasses must implement with their specific LLM integration.
        """
        raise NotImplementedError("Subclasses must implement process_audio")


# ============================================================================
# MOCK DATA FOR LOCATION INTELLIGENCE (when MCP is not available)
# ============================================================================

ROMANIAN_CITIES_DATA = {
    "București": {
        "population": 1883425,
        "avg_rent_sqm": 12.5,  # EUR/sqm
        "business_density": "very_high",
        "transport_score": 9,
        "districts": ["Sector 1", "Sector 2", "Sector 3", "Sector 4", "Sector 5", "Sector 6"]
    },
    "Cluj-Napoca": {
        "population": 286598,
        "avg_rent_sqm": 10.0,
        "business_density": "high",
        "transport_score": 8,
        "districts": ["Centru", "Mănăștur", "Mărăști", "Gheorgheni"]
    },
    "Timișoara": {
        "population": 319279,
        "avg_rent_sqm": 8.5,
        "business_density": "high",
        "transport_score": 7,
        "districts": ["Centru", "Fabric", "Elisabetin", "Circumvalațiunii"]
    },
    "Iași": {
        "population": 290422,
        "avg_rent_sqm": 7.0,
        "business_density": "medium",
        "transport_score": 6,
        "districts": ["Centru", "Nicolina", "Tătărași", "Păcurari"]
    },
    "Constanța": {
        "population": 283872,
        "avg_rent_sqm": 8.0,
        "business_density": "medium",
        "transport_score": 6,
        "districts": ["Centru", "Mamaia", "Tomis", "Palazu Mare"]
    },
    "Brașov": {
        "population": 253200,
        "avg_rent_sqm": 9.0,
        "business_density": "medium",
        "transport_score": 7,
        "districts": ["Centru", "Tractorul", "Astra", "Bartolomeu"]
    }
}

BUSINESS_TYPES_COSTS = {
    "coffee_shop": {
        "name": "Coffee Shop / Cafenea",
        "avg_size_sqm": 60,
        "setup_cost_eur": 25000,
        "monthly_costs_eur": 3500,
        "staff_needed": 2
    },
    "restaurant": {
        "name": "Restaurant",
        "avg_size_sqm": 120,
        "setup_cost_eur": 50000,
        "monthly_costs_eur": 8000,
        "staff_needed": 5
    },
    "retail_store": {
        "name": "Retail Store / Magazin",
        "avg_size_sqm": 80,
        "setup_cost_eur": 20000,
        "monthly_costs_eur": 3000,
        "staff_needed": 2
    },
    "gym": {
        "name": "Gym / Sală de fitness",
        "avg_size_sqm": 200,
        "setup_cost_eur": 40000,
        "monthly_costs_eur": 6000,
        "staff_needed": 3
    },
    "coworking": {
        "name": "Coworking Space / Spațiu coworking",
        "avg_size_sqm": 150,
        "setup_cost_eur": 30000,
        "monthly_costs_eur": 5000,
        "staff_needed": 2
    },
    "bakery": {
        "name": "Bakery / Brutărie",
        "avg_size_sqm": 70,
        "setup_cost_eur": 35000,
        "monthly_costs_eur": 4500,
        "staff_needed": 3
    }
}


# ============================================================================
# MOCK FUNCTIONS (fallback when MCP is not available)
# ============================================================================

def get_city_info(city_name: str) -> dict:
    """Get basic information about a Romanian city"""
    city = ROMANIAN_CITIES_DATA.get(city_name)
    if not city:
        return {
            "error": f"City '{city_name}' not found",
            "available_cities": list(ROMANIAN_CITIES_DATA.keys())
        }
    
    return {
        "city": city_name,
        "population": city["population"],
        "avg_rent_per_sqm_eur": city["avg_rent_sqm"],
        "business_density": city["business_density"],
        "transport_score": city["transport_score"],
        "districts": city["districts"]
    }


def estimate_business_costs(business_type: str, city_name: str, size_sqm: int = None) -> dict:
    """Estimate costs for opening a business in a specific city"""
    
    # Normalize business type
    business_key = business_type.lower().replace(" ", "_")
    if business_key not in BUSINESS_TYPES_COSTS:
        # Try to match partial
        for key in BUSINESS_TYPES_COSTS:
            if key in business_key or business_key in key:
                business_key = key
                break
        else:
            return {
                "error": f"Business type '{business_type}' not recognized",
                "available_types": list(BUSINESS_TYPES_COSTS.keys())
            }
    
    city = ROMANIAN_CITIES_DATA.get(city_name)
    if not city:
        return {
            "error": f"City '{city_name}' not found",
            "available_cities": list(ROMANIAN_CITIES_DATA.keys())
        }
    
    business = BUSINESS_TYPES_COSTS[business_key]
    
    # Use provided size or default
    actual_size = size_sqm if size_sqm else business["avg_size_sqm"]
    
    # Calculate costs
    monthly_rent = actual_size * city["avg_rent_sqm"]
    total_setup = business["setup_cost_eur"]
    monthly_operating = business["monthly_costs_eur"]
    
    return {
        "business_type": business["name"],
        "city": city_name,
        "size_sqm": actual_size,
        "initial_investment": {
            "setup_costs_eur": total_setup,
            "first_month_rent_eur": monthly_rent,
            "total_initial_eur": total_setup + monthly_rent
        },
        "monthly_costs": {
            "rent_eur": round(monthly_rent, 2),
            "operating_costs_eur": monthly_operating,
            "total_monthly_eur": round(monthly_rent + monthly_operating, 2)
        },
        "staff_needed": business["staff_needed"],
        "recommendations": [
            f"Total initial investment: €{total_setup + monthly_rent:,.0f}",
            f"Monthly break-even needs to cover: €{monthly_rent + monthly_operating:,.0f}",
            f"Consider Factory loan for: €{(total_setup + monthly_rent) * 0.8:,.0f} (80% financing)"
        ]
    }


def compare_locations(city1: str, city2: str, business_type: str = "coffee_shop") -> dict:
    """Compare two cities for opening a specific business"""
    
    info1 = get_city_info(city1)
    info2 = get_city_info(city2)
    
    if "error" in info1 or "error" in info2:
        return {
            "error": "One or both cities not found",
            "city1_status": info1,
            "city2_status": info2
        }
    
    costs1 = estimate_business_costs(business_type, city1)
    costs2 = estimate_business_costs(business_type, city2)
    
    return {
        "comparison": {
            "city1": {
                "name": city1,
                "population": info1["population"],
                "rent_per_sqm": info1["avg_rent_per_sqm_eur"],
                "monthly_total": costs1["monthly_costs"]["total_monthly_eur"],
                "transport_score": info1["transport_score"],
                "business_density": info1["business_density"]
            },
            "city2": {
                "name": city2,
                "population": info2["population"],
                "rent_per_sqm": info2["avg_rent_per_sqm_eur"],
                "monthly_total": costs2["monthly_costs"]["total_monthly_eur"],
                "transport_score": info2["transport_score"],
                "business_density": info2["business_density"]
            }
        },
        "recommendation": (
            f"{city1} has better transport ({info1['transport_score']}/10) but higher costs (€{costs1['monthly_costs']['total_monthly_eur']}/month). "
            f"{city2} is more affordable (€{costs2['monthly_costs']['total_monthly_eur']}/month) with good growth potential."
        )
    }


def analyze_competitor_density(city: str, business_type: str, district: str = None) -> dict:
    """Analyze competitor density for a business type in a city/district"""
    
    city_info = get_city_info(city)
    if "error" in city_info:
        return city_info
    
    # Mock competitor data based on city business density
    density_map = {
        "very_high": {"count": 50, "saturation": "high"},
        "high": {"count": 30, "saturation": "medium"},
        "medium": {"count": 15, "saturation": "low"}
    }
    
    density = density_map.get(city_info["business_density"], {"count": 10, "saturation": "very_low"})
    
    return {
        "city": city,
        "district": district or "city-wide",
        "business_type": business_type,
        "competitor_analysis": {
            "estimated_competitors": density["count"],
            "market_saturation": density["saturation"],
            "opportunity_score": 8 if density["saturation"] in ["low", "very_low"] else 5,
            "recommendation": (
                f"{'Good' if density['saturation'] in ['low', 'very_low'] else 'Moderate'} opportunity for {business_type}. "
                f"Approximately {density['count']} similar businesses in the area."
            )
        }
    }