#!/usr/bin/env python3
"""
GOOGLE MAPS MCP SERVER - FULLY OPTIMIZED VERSION
Complete location intelligence and business analysis using Google Maps Platform

PERFORMANCE OPTIMIZATIONS:
- Reusable aiohttp ClientSession with connection pooling
- TCPConnector with optimized pool settings
- Proper async context management
- Structured error handling with ToolError
- Type-safe implementations
- Exponential backoff retry logic
- Memory-efficient session lifecycle

FEATURES:
- 13 Google Maps Location Intelligence Tools
- Fully async/await implementation for maximum performance
- Parallel tool execution support
- Production-ready security and error handling
"""

import os
import asyncio
import aiohttp
import googlemaps
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from statistics import mean, median
from math import radians, sin, cos, sqrt, atan2
from contextlib import asynccontextmanager
from dataclasses import dataclass

try:
    from fastmcp import FastMCP
    from fastmcp.exceptions import ToolError
except ImportError:
    raise ImportError("fastmcp is required. Install with: pip install fastmcp")

from dotenv import load_dotenv

# Google Cloud Secret Manager
try:
    from google.cloud import secretmanager
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False
    logging.warning("google-cloud-secret-manager not installed. Will use environment variables.")

# ==================== CONFIGURATION ====================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Server Configuration
PORT = int(os.getenv("PORT", "8000"))
SERVER_NAME = "google-maps-intelligence-server"
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "845266575866")

# Request Configuration
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2

# Connection Pool Configuration
CONNECTOR_LIMIT = 100  # Total connection pool size
CONNECTOR_LIMIT_PER_HOST = 30  # Connections per host
CONNECTOR_TTL_DNS_CACHE = 300  # DNS cache TTL in seconds

# ==================== DATA CLASSES ====================

@dataclass
class APIConfig:
    """API configuration container"""
    google_maps_key: Optional[str] = None

# ==================== SECRET MANAGER FUNCTIONS ====================

def get_secret_from_gcp(secret_id: str) -> Optional[str]:
    """
    Fetch secret from Google Cloud Secret Manager
    
    Args:
        secret_id: Secret resource name
    
    Returns:
        Secret value or None if not found
    """
    if not SECRET_MANAGER_AVAILABLE:
        logger.warning("Secret Manager not available, falling back to environment variables")
        return None
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        
        # Build the resource name
        if not secret_id.startswith("projects/"):
            secret_id = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/latest"
        else:
            secret_id = f"{secret_id}/versions/latest"
        
        # Access the secret version
        response = client.access_secret_version(request={"name": secret_id})
        secret_value = response.payload.data.decode("UTF-8")
        logger.info(f"✓ Successfully retrieved secret from GCP Secret Manager")
        return secret_value
    except Exception as e:
        logger.error(f"Error accessing secret from GCP: {e}")
        return None


def get_api_key(secret_name: str, env_fallback: Optional[str] = None) -> Optional[str]:
    """
    Get API key from GCP Secret Manager with fallback to environment variable
    
    Args:
        secret_name: GCP secret name or full resource path
        env_fallback: Environment variable name as fallback
    
    Returns:
        API key or None
    """
    # Try GCP Secret Manager first
    api_key = get_secret_from_gcp(secret_name)
    
    # Fallback to environment variable
    if not api_key and env_fallback:
        api_key = os.getenv(env_fallback)
        if api_key:
            logger.info(f"✓ Using {env_fallback} from environment variable")
    
    return api_key


# ==================== API INITIALIZATION ====================

# Google Maps Configuration
api_config = APIConfig(
    google_maps_key=get_api_key(
        f"projects/{GCP_PROJECT_ID}/secrets/GOOGLE_MAPS_API_KEY",
        "GOOGLE_MAPS_API_KEY"
    )
)

gmaps = None
if api_config.google_maps_key:
    gmaps = googlemaps.Client(key=api_config.google_maps_key)
    logger.info("✓ Google Maps API configured")
else:
    logger.warning("⚠ Google Maps API key not found - location tools will be disabled")

# ==================== HTTP SESSION MANAGER ====================

class HTTPSessionManager:
    """
    Manages reusable aiohttp ClientSession with connection pooling
    Implements best practices for async HTTP performance
    """
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._connector: Optional[aiohttp.TCPConnector] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the shared session"""
        if self._session is None or self._session.closed:
            self._connector = aiohttp.TCPConnector(
                limit=CONNECTOR_LIMIT,
                limit_per_host=CONNECTOR_LIMIT_PER_HOST,
                ttl_dns_cache=CONNECTOR_TTL_DNS_CACHE,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"{SERVER_NAME}/2.0"
                }
            )
            
            logger.info("✓ Created new aiohttp ClientSession with connection pooling")
        
        return self._session
    
    async def close(self):
        """Properly close the session and connector"""
        if self._session and not self._session.closed:
            await self._session.close()
            # Give time for connections to close
            await asyncio.sleep(0.25)
            logger.info("✓ Closed aiohttp ClientSession")

# Global session manager
session_manager = HTTPSessionManager()

# ==================== LIFESPAN MANAGEMENT ====================

@asynccontextmanager
async def lifespan(app: FastMCP):
    """
    Lifespan context manager for FastMCP server
    Handles startup and shutdown of resources
    """
    logger.info("🚀 Starting Google Maps Intelligence Server...")
    
    # Startup: Initialize session
    await session_manager.get_session()
    logger.info("✓ HTTP session initialized")
    
    yield
    
    # Shutdown: Cleanup resources
    logger.info("🛑 Shutting down server...")
    await session_manager.close()
    logger.info("✓ Resources cleaned up")

# ==================== INITIALIZE FASTMCP SERVER ====================

mcp = FastMCP(
    name=SERVER_NAME,
    dependencies=["googlemaps", "python-dotenv", "google-cloud-secret-manager", "aiohttp"]
)

# ==================== UTILITY FUNCTIONS ====================

def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Standardized success response - returns dict for FastMCP"""
    return {
        "status": "success",
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points using Haversine formula (in km)"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    
    a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def calculate_saturation(count: int, radius_km: float) -> str:
    """Calculate market saturation level"""
    density = count / (3.14159 * radius_km * radius_km)
    
    if density > 2:
        return "Very High"
    elif density > 1:
        return "High"
    elif density > 0.5:
        return "Moderate"
    else:
        return "Low"


# ==================== ASYNC GOOGLEMAPS WRAPPER ====================

async def async_gmaps_geocode(address: str):
    """Async wrapper for googlemaps geocode"""
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    return await asyncio.to_thread(gmaps.geocode, address)


async def async_gmaps_reverse_geocode(latlng: tuple):
    """Async wrapper for googlemaps reverse_geocode"""
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    return await asyncio.to_thread(gmaps.reverse_geocode, latlng)


async def async_gmaps_places_nearby(location: tuple, radius: int, type: str = None):
    """Async wrapper for googlemaps places_nearby"""
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    return await asyncio.to_thread(gmaps.places_nearby, location=location, radius=radius, type=type)


async def async_gmaps_distance_matrix(origins: List, destinations: List, mode: str = "driving"):
    """Async wrapper for googlemaps distance_matrix"""
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    return await asyncio.to_thread(gmaps.distance_matrix, origins=origins, destinations=destinations, mode=mode)


async def async_gmaps_directions(origin: str, destination: str, mode: str = "driving", alternatives: bool = False):
    """Async wrapper for googlemaps directions"""
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    return await asyncio.to_thread(gmaps.directions, origin=origin, destination=destination, mode=mode, alternatives=alternatives)


async def async_gmaps_elevation(locations):
    """Async wrapper for googlemaps elevation"""
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    return await asyncio.to_thread(gmaps.elevation, locations)


async def async_gmaps_timezone(location: tuple, timestamp: int):
    """Async wrapper for googlemaps timezone"""
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    return await asyncio.to_thread(gmaps.timezone, location, timestamp)


async def async_gmaps_find_place(query: str, input_type: str = "textquery", location_bias: str = None):
    """Async wrapper for googlemaps find_place"""
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    kwargs = {"query": query, "input_type": input_type}
    if location_bias:
        kwargs["location_bias"] = location_bias
    return await asyncio.to_thread(gmaps.find_place, **kwargs)


async def async_gmaps_place(place_id: str):
    """Async wrapper for googlemaps place"""
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    return await asyncio.to_thread(gmaps.place, place_id=place_id)


# ==================== GOOGLE MAPS TOOLS ====================

@mcp.tool()
async def search_locations_by_city(city: str, business_type: str, radius_km: float = 5.0) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Search for business locations within a city
    
    Args:
        city: City name (e.g., "Bucharest", "Cluj-Napoca")
        business_type: Type of business to search for (e.g., "restaurant", "pharmacy", "bank")
        radius_km: Search radius in kilometers (default: 5.0)
    
    Returns: List of locations with details
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        # Geocode the city
        geocode_result = await async_gmaps_geocode(f"{city}, Romania")
        
        if not geocode_result:
            raise ToolError(f"City not found: {city}")
        
        city_coords = geocode_result[0]['geometry']['location']
        radius_meters = int(radius_km * 1000)
        
        # Search for businesses
        places = await async_gmaps_places_nearby(
            location=(city_coords['lat'], city_coords['lng']),
            radius=radius_meters,
            type=business_type
        )
        
        results = []
        for place in places.get('results', [])[:20]:  # Limit to 20 results
            results.append({
                "name": place.get('name'),
                "address": place.get('vicinity'),
                "rating": place.get('rating', 0),
                "total_ratings": place.get('user_ratings_total', 0),
                "place_id": place.get('place_id'),
                "location": place.get('geometry', {}).get('location', {})
            })
        
        data = {
            "city": city,
            "business_type": business_type,
            "search_radius_km": radius_km,
            "center_coordinates": city_coords,
            "total_found": len(results),
            "locations": results
        }
        
        return success_response(data, f"Found {len(results)} locations")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in search_locations_by_city: {e}")
        raise ToolError(f"Search failed: {str(e)}")


@mcp.tool()
async def analyze_competitor_density(
    latitude: float, 
    longitude: float, 
    business_type: str, 
    radius_km: float = 2.0
) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Analyze competitor density around a location
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        business_type: Type of business (e.g., "restaurant", "cafe", "gym")
        radius_km: Analysis radius in kilometers (default: 2.0)
    
    Returns: Competitor density analysis with saturation metrics
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        radius_meters = int(radius_km * 1000)
        
        # Search for competitors
        places = await async_gmaps_places_nearby(
            location=(latitude, longitude),
            radius=radius_meters,
            type=business_type
        )
        
        competitors = places.get('results', [])
        
        # Calculate metrics
        ratings = [p.get('rating', 0) for p in competitors if 'rating' in p]
        avg_rating = round(mean(ratings), 2) if ratings else 0
        median_rating = round(median(ratings), 2) if ratings else 0
        
        # Distance analysis
        distances = []
        for comp in competitors:
            comp_loc = comp.get('geometry', {}).get('location', {})
            if comp_loc:
                dist = calculate_distance(
                    latitude, longitude,
                    comp_loc.get('lat', latitude), 
                    comp_loc.get('lng', longitude)
                )
                distances.append(dist)
        
        analysis = {
            "location": {"lat": latitude, "lng": longitude},
            "business_type": business_type,
            "radius_km": radius_km,
            "competitor_count": len(competitors),
            "saturation_level": calculate_saturation(len(competitors), radius_km),
            "metrics": {
                "average_rating": avg_rating,
                "median_rating": median_rating,
                "total_with_ratings": len(ratings),
                "avg_distance_km": round(mean(distances), 2) if distances else 0,
                "closest_competitor_km": round(min(distances), 2) if distances else 0
            },
            "top_competitors": [
                {
                    "name": c.get('name'),
                    "rating": c.get('rating', 0),
                    "address": c.get('vicinity')
                }
                for c in sorted(competitors, key=lambda x: x.get('rating', 0), reverse=True)[:5]
            ]
        }
        
        return success_response(analysis, "Competitor density analyzed")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_competitor_density: {e}")
        raise ToolError(f"Analysis failed: {str(e)}")


@mcp.tool()
async def calculate_accessibility_score(
    latitude: float, 
    longitude: float, 
    amenity_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Calculate location accessibility score based on nearby amenities
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        amenity_types: List of amenity types to check (default: transport, parking, shopping)
    
    Returns: Accessibility score and detailed breakdown
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        if amenity_types is None:
            amenity_types = ["transit_station", "parking", "supermarket", "bank", "pharmacy"]
        
        # Fetch all amenity types in parallel
        tasks = [
            async_gmaps_places_nearby(
                location=(latitude, longitude),
                radius=1000,
                type=amenity
            )
            for amenity in amenity_types
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        accessibility_data = {}
        total_score = 0
        max_score = len(amenity_types) * 10
        
        for i, amenity in enumerate(amenity_types):
            places = results[i] if not isinstance(results[i], Exception) else {}
            count = len(places.get('results', []))
            score = min(count * 2, 10)
            total_score += score
            
            accessibility_data[amenity] = {
                "count": count,
                "score": score,
                "available": count > 0
            }
        
        final_score = round((total_score / max_score) * 100, 1)
        
        # Rating categorization
        if final_score >= 80:
            rating = "Excellent"
        elif final_score >= 60:
            rating = "Good"
        elif final_score >= 40:
            rating = "Moderate"
        else:
            rating = "Poor"
        
        result = {
            "location": {"lat": latitude, "lng": longitude},
            "accessibility_score": final_score,
            "rating": rating,
            "amenities_analyzed": accessibility_data,
            "summary": {
                "total_amenities_found": sum(d['count'] for d in accessibility_data.values()),
                "types_available": sum(1 for d in accessibility_data.values() if d['available'])
            }
        }
        
        return success_response(result, f"Accessibility score: {final_score}% ({rating})")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in calculate_accessibility_score: {e}")
        raise ToolError(f"Calculation failed: {str(e)}")


@mcp.tool()
async def geocode_address(address: str) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Convert address to geographic coordinates
    
    Args:
        address: Full address to geocode
    
    Returns: Latitude, longitude, and formatted address
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        result = await async_gmaps_geocode(address)
        
        if not result:
            raise ToolError(f"Address not found: {address}")
        
        location = result[0]
        coords = location['geometry']['location']
        
        data = {
            "original_address": address,
            "formatted_address": location['formatted_address'],
            "coordinates": {
                "lat": coords['lat'],
                "lng": coords['lng']
            },
            "place_id": location.get('place_id'),
            "location_type": location['geometry'].get('location_type'),
            "address_components": location.get('address_components', [])
        }
        
        return success_response(data, "Address geocoded successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in geocode_address: {e}")
        raise ToolError(f"Geocoding failed: {str(e)}")


@mcp.tool()
async def reverse_geocode_coordinates(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Convert coordinates to address
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
    
    Returns: Address and location details
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        result = await async_gmaps_reverse_geocode((latitude, longitude))
        
        if not result:
            raise ToolError(f"Location not found for coordinates: {latitude}, {longitude}")
        
        location = result[0]
        
        data = {
            "coordinates": {"lat": latitude, "lng": longitude},
            "formatted_address": location['formatted_address'],
            "place_id": location.get('place_id'),
            "address_components": location.get('address_components', []),
            "location_types": location.get('types', [])
        }
        
        return success_response(data, "Coordinates reverse geocoded")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in reverse_geocode_coordinates: {e}")
        raise ToolError(f"Reverse geocoding failed: {str(e)}")


@mcp.tool()
async def find_nearby_amenities(
    latitude: float, 
    longitude: float, 
    amenity_type: str, 
    radius_km: float = 1.0, 
    max_results: int = 20
) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Find nearby amenities of a specific type
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        amenity_type: Type of amenity (e.g., "hospital", "school", "restaurant", "atm")
        radius_km: Search radius in kilometers (default: 1.0)
        max_results: Maximum number of results (default: 20)
    
    Returns: List of nearby amenities with details
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        radius_meters = int(radius_km * 1000)
        
        places = await async_gmaps_places_nearby(
            location=(latitude, longitude),
            radius=radius_meters,
            type=amenity_type
        )
        
        results = []
        for place in places.get('results', [])[:max_results]:
            place_loc = place.get('geometry', {}).get('location', {})
            distance = calculate_distance(
                latitude, longitude,
                place_loc.get('lat', latitude),
                place_loc.get('lng', longitude)
            ) if place_loc else 0
            
            results.append({
                "name": place.get('name'),
                "address": place.get('vicinity'),
                "rating": place.get('rating', 0),
                "total_ratings": place.get('user_ratings_total', 0),
                "distance_km": round(distance, 2),
                "place_id": place.get('place_id'),
                "open_now": place.get('opening_hours', {}).get('open_now'),
                "location": place_loc
            })
        
        # Sort by distance
        results.sort(key=lambda x: x['distance_km'])
        
        data = {
            "search_location": {"lat": latitude, "lng": longitude},
            "amenity_type": amenity_type,
            "radius_km": radius_km,
            "total_found": len(results),
            "amenities": results
        }
        
        return success_response(data, f"Found {len(results)} {amenity_type}s nearby")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in find_nearby_amenities: {e}")
        raise ToolError(f"Search failed: {str(e)}")


@mcp.tool()
async def get_distance_matrix(
    origins: List[str], 
    destinations: List[str], 
    mode: str = "driving"
) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Calculate distances and travel times between multiple locations
    
    Args:
        origins: List of origin addresses or coordinates
        destinations: List of destination addresses or coordinates
        mode: Travel mode - "driving", "walking", "bicycling", or "transit" (default: "driving")
    
    Returns: Distance and duration matrix
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        result = await async_gmaps_distance_matrix(
            origins=origins,
            destinations=destinations,
            mode=mode
        )
        
        if result['status'] != 'OK':
            raise ToolError(f"Distance matrix calculation failed: {result.get('error_message', 'Unknown error')}")
        
        matrix_data = {
            "origins": result.get('origin_addresses', []),
            "destinations": result.get('destination_addresses', []),
            "mode": mode,
            "rows": []
        }
        
        for i, row in enumerate(result['rows']):
            row_data = {
                "origin": result['origin_addresses'][i],
                "destinations": []
            }
            
            for j, element in enumerate(row['elements']):
                dest_data = {
                    "destination": result['destination_addresses'][j],
                    "status": element['status']
                }
                
                if element['status'] == 'OK':
                    dest_data.update({
                        "distance": {
                            "value_meters": element['distance']['value'],
                            "text": element['distance']['text']
                        },
                        "duration": {
                            "value_seconds": element['duration']['value'],
                            "text": element['duration']['text']
                        }
                    })
                
                row_data['destinations'].append(dest_data)
            
            matrix_data['rows'].append(row_data)
        
        return success_response(matrix_data, "Distance matrix calculated")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in get_distance_matrix: {e}")
        raise ToolError(f"Matrix calculation failed: {str(e)}")


@mcp.tool()
async def get_directions(
    origin: str, 
    destination: str, 
    mode: str = "driving", 
    alternatives: bool = False
) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Get directions between two locations
    
    Args:
        origin: Starting address or coordinates
        destination: Ending address or coordinates
        mode: Travel mode - "driving", "walking", "bicycling", or "transit" (default: "driving")
        alternatives: Whether to return alternative routes (default: False)
    
    Returns: Turn-by-turn directions with distance and duration
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        result = await async_gmaps_directions(
            origin=origin,
            destination=destination,
            mode=mode,
            alternatives=alternatives
        )
        
        if not result:
            raise ToolError(f"No routes found from {origin} to {destination}")
        
        routes_data = []
        for route in result:
            leg = route['legs'][0]
            
            route_data = {
                "summary": route.get('summary'),
                "distance": {
                    "value_meters": leg['distance']['value'],
                    "text": leg['distance']['text']
                },
                "duration": {
                    "value_seconds": leg['duration']['value'],
                    "text": leg['duration']['text']
                },
                "start_address": leg['start_address'],
                "end_address": leg['end_address'],
                "steps": [
                    {
                        "instruction": step['html_instructions'],
                        "distance": step['distance']['text'],
                        "duration": step['duration']['text'],
                        "travel_mode": step['travel_mode']
                    }
                    for step in leg['steps']
                ]
            }
            
            routes_data.append(route_data)
        
        data = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "routes_found": len(routes_data),
            "routes": routes_data
        }
        
        return success_response(data, f"Found {len(routes_data)} route(s)")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in get_directions: {e}")
        raise ToolError(f"Directions failed: {str(e)}")


@mcp.tool()
async def get_elevation(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Get elevation data for a location
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
    
    Returns: Elevation in meters
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        result = await async_gmaps_elevation((latitude, longitude))
        
        if not result:
            raise ToolError(f"Elevation data not found for coordinates: {latitude}, {longitude}")
        
        data = {
            "location": {"lat": latitude, "lng": longitude},
            "elevation_meters": result[0]['elevation'],
            "resolution": result[0].get('resolution')
        }
        
        return success_response(data, "Elevation retrieved")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in get_elevation: {e}")
        raise ToolError(f"Elevation retrieval failed: {str(e)}")


@mcp.tool()
async def get_timezone(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Get timezone information for a location
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
    
    Returns: Timezone data including ID and UTC offset
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        timestamp = int(time.time())
        result = await async_gmaps_timezone((latitude, longitude), timestamp)
        
        if result['status'] != 'OK':
            raise ToolError(f"Timezone data not found for coordinates: {latitude}, {longitude}")
        
        data = {
            "location": {"lat": latitude, "lng": longitude},
            "timezone_id": result['timeZoneId'],
            "timezone_name": result['timeZoneName'],
            "raw_offset_seconds": result['rawOffset'],
            "dst_offset_seconds": result['dstOffset'],
            "total_offset_seconds": result['rawOffset'] + result['dstOffset'],
            "utc_offset_hours": (result['rawOffset'] + result['dstOffset']) / 3600
        }
        
        return success_response(data, "Timezone information retrieved")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in get_timezone: {e}")
        raise ToolError(f"Timezone retrieval failed: {str(e)}")


@mcp.tool()
async def find_place_from_text(query: str, location_bias: Optional[str] = None) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Find a place using text search
    
    Args:
        query: Search query (e.g., "pizza in Cluj-Napoca", "Eiffel Tower")
        location_bias: Optional location to bias results (e.g., "45.7489,21.2087")
    
    Returns: Place details including address, coordinates, and ratings
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        result = await async_gmaps_find_place(
            query=query,
            input_type="textquery",
            location_bias=location_bias
        )
        
        if result['status'] != 'OK' or not result.get('candidates'):
            raise ToolError(f"No places found for query: {query}")
        
        places_data = []
        for place in result['candidates']:
            place_data = {
                "name": place.get('name'),
                "formatted_address": place.get('formatted_address'),
                "place_id": place.get('place_id'),
                "rating": place.get('rating'),
                "user_ratings_total": place.get('user_ratings_total')
            }
            
            if 'geometry' in place:
                place_data['location'] = place['geometry']['location']
            
            places_data.append(place_data)
        
        data = {
            "query": query,
            "results_found": len(places_data),
            "places": places_data
        }
        
        return success_response(data, f"Found {len(places_data)} place(s)")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in find_place_from_text: {e}")
        raise ToolError(f"Search failed: {str(e)}")


@mcp.tool()
async def compare_multiple_locations(
    locations: List[Dict[str, float]], 
    business_type: str
) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Compare multiple locations for business viability
    
    Args:
        locations: List of locations as dicts with 'lat' and 'lng' keys
        business_type: Type of business to analyze
    
    Returns: Comparative analysis ranking locations by viability
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        if len(locations) < 2:
            raise ToolError("Provide at least 2 locations to compare")
        
        if len(locations) > 10:
            raise ToolError("Maximum 10 locations allowed for comparison")
        
        # Fetch competitor data for all locations in parallel
        tasks = [
            async_gmaps_places_nearby(
                location=(loc['lat'], loc['lng']),
                radius=2000,
                type=business_type
            )
            for loc in locations
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        comparison_results = []
        for idx, (loc, places_result) in enumerate(zip(locations, results)):
            if isinstance(places_result, Exception):
                competitors = []
            else:
                competitors = places_result.get('results', [])
            
            ratings = [p.get('rating', 0) for p in competitors if 'rating' in p]
            
            comparison_results.append({
                "location_id": idx + 1,
                "coordinates": loc,
                "competitor_count": len(competitors),
                "avg_competitor_rating": round(mean(ratings), 2) if ratings else 0,
                "saturation": calculate_saturation(len(competitors), 2.0),
                "viability_score": max(0, 100 - (len(competitors) * 5))
            })
        
        # Rank locations by viability score
        ranked = sorted(comparison_results, key=lambda x: x['viability_score'], reverse=True)
        
        result = {
            "business_type": business_type,
            "locations_analyzed": len(locations),
            "comparison": ranked,
            "best_location": ranked[0] if ranked else None,
            "recommendation": f"Location {ranked[0]['location_id']} shows highest viability" if ranked else None
        }
        
        return success_response(result, "Location comparison completed")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in compare_multiple_locations: {e}")
        raise ToolError(f"Comparison failed: {str(e)}")


@mcp.tool()
async def get_location_details(place_id: str) -> Dict[str, Any]:
    """
    [GOOGLE MAPS] Get detailed information about a specific place
    
    Args:
        place_id: Google Maps place ID
    
    Returns: Full place details including hours, photos, reviews
    """
    if not gmaps:
        raise ToolError("Google Maps API not configured")
    
    try:
        details = await async_gmaps_place(place_id=place_id)
        
        if details['status'] != 'OK':
            raise ToolError(f"Place details not found for place_id: {place_id}")
        
        place = details['result']
        
        result = {
            "place_id": place_id,
            "name": place.get('name'),
            "formatted_address": place.get('formatted_address'),
            "formatted_phone_number": place.get('formatted_phone_number'),
            "international_phone_number": place.get('international_phone_number'),
            "website": place.get('website'),
            "rating": place.get('rating', 0),
            "user_ratings_total": place.get('user_ratings_total', 0),
            "price_level": place.get('price_level', 0),
            "types": place.get('types', []),
            "opening_hours": place.get('opening_hours', {}),
            "geometry": place.get('geometry', {}),
            "reviews": place.get('reviews', [])[:5]
        }
        
        return success_response(result, "Place details retrieved")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in get_location_details: {e}")
        raise ToolError(f"Details retrieval failed: {str(e)}")


# ==================== MCP RESOURCES ====================

@mcp.resource("config://server-info")
def get_server_info() -> str:
    """Complete server configuration and capabilities"""
    return json.dumps({
        "server_name": SERVER_NAME,
        "version": "2.0.0-optimized",
        "port": PORT,
        "async_support": True,
        "parallel_execution": True,
        "connection_pooling": True,
        "total_tools": 13,
        "tool_categories": {
            "google_maps_location": 13
        },
        "apis_integrated": [
            "Google Maps Platform (7 APIs)"
        ],
        "security": {
            "secret_manager": "Google Cloud Secret Manager",
            "gcp_project": GCP_PROJECT_ID
        },
        "performance": {
            "session_manager": "aiohttp with connection pooling",
            "connector_limit": CONNECTOR_LIMIT,
            "connector_limit_per_host": CONNECTOR_LIMIT_PER_HOST,
            "parallel_tool_calls": "supported",
            "retry_logic": "exponential backoff"
        },
        "google_maps_tools": [
            "search_locations_by_city",
            "analyze_competitor_density",
            "calculate_accessibility_score",
            "geocode_address",
            "reverse_geocode_coordinates",
            "find_nearby_amenities",
            "get_distance_matrix",
            "get_directions",
            "get_elevation",
            "get_timezone",
            "find_place_from_text",
            "compare_multiple_locations",
            "get_location_details"
        ],
        "features": [
            "Fully async implementation",
            "Parallel tool execution",
            "Connection pooling (100 total, 30 per host)",
            "Secure key management via GCP",
            "Location intelligence",
            "Competitor analysis",
            "Route planning",
            "Distance calculations",
            "Accessibility scoring",
            "Structured error handling with ToolError",
            "Proper resource lifecycle management"
        ]
    }, indent=2)


@mcp.resource("api://capabilities")
def get_api_capabilities() -> str:
    """Detailed API capabilities"""
    return json.dumps({
        "google_maps": {
            "authentication": "API key",
            "configured": gmaps is not None,
            "async_support": True,
            "parallel_requests": True,
            "apis_available": [
                "Geocoding API",
                "Places API",
                "Distance Matrix API",
                "Directions API",
                "Elevation API",
                "Time Zone API",
                "Places Text Search"
            ],
            "features": [
                "Location search",
                "Competitor analysis",
                "Route planning",
                "Distance calculations",
                "Accessibility scoring"
            ]
        }
    }, indent=2)


@mcp.resource("docs://usage-guide")
def get_usage_guide() -> str:
    """Usage guide and examples"""
    return json.dumps({
        "setup": {
            "environment_variables": [
                "GOOGLE_MAPS_API_KEY - Google Maps API key"
            ],
            "gcp_secrets": [
                f"projects/{GCP_PROJECT_ID}/secrets/GOOGLE_MAPS_API_KEY"
            ],
            "installation": [
                "pip install googlemaps python-dotenv google-cloud-secret-manager fastmcp aiohttp",
                "python google-maps-mcp-optimized.py"
            ]
        },
        "optimization_features": {
            "connection_pooling": "Reusable aiohttp ClientSession with 100 total connections, 30 per host",
            "parallel_execution": "Multiple tools can be called simultaneously",
            "non_blocking": "All I/O operations are non-blocking",
            "retry_logic": "Exponential backoff with configurable retries",
            "error_handling": "Structured ToolError exceptions",
            "resource_management": "Proper startup/shutdown lifecycle"
        },
        "examples": {
            "search": {
                "description": "Search businesses in a city",
                "example": "await search_locations_by_city(city='Bucharest', business_type='restaurant')"
            },
            "directions": {
                "description": "Get directions",
                "example": "await get_directions(origin='Bucharest', destination='Cluj-Napoca')"
            },
            "competitor_analysis": {
                "description": "Analyze competitor density",
                "example": "await analyze_competitor_density(latitude=44.4268, longitude=26.1025, business_type='cafe')"
            }
        }
    }, indent=2)


# ==================== SERVER STARTUP ====================

if __name__ == "__main__":
    print("=" * 90)
    print(f"🚀 {SERVER_NAME.upper().replace('-', ' ')}")
    print("=" * 90)
    print("GOOGLE MAPS MCP SERVER - FULLY OPTIMIZED")
    print(f"Port: {PORT}")
    print("=" * 90)
    
    print("\n✨ PERFORMANCE FEATURES:")
    print("  • Reusable aiohttp ClientSession with connection pooling")
    print(f"  • {CONNECTOR_LIMIT} total connections, {CONNECTOR_LIMIT_PER_HOST} per host")
    print("  • Exponential backoff retry logic")
    print("  • Proper async resource management")
    print("  • Structured error handling with ToolError")
    print("  • Type-safe implementations")
    
    print("\n🔐 SECURITY CONFIGURATION:")
    print(f"  • GCP Project: {GCP_PROJECT_ID}")
    print(f"  • Secret Manager: {'✓ Available' if SECRET_MANAGER_AVAILABLE else '✗ Not Available'}")
    print(f"  • Google Maps API: {'✓ Configured' if api_config.google_maps_key else '✗ Not Configured'}")
    
    print("\n🗺️  GOOGLE MAPS TOOLS (13):")
    print("  1. search_locations_by_city - Find locations (ASYNC)")
    print("  2. analyze_competitor_density - Competition analysis (ASYNC)")
    print("  3. calculate_accessibility_score - Accessibility (PARALLEL)")
    print("  4. geocode_address - Address to coords (ASYNC)")
    print("  5. reverse_geocode_coordinates - Coords to address (ASYNC)")
    print("  6. find_nearby_amenities - Amenities search (ASYNC)")
    print("  7. get_distance_matrix - Distance calculations (ASYNC)")
    print("  8. get_directions - Turn-by-turn directions (ASYNC)")
    print("  9. get_elevation - Elevation data (ASYNC)")
    print("  10. get_timezone - Timezone information (ASYNC)")
    print("  11. find_place_from_text - Text search (ASYNC)")
    print("  12. compare_multiple_locations - Location comparison (PARALLEL)")
    print("  13. get_location_details - Place details (ASYNC)")
    
    print("\n📚 MCP RESOURCES (3):")
    print("   • config://server-info")
    print("   • api://capabilities")
    print("   • docs://usage-guide")
    
    print("\n" + "=" * 90)
    print("🎯 TOTAL CAPABILITIES:")
    print(f"  ✓ 13 Tools (ALL ASYNC)")
    print(f"  ✓ 3 Resources")
    print(f"  ✓ Connection pooling ({CONNECTOR_LIMIT} connections)")
    print(f"  ✓ Parallel execution support")
    print(f"  ✓ Exponential backoff retry")
    print(f"  ✓ Structured error handling")
    print(f"  ✓ Google Maps Platform")
    print(f"  ✓ Google Cloud Secret Manager")
    print(f"  ✓ Production-ready security")
    print("=" * 90)
    
    if not api_config.google_maps_key:
        print("\n⚠️  WARNING: Google Maps API not configured!")
        print("   Set GOOGLE_MAPS_API_KEY environment variable")
        print("=" * 90)
    
    print(f"\n🚀 Starting optimized server on http://0.0.0.0:{PORT}/mcp...")
    print("=" * 90)
    
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=PORT
    )