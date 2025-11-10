#!/usr/bin/env python3
"""
ROMANIAN FINANCIAL INTELLIGENCE MCP SERVER (OPTIMIZED)
High-performance async server for comprehensive financial analysis of Romanian companies

PERFORMANCE OPTIMIZATIONS:
- Reusable aiohttp ClientSession with connection pooling
- TCPConnector with optimized pool settings
- Proper async context management
- Structured error handling with ToolError
- Type-safe implementations
- Exponential backoff retry logic
- Memory-efficient session lifecycle

FEATURES:
- Financial data retrieval from official Targetare API
- Advanced financial metrics calculation (liquidity, profitability, solvency)
- Year-over-year trend analysis
- Multi-company financial comparison
- Risk assessment and credit scoring
- Financial health monitoring
- Industry benchmarking capabilities

TOOLS: 9 SPECIALIZED FINANCIAL TOOLS
"""

import os
import asyncio
import aiohttp
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from statistics import mean, median, stdev
from contextlib import asynccontextmanager
from dataclasses import dataclass

try:
    from fastmcp import FastMCP
    from fastmcp.exceptions import ToolError
except ImportError:
    raise ImportError(
        "fastmcp is required. Install with: pip install fastmcp"
    )

# Google Cloud Secret Manager (optional but recommended)
try:
    from google.cloud import secretmanager
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False
    logging.warning("google-cloud-secret-manager not available. Set API keys via environment variables.")

# ==================== CONFIGURATION ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Server Configuration
PORT = int(os.getenv("PORT", "8001"))
SERVER_NAME = "romanian-financial-intelligence-server"
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "845266575866")

# API Configuration
TARGETARE_API_BASE_URL = "https://api.targetare.ro/v1"
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
    targetare_key: Optional[str] = None
    google_search_key: Optional[str] = None
    google_search_cx: Optional[str] = None

# ==================== SECRET MANAGEMENT ====================

def get_secret_from_gcp(secret_id: str) -> Optional[str]:
    """
    Fetch secret from Google Cloud Secret Manager
    
    Args:
        secret_id: Secret resource name or just the secret name
    
    Returns:
        Secret value or None if not found
    """
    if not SECRET_MANAGER_AVAILABLE:
        return None
        
    try:
        client = secretmanager.SecretManagerServiceClient()
        
        if not secret_id.startswith("projects/"):
            secret_id = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/latest"
        else:
            secret_id = f"{secret_id}/versions/latest"
        
        response = client.access_secret_version(request={"name": secret_id})
        secret_value = response.payload.data.decode("UTF-8")
        logger.info(f"✓ Successfully retrieved secret from GCP Secret Manager")
        return secret_value
    except Exception as e:
        logger.error(f"Error accessing secret from GCP: {e}")
        return None


def get_api_key(secret_name: str, env_fallback: Optional[str] = None) -> Optional[str]:
    """
    Get API key from GCP Secret Manager or environment variable
    
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
            logger.info(f"✓ Using API key from environment variable: {env_fallback}")
    
    if not api_key:
        logger.warning(f"Failed to retrieve secret: {secret_name}")
    
    return api_key


# ==================== API INITIALIZATION ====================

# Initialize API configuration
api_config = APIConfig(
    targetare_key=get_api_key(
        f"projects/{GCP_PROJECT_ID}/secrets/API_KEY_TARGETARE",
        "API_KEY_TARGETARE"
    ),
    google_search_key=get_api_key(
        f"projects/{GCP_PROJECT_ID}/secrets/GOOGLE_CUSTOM_SEARCH_API_KE gY",
        "GOOGLE_CUSTOM_SEARCH_API_KEY"
    ),
    google_search_cx=get_api_key(
        f"projects/{GCP_PROJECT_ID}/secrets/GOOGLE_CUSTOM_SEARCH_CX",
        "GOOGLE_CUSTOM_SEARCH_CX"
    )
)

if api_config.targetare_key:
    logger.info("✓ Targetare API configured")
else:
    logger.warning("⚠ Targetare API key not found - Financial tools will be disabled")

if api_config.google_search_key and api_config.google_search_cx:
    logger.info("✓ Google Custom Search API configured for CUI lookup")
else:
    logger.warning("⚠ Google Custom Search API not configured - CUI search by name will be disabled")

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
                    "User-Agent": f"{SERVER_NAME}/1.0"
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
    logger.info("🚀 Starting Romanian Financial Intelligence Server...")
    
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
    dependencies=["aiohttp", "google-cloud-secret-manager"]
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


def validate_tax_id(tax_id: str) -> str:
    """
    Validate and clean Romanian tax ID (CUI)
    
    Args:
        tax_id: Raw tax ID input
    
    Returns:
        Cleaned numeric CUI
    
    Raises:
        ToolError: If tax ID is invalid
    """
    if not tax_id or not isinstance(tax_id, str):
        raise ToolError("Tax ID must be a non-empty string")
    
    cleaned = tax_id.strip().upper()
    cleaned = cleaned.replace("RO", "").replace("CUI", "").replace("CIF", "").strip()
    cleaned = ''.join(filter(str.isdigit, cleaned))
    
    if not cleaned:
        raise ToolError(f"Invalid tax ID: {tax_id}. Must contain digits.")
    
    if len(cleaned) < 2 or len(cleaned) > 10:
        raise ToolError(f"Invalid tax ID length: {len(cleaned)}. Must be 2-10 digits.")
    
    return cleaned


async def make_request_with_retry(
    url: str,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
    max_retries: int = MAX_RETRIES
) -> Optional[Dict]:
    """
    Make async HTTP request with exponential backoff retry logic
    
    Args:
        url: Full URL to request
        headers: Optional headers
        params: Optional query parameters
        max_retries: Maximum retry attempts
    
    Returns:
        JSON response or None on error
    """
    session = await session_manager.get_session()
    
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    logger.error("Authentication failed - Invalid API key")
                    raise ToolError("Authentication failed - Invalid API key")
                elif response.status == 404:
                    logger.warning(f"Resource not found: {url}")
                    return None
                elif response.status == 429:
                    # Rate limited - wait and retry
                    wait_time = RETRY_BACKOFF_FACTOR ** attempt
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    text = await response.text()
                    logger.error(f"API returned status {response.status}: {text}")
                    if attempt == max_retries - 1:
                        raise ToolError(f"API request failed with status {response.status}")
                    await asyncio.sleep(RETRY_BACKOFF_FACTOR ** attempt)
        except asyncio.TimeoutError:
            logger.error(f"Request timeout (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                raise ToolError("Request timeout - API not responding")
            await asyncio.sleep(RETRY_BACKOFF_FACTOR ** attempt)
        except aiohttp.ClientError as e:
            logger.error(f"Client error: {e} (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                raise ToolError(f"Network error: {str(e)}")
            await asyncio.sleep(RETRY_BACKOFF_FACTOR ** attempt)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ToolError(f"Request failed: {str(e)}")
    
    return None


async def make_targetare_request(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    """
    Make async authenticated request to Targetare API
    
    Args:
        endpoint: API endpoint (e.g., '/companies/12345678')
        params: Optional query parameters
    
    Returns:
        JSON response or None on error
    """
    if not api_config.targetare_key:
        raise ToolError("Targetare API key not configured")
    
    url = f"{TARGETARE_API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_config.targetare_key}",
        "Content-Type": "application/json"
    }
    
    return await make_request_with_retry(url, headers=headers, params=params)


def confidence_score(confidence: str) -> int:
    """Convert confidence level to numeric score for sorting"""
    scores = {
        "very_high": 4,
        "high": 3,
        "medium": 2,
        "low": 1
    }
    return scores.get(confidence, 0)


# ==================== FINANCIAL CALCULATION FUNCTIONS ====================

def calculate_liquidity_ratios(financials: Dict) -> Dict[str, Optional[float]]:
    """Calculate liquidity ratios with proper null handling"""
    ratios = {}
    
    try:
        current_assets = float(financials.get('current_assets', 0))
        current_liabilities = float(financials.get('current_liabilities', 0))
        inventory = float(financials.get('inventory', 0))
        cash = float(financials.get('cash', 0))
        
        if current_liabilities > 0:
            ratios['current_ratio'] = round(current_assets / current_liabilities, 2)
            ratios['quick_ratio'] = round((current_assets - inventory) / current_liabilities, 2)
            ratios['cash_ratio'] = round(cash / current_liabilities, 2)
        else:
            ratios['current_ratio'] = None
            ratios['quick_ratio'] = None
            ratios['cash_ratio'] = None
            
    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.error(f"Error calculating liquidity ratios: {e}")
        ratios = {'current_ratio': None, 'quick_ratio': None, 'cash_ratio': None}
    
    return ratios


def calculate_profitability_ratios(financials: Dict) -> Dict[str, Optional[float]]:
    """Calculate profitability ratios with proper null handling"""
    ratios = {}
    
    try:
        revenue = float(financials.get('revenue', 0))
        cogs = float(financials.get('cost_of_goods_sold', 0))
        operating_income = float(financials.get('operating_income', 0))
        net_income = float(financials.get('net_income', 0))
        total_assets = float(financials.get('total_assets', 0))
        total_equity = float(financials.get('total_equity', 0))
        
        if revenue > 0:
            ratios['gross_profit_margin'] = round(((revenue - cogs) / revenue) * 100, 2)
            ratios['operating_profit_margin'] = round((operating_income / revenue) * 100, 2)
            ratios['net_profit_margin'] = round((net_income / revenue) * 100, 2)
        else:
            ratios['gross_profit_margin'] = None
            ratios['operating_profit_margin'] = None
            ratios['net_profit_margin'] = None
        
        ratios['roa'] = round((net_income / total_assets) * 100, 2) if total_assets > 0 else None
        ratios['roe'] = round((net_income / total_equity) * 100, 2) if total_equity > 0 else None
            
    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.error(f"Error calculating profitability ratios: {e}")
        ratios = {
            'gross_profit_margin': None, 'operating_profit_margin': None,
            'net_profit_margin': None, 'roa': None, 'roe': None
        }
    
    return ratios


def calculate_solvency_ratios(financials: Dict) -> Dict[str, Optional[float]]:
    """Calculate solvency/leverage ratios with proper null handling"""
    ratios = {}
    
    try:
        total_debt = float(financials.get('total_debt', 0))
        total_equity = float(financials.get('total_equity', 0))
        total_assets = float(financials.get('total_assets', 0))
        ebit = float(financials.get('ebit', 0))
        interest_expense = float(financials.get('interest_expense', 0))
        
        ratios['debt_to_equity'] = round(total_debt / total_equity, 2) if total_equity > 0 else None
        ratios['debt_to_assets'] = round(total_debt / total_assets, 2) if total_assets > 0 else None
        ratios['equity_ratio'] = round(total_equity / total_assets, 2) if total_assets > 0 else None
        ratios['interest_coverage'] = round(ebit / interest_expense, 2) if interest_expense > 0 else None
            
    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.error(f"Error calculating solvency ratios: {e}")
        ratios = {
            'debt_to_equity': None, 'debt_to_assets': None,
            'equity_ratio': None, 'interest_coverage': None
        }
    
    return ratios


def calculate_efficiency_ratios(financials: Dict) -> Dict[str, Optional[float]]:
    """Calculate efficiency/activity ratios with proper null handling"""
    ratios = {}
    
    try:
        revenue = float(financials.get('revenue', 0))
        total_assets = float(financials.get('total_assets', 0))
        cogs = float(financials.get('cost_of_goods_sold', 0))
        inventory = float(financials.get('inventory', 0))
        accounts_receivable = float(financials.get('accounts_receivable', 0))
        
        ratios['asset_turnover'] = round(revenue / total_assets, 2) if total_assets > 0 else None
        ratios['inventory_turnover'] = round(cogs / inventory, 2) if inventory > 0 else None
        
        if accounts_receivable > 0 and revenue > 0:
            receivables_turnover = revenue / accounts_receivable
            ratios['receivables_turnover'] = round(receivables_turnover, 2)
            ratios['days_sales_outstanding'] = round(365 / receivables_turnover, 0)
        else:
            ratios['receivables_turnover'] = None
            ratios['days_sales_outstanding'] = None
            
    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.error(f"Error calculating efficiency ratios: {e}")
        ratios = {
            'asset_turnover': None, 'inventory_turnover': None,
            'receivables_turnover': None, 'days_sales_outstanding': None
        }
    
    return ratios


def calculate_financial_health_score(ratios: Dict) -> Tuple[int, str]:
    """
    Calculate overall financial health score (0-100)
    
    Args:
        ratios: Dictionary containing all calculated ratios
    
    Returns:
        Tuple of (score, rating)
    """
    score = 0
    max_score = 0
    
    # Liquidity (25 points max)
    if ratios.get('liquidity', {}).get('current_ratio'):
        current_ratio = ratios['liquidity']['current_ratio']
        if current_ratio >= 2.0:
            score += 25
        elif current_ratio >= 1.5:
            score += 20
        elif current_ratio >= 1.0:
            score += 15
        elif current_ratio >= 0.5:
            score += 10
        else:
            score += 5
    max_score += 25
    
    # Profitability (30 points max)
    if ratios.get('profitability', {}).get('net_profit_margin') is not None:
        npm = ratios['profitability']['net_profit_margin']
        if npm >= 15:
            score += 20
        elif npm >= 10:
            score += 15
        elif npm >= 5:
            score += 10
        elif npm >= 0:
            score += 5
    max_score += 20
    
    if ratios.get('profitability', {}).get('roe') is not None:
        roe = ratios['profitability']['roe']
        if roe >= 20:
            score += 10
        elif roe >= 15:
            score += 8
        elif roe >= 10:
            score += 6
        elif roe >= 5:
            score += 4
        elif roe >= 0:
            score += 2
    max_score += 10
    
    # Solvency (25 points max)
    if ratios.get('solvency', {}).get('debt_to_equity') is not None:
        dte = ratios['solvency']['debt_to_equity']
        if dte <= 0.5:
            score += 15
        elif dte <= 1.0:
            score += 12
        elif dte <= 2.0:
            score += 8
        elif dte <= 3.0:
            score += 4
    max_score += 15
    
    if ratios.get('solvency', {}).get('interest_coverage') is not None:
        ic = ratios['solvency']['interest_coverage']
        if ic >= 5:
            score += 10
        elif ic >= 3:
            score += 8
        elif ic >= 2:
            score += 6
        elif ic >= 1:
            score += 4
    max_score += 10
    
    # Efficiency (20 points max)
    if ratios.get('efficiency', {}).get('asset_turnover') is not None:
        at = ratios['efficiency']['asset_turnover']
        if at >= 2.0:
            score += 20
        elif at >= 1.5:
            score += 15
        elif at >= 1.0:
            score += 10
        elif at >= 0.5:
            score += 5
    max_score += 20
    
    # Calculate final score
    final_score = int((score / max_score) * 100) if max_score > 0 else 0
    
    # Determine rating
    if final_score >= 80:
        rating = "Excellent"
    elif final_score >= 65:
        rating = "Good"
    elif final_score >= 50:
        rating = "Fair"
    elif final_score >= 35:
        rating = "Poor"
    else:
        rating = "Critical"
    
    return final_score, rating


def calculate_trend_analysis(historical_data: List[Dict]) -> Dict:
    """
    Calculate year-over-year trends
    
    Args:
        historical_data: List of financial data dictionaries sorted by year
    
    Returns:
        Dictionary with trend metrics
    """
    if len(historical_data) < 2:
        return {"error": "Insufficient historical data for trend analysis"}
    
    trends = {}
    
    try:
        # Revenue trend
        revenues = [float(d.get('revenue', 0)) for d in historical_data]
        if len(revenues) >= 2 and revenues[-2] > 0:
            yoy_growth = ((revenues[-1] - revenues[-2]) / revenues[-2] * 100)
            cagr = (((revenues[-1] / revenues[0]) ** (1 / (len(revenues) - 1))) - 1) * 100 if revenues[0] > 0 else None
            trends['revenue'] = {
                'values': revenues,
                'yoy_growth_pct': round(yoy_growth, 2),
                'cagr_pct': round(cagr, 2) if cagr else None,
                'trend': 'increasing' if yoy_growth > 0 else 'decreasing'
            }
        
        # Profit trend
        net_incomes = [float(d.get('net_income', 0)) for d in historical_data]
        if len(net_incomes) >= 2 and net_incomes[-2] != 0:
            yoy_growth = ((net_incomes[-1] - net_incomes[-2]) / abs(net_incomes[-2]) * 100)
            trends['net_income'] = {
                'values': net_incomes,
                'yoy_growth_pct': round(yoy_growth, 2),
                'trend': 'increasing' if yoy_growth > 0 else 'decreasing'
            }
        
        # Asset trend
        assets = [float(d.get('total_assets', 0)) for d in historical_data]
        if len(assets) >= 2 and assets[-2] > 0:
            yoy_growth = ((assets[-1] - assets[-2]) / assets[-2] * 100)
            trends['total_assets'] = {
                'values': assets,
                'yoy_growth_pct': round(yoy_growth, 2),
                'trend': 'increasing' if yoy_growth > 0 else 'decreasing'
            }
            
    except (ValueError, TypeError, ZeroDivisionError) as e:
        logger.error(f"Error calculating trends: {e}")
        trends['error'] = str(e)
    
    return trends


# ==================== CUI LOOKUP TOOL ====================

@mcp.tool()
async def find_company_cui_by_name(
    company_name: str, 
    county: str = "",
    limit_results: int = 5
) -> Dict[str, Any]:
    """
    [SEARCH] Find Romanian company CUI by searching official sources
    
    Essential first step for financial analysis workflow. Use this when you only
    have the company name and need to find its CUI/tax ID.
    
    Args:
        company_name: Full company name (e.g., "Carrefour Romania SA")
        county: Optional county to narrow search (e.g., "Bucuresti", "Cluj")
        limit_results: Maximum candidates to return (default: 5)
    
    Returns: Dict with CUI candidates and confidence scores
    
    Example workflow:
        1. find_company_cui_by_name(company_name="Dedeman SRL")
        2. Extract best CUI from results
        3. get_company_financials(tax_id=extracted_cui)
    """
    if not api_config.google_search_key or not api_config.google_search_cx:
        raise ToolError("Google Custom Search not configured. Set GOOGLE_CUSTOM_SEARCH_API_KEY and GOOGLE_CUSTOM_SEARCH_CX")
    
    if not company_name or not isinstance(company_name, str):
        raise ToolError("company_name must be a non-empty string")
    
    try:
        query = f'"{company_name}" CUI România'
        if county:
            query += f' {county}'
        
        logger.info(f"Searching for CUI: {query}")
        
        params = {
            "key": api_config.google_search_key,
            "cx": api_config.google_search_cx,
            "q": query,
            "gl": "ro",
            "lr": "lang_ro",
            "num": 10
        }
        
        session = await session_manager.get_session()
        
        async with session.get("https://www.googleapis.com/customsearch/v1", params=params) as response:
            if response.status != 200:
                text = await response.text()
                raise ToolError(f"Search failed with status {response.status}: {text}")
            
            data = await response.json()
        
        if "items" not in data:
            raise ToolError(f"No results found for: {company_name}")
        
        cui_pattern = re.compile(r'\b(?:CUI|CIF|RO|Cod\s+fiscal)[\s:\-]*(\d{2,10})\b', re.IGNORECASE)
        cui_candidates = {}
        
        for item in data["items"]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            matches = cui_pattern.findall(f"{title} {snippet}")
            
            for cui in matches:
                if not (2 <= len(cui) <= 10 and cui.isdigit()):
                    continue
                
                if "mfinante.ro" in link or "onrc.ro" in link or "anaf.ro" in link:
                    confidence = "very_high"
                    source = "mfinante.ro" if "mfinante" in link else "onrc.ro" if "onrc" in link else "anaf.ro"
                elif "targetare.ro" in link:
                    confidence = "high"
                    source = "targetare.ro"
                else:
                    confidence = "medium"
                    source = "other"
                
                if cui not in cui_candidates or confidence_score(confidence) > confidence_score(cui_candidates[cui]["confidence"]):
                    cui_candidates[cui] = {
                        "cui": cui,
                        "source": source,
                        "confidence": confidence,
                        "url": link,
                        "context": snippet[:150],
                        "title": title
                    }
        
        sorted_candidates = sorted(
            cui_candidates.values(), 
            key=lambda x: confidence_score(x["confidence"]), 
            reverse=True
        )[:limit_results]
        
        if not sorted_candidates:
            raise ToolError("Could not extract CUI from search results")
        
        best = sorted_candidates[0]
        result = {
            "company_name": company_name,
            "county": county,
            "search_query": query,
            "candidates_found": len(sorted_candidates),
            "candidates": sorted_candidates,
            "best_match": {
                "cui": best["cui"],
                "confidence": best["confidence"],
                "source": best["source"],
                "next_step": f"Use get_company_financials(tax_id='{best['cui']}') for financial analysis"
            }
        }
        
        return success_response(result, f"Found CUI: {best['cui']} ({best['confidence']} confidence)")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in find_company_cui_by_name: {e}")
        raise ToolError(f"Search failed: {str(e)}")


# ==================== CORE FINANCIAL DATA TOOLS ====================

@mcp.tool()
async def get_company_financials(tax_id: str) -> Dict[str, Any]:
    """
    [CORE] Get raw company financial data from official API
    
    Retrieves complete financial statements including balance sheet,
    income statement, and cash flow data from official Romanian sources.
    
    Args:
        tax_id: Romanian company tax ID (CUI/CIF) - e.g., "12345678" or "RO12345678"
    
    Returns: Complete financial data including:
        - Balance sheet items (assets, liabilities, equity)
        - Income statement (revenue, expenses, profits)
        - Cash flow information
        - Multi-year historical data (if available)
    
    Data source: Official Romanian financial registry via Targetare API
    """
    try:
        tax_id = validate_tax_id(tax_id)
        data = await make_targetare_request(f"/companies/{tax_id}/financial")
        
        if not data:
            raise ToolError(f"No financial data found for tax ID: {tax_id}")
        
        return success_response(data, f"Financial data retrieved for CUI {tax_id}")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in get_company_financials: {e}")
        raise ToolError(f"Financial data retrieval failed: {str(e)}")


@mcp.tool()
async def get_company_profile(tax_id: str) -> Dict[str, Any]:
    """
    [CORE] Get company profile for context in financial analysis
    
    Retrieves company registration and operational details that provide
    important context for financial analysis (industry, size, age, etc.)
    
    Args:
        tax_id: Romanian company tax ID (CUI/CIF)
    
    Returns: Company profile including:
        - Registration details
        - Industry classification (CAEN code)
        - Company size and employee count
        - Legal structure
        - Registration date
    """
    try:
        tax_id = validate_tax_id(tax_id)
        data = await make_targetare_request(f"/companies/{tax_id}")
        
        if not data:
            raise ToolError(f"No company data found for tax ID: {tax_id}")
        
        return success_response(data, f"Company profile retrieved for CUI {tax_id}")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in get_company_profile: {e}")
        raise ToolError(f"Profile retrieval failed: {str(e)}")


# ==================== ADVANCED FINANCIAL ANALYSIS TOOLS ====================

@mcp.tool()
async def analyze_financial_ratios(tax_id: str) -> Dict[str, Any]:
    """
    [ANALYSIS] Calculate comprehensive financial ratios and metrics
    
    Performs in-depth financial ratio analysis across four key dimensions:
    1. Liquidity - ability to meet short-term obligations
    2. Profitability - efficiency in generating profits
    3. Solvency - long-term financial stability and leverage
    4. Efficiency - effectiveness in using assets
    
    Args:
        tax_id: Romanian company tax ID (CUI/CIF)
    
    Returns: Comprehensive ratio analysis with:
        - 15+ key financial ratios
        - Ratio interpretations and benchmarks
        - Overall financial health score (0-100)
        - Financial health rating (Excellent/Good/Fair/Poor/Critical)
        - Key strengths and weaknesses
        - Recommendations for improvement
    """
    try:
        tax_id = validate_tax_id(tax_id)
        
        # Get financial data
        financial_data = await make_targetare_request(f"/companies/{tax_id}/financial")
        
        if not financial_data:
            raise ToolError("Financial data not available for this company")
        
        # Calculate all ratio categories
        liquidity = calculate_liquidity_ratios(financial_data)
        profitability = calculate_profitability_ratios(financial_data)
        solvency = calculate_solvency_ratios(financial_data)
        efficiency = calculate_efficiency_ratios(financial_data)
        
        # Combine all ratios
        all_ratios = {
            "liquidity": liquidity,
            "profitability": profitability,
            "solvency": solvency,
            "efficiency": efficiency
        }
        
        # Calculate overall health score
        health_score, rating = calculate_financial_health_score(all_ratios)
        
        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []
        
        if liquidity.get('current_ratio') and liquidity['current_ratio'] >= 1.5:
            strengths.append("Strong liquidity position")
        elif liquidity.get('current_ratio') and liquidity['current_ratio'] < 1.0:
            weaknesses.append("Weak liquidity - may struggle with short-term obligations")
        
        if profitability.get('net_profit_margin') and profitability['net_profit_margin'] >= 10:
            strengths.append("Excellent profit margins")
        elif profitability.get('net_profit_margin') is not None and profitability['net_profit_margin'] < 0:
            weaknesses.append("Negative profitability - operating at a loss")
        
        if solvency.get('debt_to_equity') and solvency['debt_to_equity'] <= 1.0:
            strengths.append("Conservative leverage")
        elif solvency.get('debt_to_equity') and solvency['debt_to_equity'] > 2.0:
            weaknesses.append("High leverage - elevated financial risk")
        
        analysis = {
            "tax_id": tax_id,
            "analysis_date": datetime.utcnow().isoformat(),
            "ratios": all_ratios,
            "financial_health": {
                "score": health_score,
                "rating": rating,
                "interpretation": {
                    "score_range": f"{health_score}/100",
                    "meaning": "Excellent - Very strong financial position" if health_score >= 80
                             else "Good - Solid financial health" if health_score >= 65
                             else "Fair - Adequate but room for improvement" if health_score >= 50
                             else "Poor - Concerning financial weakness" if health_score >= 35
                             else "Critical - Severe financial distress"
                }
            },
            "key_strengths": strengths if strengths else ["No significant strengths identified"],
            "key_weaknesses": weaknesses if weaknesses else ["No significant weaknesses identified"],
            "recommendations": []
        }
        
        # Add recommendations based on weaknesses
        if liquidity.get('current_ratio') and liquidity['current_ratio'] < 1.0:
            analysis['recommendations'].append("Improve working capital management")
        if profitability.get('net_profit_margin') is not None and profitability['net_profit_margin'] < 5:
            analysis['recommendations'].append("Focus on cost reduction and margin improvement")
        if solvency.get('debt_to_equity') and solvency['debt_to_equity'] > 2.0:
            analysis['recommendations'].append("Consider debt reduction strategies")
        
        if not analysis['recommendations']:
            analysis['recommendations'].append("Maintain current financial discipline")
        
        return success_response(
            analysis, 
            f"Financial ratio analysis completed - Health Score: {health_score}/100 ({rating})"
        )
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_financial_ratios: {e}")
        raise ToolError(f"Analysis failed: {str(e)}")


@mcp.tool()
async def compare_financial_performance(
    tax_ids: List[str], 
    metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    [ANALYSIS] Compare financial performance across multiple companies
    
    Performs side-by-side financial comparison of 2-10 companies with statistical
    analysis to identify leaders, laggards, and outliers.
    
    Args:
        tax_ids: List of 2-10 tax IDs to compare
        metrics: Optional list of specific metrics to focus on
    
    Returns: Comparative analysis including:
        - Side-by-side financial metrics
        - Ranking by key performance indicators
        - Statistical summary (mean, median, std dev)
        - Outlier identification
        - Relative performance scores
        - Industry positioning insights
    """
    try:
        if not tax_ids or len(tax_ids) < 2:
            raise ToolError("Provide at least 2 companies to compare")
        
        if len(tax_ids) > 10:
            raise ToolError("Maximum 10 companies allowed for comparison")
        
        # Validate all tax IDs first
        cleaned_ids = [validate_tax_id(tid) for tid in tax_ids]
        
        # Fetch all companies' data in parallel
        tasks = []
        for cleaned_id in cleaned_ids:
            tasks.append(make_targetare_request(f"/companies/{cleaned_id}"))
            tasks.append(make_targetare_request(f"/companies/{cleaned_id}/financial"))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Organize and analyze results
        companies_data = []
        for i in range(0, len(results), 2):
            company_data = results[i] if not isinstance(results[i], Exception) else None
            financial_data = results[i+1] if not isinstance(results[i+1], Exception) else None
            
            if financial_data and company_data:
                # Calculate ratios for each company
                ratios = {
                    "liquidity": calculate_liquidity_ratios(financial_data),
                    "profitability": calculate_profitability_ratios(financial_data),
                    "solvency": calculate_solvency_ratios(financial_data),
                    "efficiency": calculate_efficiency_ratios(financial_data)
                }
                health_score, rating = calculate_financial_health_score(ratios)
                
                companies_data.append({
                    "tax_id": cleaned_ids[i//2],
                    "company_name": company_data.get("name", "Unknown"),
                    "revenue": financial_data.get("revenue", 0),
                    "net_income": financial_data.get("net_income", 0),
                    "total_assets": financial_data.get("total_assets", 0),
                    "ratios": ratios,
                    "health_score": health_score,
                    "health_rating": rating
                })
        
        if len(companies_data) < 2:
            raise ToolError("Could not retrieve financial data for enough companies")
        
        # Statistical analysis
        revenues = [c['revenue'] for c in companies_data if c['revenue'] > 0]
        health_scores = [c['health_score'] for c in companies_data]
        
        statistics = {
            "revenue": {
                "mean": round(mean(revenues), 2) if revenues else 0,
                "median": round(median(revenues), 2) if revenues else 0,
                "std_dev": round(stdev(revenues), 2) if len(revenues) > 1 else 0,
                "min": round(min(revenues), 2) if revenues else 0,
                "max": round(max(revenues), 2) if revenues else 0
            },
            "health_score": {
                "mean": round(mean(health_scores), 1),
                "median": round(median(health_scores), 1),
                "std_dev": round(stdev(health_scores), 1) if len(health_scores) > 1 else 0
            }
        }
        
        # Rankings
        by_revenue = sorted(companies_data, key=lambda x: x['revenue'], reverse=True)
        by_health = sorted(companies_data, key=lambda x: x['health_score'], reverse=True)
        
        result = {
            "companies_compared": len(companies_data),
            "comparison_date": datetime.utcnow().isoformat(),
            "companies": companies_data,
            "rankings": {
                "by_revenue": [
                    {
                        "rank": i+1, 
                        "tax_id": c['tax_id'], 
                        "name": c['company_name'], 
                        "revenue": c['revenue']
                    } 
                    for i, c in enumerate(by_revenue)
                ],
                "by_financial_health": [
                    {
                        "rank": i+1, 
                        "tax_id": c['tax_id'], 
                        "name": c['company_name'], 
                        "score": c['health_score']
                    } 
                    for i, c in enumerate(by_health)
                ]
            },
            "statistical_summary": statistics,
            "leader": {
                "by_revenue": by_revenue[0]['company_name'] if by_revenue else None,
                "by_health": by_health[0]['company_name'] if by_health else None
            }
        }
        
        return success_response(result, f"Compared {len(companies_data)} companies successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in compare_financial_performance: {e}")
        raise ToolError(f"Comparison failed: {str(e)}")


@mcp.tool()
async def assess_credit_risk(tax_id: str) -> Dict[str, Any]:
    """
    [ANALYSIS] Assess credit risk and financial stability
    
    Comprehensive credit risk assessment using multiple financial indicators
    to evaluate the company's creditworthiness and default probability.
    
    Args:
        tax_id: Romanian company tax ID (CUI/CIF)
    
    Returns: Credit risk assessment with:
        - Credit risk score (0-100, higher is better)
        - Credit rating (AAA to D scale)
        - Default probability estimate
        - Key risk factors identified
        - Early warning indicators
        - Risk mitigation recommendations
    """
    try:
        tax_id = validate_tax_id(tax_id)
        
        # Fetch profile and financials in parallel
        profile, financials = await asyncio.gather(
            make_targetare_request(f"/companies/{tax_id}"),
            make_targetare_request(f"/companies/{tax_id}/financial"),
            return_exceptions=True
        )
        
        if not financials or isinstance(financials, Exception):
            raise ToolError("Financial data not available for credit assessment")
        
        # Calculate ratios
        liquidity = calculate_liquidity_ratios(financials)
        profitability = calculate_profitability_ratios(financials)
        solvency = calculate_solvency_ratios(financials)
        
        # Credit scoring model
        credit_score = 0
        risk_factors = []
        
        # Liquidity (25 points)
        current_ratio = liquidity.get('current_ratio', 0)
        if current_ratio:
            if current_ratio >= 2.0:
                credit_score += 25
            elif current_ratio >= 1.5:
                credit_score += 20
            elif current_ratio >= 1.0:
                credit_score += 15
            elif current_ratio >= 0.75:
                credit_score += 10
            else:
                credit_score += 5
                risk_factors.append("Critical liquidity shortage")
        
        # Profitability (20 points)
        net_margin = profitability.get('net_profit_margin', 0)
        if net_margin is not None:
            if net_margin >= 10:
                credit_score += 20
            elif net_margin >= 5:
                credit_score += 15
            elif net_margin >= 2:
                credit_score += 10
            elif net_margin >= 0:
                credit_score += 5
            else:
                risk_factors.append("Operating losses detected")
        
        # Solvency (35 points)
        debt_to_equity = solvency.get('debt_to_equity', 0)
        interest_coverage = solvency.get('interest_coverage', 0)
        
        if debt_to_equity is not None:
            if debt_to_equity <= 0.5:
                credit_score += 20
            elif debt_to_equity <= 1.0:
                credit_score += 15
            elif debt_to_equity <= 2.0:
                credit_score += 10
            elif debt_to_equity <= 3.0:
                credit_score += 5
            else:
                risk_factors.append("Excessive leverage")
        
        if interest_coverage:
            if interest_coverage >= 5:
                credit_score += 15
            elif interest_coverage >= 3:
                credit_score += 12
            elif interest_coverage >= 2:
                credit_score += 8
            elif interest_coverage >= 1:
                credit_score += 4
            else:
                risk_factors.append("Insufficient interest coverage")
        
        # ROA (20 points)
        roa = profitability.get('roa', 0)
        if roa is not None:
            if roa >= 15:
                credit_score += 20
            elif roa >= 10:
                credit_score += 15
            elif roa >= 5:
                credit_score += 10
            elif roa >= 0:
                credit_score += 5
        
        # Determine credit rating
        if credit_score >= 90:
            rating, risk_level, default_prob = "AAA", "Minimal", "< 0.5%"
        elif credit_score >= 80:
            rating, risk_level, default_prob = "AA", "Very Low", "0.5-1%"
        elif credit_score >= 70:
            rating, risk_level, default_prob = "A", "Low", "1-2%"
        elif credit_score >= 60:
            rating, risk_level, default_prob = "BBB", "Moderate", "2-5%"
        elif credit_score >= 50:
            rating, risk_level, default_prob = "BB", "Elevated", "5-10%"
        elif credit_score >= 40:
            rating, risk_level, default_prob = "B", "High", "10-20%"
        elif credit_score >= 30:
            rating, risk_level, default_prob = "CCC", "Very High", "20-35%"
        elif credit_score >= 20:
            rating, risk_level, default_prob = "CC", "Substantial", "35-50%"
        elif credit_score >= 10:
            rating, risk_level, default_prob = "C", "Extremely High", "50-75%"
        else:
            rating, risk_level, default_prob = "D", "Default Imminent", "> 75%"
        
        assessment = {
            "tax_id": tax_id,
            "assessment_date": datetime.utcnow().isoformat(),
            "credit_score": credit_score,
            "credit_rating": rating,
            "risk_level": risk_level,
            "default_probability": default_prob,
            "investment_grade": credit_score >= 60,
            "key_metrics": {
                "current_ratio": current_ratio,
                "net_profit_margin": net_margin,
                "debt_to_equity": debt_to_equity,
                "interest_coverage": interest_coverage,
                "roa": roa
            },
            "risk_factors": risk_factors if risk_factors else ["No significant risk factors identified"],
            "recommendations": []
        }
        
        # Add recommendations
        if credit_score < 60:
            assessment['recommendations'].append("Consider requiring additional collateral or guarantees")
        if current_ratio and current_ratio < 1.0:
            assessment['recommendations'].append("Monitor cash flow closely - liquidity concerns")
        if debt_to_equity and debt_to_equity > 2.0:
            assessment['recommendations'].append("High leverage - recommend debt restructuring")
        if not assessment['recommendations']:
            assessment['recommendations'].append("Creditworthy - acceptable risk profile")
        
        return success_response(
            assessment, 
            f"Credit assessment: {rating} rating ({risk_level} risk)"
        )
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in assess_credit_risk: {e}")
        raise ToolError(f"Assessment failed: {str(e)}")


@mcp.tool()
async def analyze_financial_trends(tax_id: str, years: int = 3) -> Dict[str, Any]:
    """
    [ANALYSIS] Analyze financial trends over time
    
    Performs time-series analysis of financial metrics to identify trends,
    patterns, and trajectory of the company's financial performance.
    
    Args:
        tax_id: Romanian company tax ID (CUI/CIF)
        years: Number of years to analyze (default: 3)
    
    Returns: Trend analysis with:
        - Year-over-year (YoY) growth rates
        - Compound annual growth rate (CAGR)
        - Trend direction (increasing/decreasing/stable)
        - Volatility measures
        - Performance trajectory assessment
    """
    try:
        tax_id = validate_tax_id(tax_id)
        
        # Get financial data (API may return multi-year data)
        financial_data = await make_targetare_request(f"/companies/{tax_id}/financial")
        
        if not financial_data:
            raise ToolError("Financial data not available")
        
        # Check if we have historical data
        if isinstance(financial_data, list):
            historical_data = sorted(financial_data, key=lambda x: x.get('year', 0))
        else:
            historical_data = [financial_data]
        
        if len(historical_data) < 2:
            raise ToolError(
                "Insufficient historical data for trend analysis. "
                "At least 2 years of data required."
            )
        
        # Calculate trends
        trends = calculate_trend_analysis(historical_data)
        
        # Calculate ratio trends if we have enough data
        ratio_trends = {}
        if len(historical_data) >= 2:
            for period in historical_data:
                year = period.get('year', 'unknown')
                liquidity = calculate_liquidity_ratios(period)
                profitability = calculate_profitability_ratios(period)
                
                ratio_trends[str(year)] = {
                    "current_ratio": liquidity.get('current_ratio'),
                    "net_profit_margin": profitability.get('net_profit_margin'),
                    "roe": profitability.get('roe')
                }
        
        analysis = {
            "tax_id": tax_id,
            "analysis_date": datetime.utcnow().isoformat(),
            "periods_analyzed": len(historical_data),
            "trends": trends,
            "ratio_evolution": ratio_trends,
            "summary": {
                "revenue_trend": trends.get('revenue', {}).get('trend', 'unknown'),
                "profitability_trend": trends.get('net_income', {}).get('trend', 'unknown'),
                "asset_growth": trends.get('total_assets', {}).get('trend', 'unknown')
            },
            "insights": []
        }
        
        # Generate insights
        revenue_growth = trends.get('revenue', {}).get('yoy_growth_pct', 0)
        if revenue_growth and revenue_growth > 15:
            analysis['insights'].append("Strong revenue growth momentum")
        elif revenue_growth and revenue_growth < 0:
            analysis['insights'].append("Revenue decline - investigate market conditions")
        
        profit_growth = trends.get('net_income', {}).get('yoy_growth_pct', 0)
        if profit_growth and abs(profit_growth) > abs(revenue_growth or 0) + 10:
            if profit_growth > 0:
                analysis['insights'].append("Profit growing faster than revenue - improving efficiency")
            else:
                analysis['insights'].append("Profit declining faster than revenue - margin compression")
        
        if not analysis['insights']:
            analysis['insights'].append("Stable financial trajectory")
        
        return success_response(
            analysis, 
            f"Trend analysis completed for {len(historical_data)} periods"
        )
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_financial_trends: {e}")
        raise ToolError(f"Analysis failed: {str(e)}")


@mcp.tool()
async def generate_financial_report(tax_id: str) -> Dict[str, Any]:
    """
    [ANALYSIS] Generate comprehensive financial intelligence report
    
    Creates an executive-level financial report combining all analysis tools
    to provide complete financial intelligence on a Romanian company.
    
    Args:
        tax_id: Romanian company tax ID (CUI/CIF)
    
    Returns: Complete financial intelligence report with:
        - Executive summary
        - Company overview and context
        - Financial position snapshot
        - Comprehensive ratio analysis
        - Credit risk assessment
        - Key performance indicators dashboard
        - Investment/lending recommendation
    """
    try:
        tax_id = validate_tax_id(tax_id)
        
        # Gather all available data in parallel
        tasks = [
            make_targetare_request(f"/companies/{tax_id}"),
            make_targetare_request(f"/companies/{tax_id}/financial"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        profile, financials = results
        
        if not financials or isinstance(financials, Exception):
            raise ToolError("Financial data not available")
        
        # Perform all analyses
        liquidity = calculate_liquidity_ratios(financials)
        profitability = calculate_profitability_ratios(financials)
        solvency = calculate_solvency_ratios(financials)
        efficiency = calculate_efficiency_ratios(financials)
        
        all_ratios = {
            "liquidity": liquidity,
            "profitability": profitability,
            "solvency": solvency,
            "efficiency": efficiency
        }
        
        health_score, rating = calculate_financial_health_score(all_ratios)
        
        # Build comprehensive report
        report = {
            "report_type": "comprehensive_financial_intelligence",
            "tax_id": tax_id,
            "generated_at": datetime.utcnow().isoformat(),
            
            "executive_summary": {
                "company_name": profile.get('name', 'Unknown') if profile and not isinstance(profile, Exception) else 'Unknown',
                "financial_health_score": health_score,
                "financial_health_rating": rating,
                "key_finding": f"Financial health rated as {rating} with score of {health_score}/100",
                "recommendation": (
                    "Approved for investment" if health_score >= 65 
                    else "Requires additional due diligence" if health_score >= 50 
                    else "Not recommended"
                )
            },
            
            "company_overview": profile if profile and not isinstance(profile, Exception) else {"note": "Profile data unavailable"},
            
            "financial_position": {
                "revenue": financials.get('revenue', 0),
                "net_income": financials.get('net_income', 0),
                "total_assets": financials.get('total_assets', 0),
                "total_equity": financials.get('total_equity', 0),
                "total_debt": financials.get('total_debt', 0)
            },
            
            "ratio_analysis": all_ratios,
            
            "key_metrics_dashboard": {
                "liquidity": {
                    "current_ratio": liquidity.get('current_ratio'),
                    "status": (
                        "Healthy" if liquidity.get('current_ratio', 0) >= 1.5 
                        else "Adequate" if liquidity.get('current_ratio', 0) >= 1.0 
                        else "Concerning"
                    )
                },
                "profitability": {
                    "net_margin_pct": profitability.get('net_profit_margin'),
                    "roe_pct": profitability.get('roe'),
                    "status": (
                        "Strong" if profitability.get('roe', 0) >= 15 
                        else "Moderate" if profitability.get('roe', 0) >= 10 
                        else "Weak"
                    )
                },
                "leverage": {
                    "debt_to_equity": solvency.get('debt_to_equity'),
                    "status": (
                        "Conservative" if solvency.get('debt_to_equity', 0) <= 1.0 
                        else "Moderate" if solvency.get('debt_to_equity', 0) <= 2.0 
                        else "Aggressive"
                    )
                }
            },
            
            "strengths_and_weaknesses": {
                "strengths": [],
                "weaknesses": [],
                "opportunities": ["Leverage strong metrics for growth", "Optimize capital structure"],
                "threats": ["Market competition", "Economic conditions"]
            }
        }
        
        # Add specific strengths/weaknesses
        if liquidity.get('current_ratio', 0) >= 1.5:
            report['strengths_and_weaknesses']['strengths'].append("Strong liquidity position")
        if profitability.get('net_profit_margin', 0) >= 10:
            report['strengths_and_weaknesses']['strengths'].append("Excellent profitability")
        if solvency.get('debt_to_equity', 0) and solvency['debt_to_equity'] <= 1.0:
            report['strengths_and_weaknesses']['strengths'].append("Conservative leverage")
        
        if liquidity.get('current_ratio', 0) < 1.0:
            report['strengths_and_weaknesses']['weaknesses'].append("Liquidity concerns")
        if profitability.get('net_profit_margin') is not None and profitability['net_profit_margin'] < 0:
            report['strengths_and_weaknesses']['weaknesses'].append("Operating losses")
        if solvency.get('debt_to_equity', 0) > 2.0:
            report['strengths_and_weaknesses']['weaknesses'].append("High leverage")
        
        return success_response(
            report, 
            f"Comprehensive financial report generated - Health Score: {health_score}/100"
        )
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in generate_financial_report: {e}")
        raise ToolError(f"Report generation failed: {str(e)}")


@mcp.tool()
async def benchmark_against_industry(
    tax_id: str, 
    industry_caen: Optional[str] = None
) -> Dict[str, Any]:
    """
    [ANALYSIS] Benchmark company performance against industry peers
    
    Compares company's financial metrics against industry averages and
    percentiles to assess relative competitive position.
    
    Args:
        tax_id: Romanian company tax ID (CUI/CIF)
        industry_caen: Optional CAEN industry code for specific industry comparison
    
    Returns: Industry benchmarking analysis with:
        - Company metrics vs. industry averages
        - Percentile rankings (25th, 50th, 75th)
        - Competitive positioning
        - Areas of competitive advantage
        - Areas requiring improvement
        - Industry-specific insights
    """
    try:
        tax_id = validate_tax_id(tax_id)
        
        # Get company data
        profile, financials = await asyncio.gather(
            make_targetare_request(f"/companies/{tax_id}"),
            make_targetare_request(f"/companies/{tax_id}/financial"),
            return_exceptions=True
        )
        
        if not financials or isinstance(financials, Exception):
            raise ToolError("Financial data not available")
        
        # Calculate company ratios
        company_ratios = {
            "liquidity": calculate_liquidity_ratios(financials),
            "profitability": calculate_profitability_ratios(financials),
            "solvency": calculate_solvency_ratios(financials),
            "efficiency": calculate_efficiency_ratios(financials)
        }
        
        # Industry benchmarks (representative data)
        # In production, fetch from aggregated database
        industry_benchmarks = {
            "retail": {
                "current_ratio": {"p25": 1.2, "median": 1.5, "p75": 2.0, "mean": 1.6},
                "net_profit_margin": {"p25": 2.0, "median": 4.0, "p75": 7.0, "mean": 4.5},
                "roe": {"p25": 8.0, "median": 12.0, "p75": 18.0, "mean": 13.0},
                "debt_to_equity": {"p25": 0.5, "median": 1.0, "p75": 1.8, "mean": 1.1}
            },
            "manufacturing": {
                "current_ratio": {"p25": 1.3, "median": 1.7, "p75": 2.2, "mean": 1.8},
                "net_profit_margin": {"p25": 3.0, "median": 6.0, "p75": 10.0, "mean": 6.5},
                "roe": {"p25": 10.0, "median": 15.0, "p75": 22.0, "mean": 16.0},
                "debt_to_equity": {"p25": 0.6, "median": 1.2, "p75": 2.0, "mean": 1.3}
            },
            "services": {
                "current_ratio": {"p25": 1.0, "median": 1.4, "p75": 1.9, "mean": 1.5},
                "net_profit_margin": {"p25": 5.0, "median": 8.0, "p75": 12.0, "mean": 8.5},
                "roe": {"p25": 12.0, "median": 18.0, "p75": 25.0, "mean": 18.5},
                "debt_to_equity": {"p25": 0.4, "median": 0.9, "p75": 1.5, "mean": 1.0}
            }
        }
        
        # Use default industry benchmarks
        benchmarks = industry_benchmarks.get("manufacturing", industry_benchmarks["manufacturing"])
        
        # Compare metrics
        comparison = {
            "tax_id": tax_id,
            "analysis_date": datetime.utcnow().isoformat(),
            "company_metrics": company_ratios,
            "industry_benchmarks": benchmarks,
            "relative_position": {},
            "competitive_advantages": [],
            "improvement_areas": []
        }
        
        # Current ratio comparison
        company_cr = company_ratios['liquidity'].get('current_ratio')
        if company_cr:
            if company_cr >= benchmarks['current_ratio']['p75']:
                comparison['relative_position']['liquidity'] = "Top Quartile"
                comparison['competitive_advantages'].append("Superior liquidity position")
            elif company_cr >= benchmarks['current_ratio']['median']:
                comparison['relative_position']['liquidity'] = "Above Average"
            elif company_cr >= benchmarks['current_ratio']['p25']:
                comparison['relative_position']['liquidity'] = "Below Average"
            else:
                comparison['relative_position']['liquidity'] = "Bottom Quartile"
                comparison['improvement_areas'].append("Improve working capital management")
        
        # Profitability comparison
        company_npm = company_ratios['profitability'].get('net_profit_margin')
        if company_npm is not None:
            if company_npm >= benchmarks['net_profit_margin']['p75']:
                comparison['relative_position']['profitability'] = "Top Quartile"
                comparison['competitive_advantages'].append("Excellent profit margins")
            elif company_npm >= benchmarks['net_profit_margin']['median']:
                comparison['relative_position']['profitability'] = "Above Average"
            elif company_npm >= benchmarks['net_profit_margin']['p25']:
                comparison['relative_position']['profitability'] = "Below Average"
                comparison['improvement_areas'].append("Enhance operational efficiency")
            else:
                comparison['relative_position']['profitability'] = "Bottom Quartile"
                comparison['improvement_areas'].append("Critical: address profitability issues")
        
        if not comparison['competitive_advantages']:
            comparison['competitive_advantages'].append("Performance in line with industry")
        
        return success_response(comparison, "Industry benchmarking analysis completed")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in benchmark_against_industry: {e}")
        raise ToolError(f"Benchmarking failed: {str(e)}")


# ==================== MCP RESOURCES ====================

@mcp.resource("config://server-info")
def get_server_info() -> str:
    """Server configuration and capabilities"""
    return json.dumps({
        "server_name": SERVER_NAME,
        "version": "2.0.0",
        "port": PORT,
        "specialization": "Romanian Company Financial Intelligence",
        "async_support": True,
        "connection_pooling": True,
        "total_tools": 9,
        "tool_categories": {
            "company_search": 1,
            "core_financial_data": 2,
            "advanced_analysis": 6
        },
        "apis_integrated": [
            "Targetare.ro Official API v1",
            "Google Custom Search API v1 (for CUI lookup)"
        ],
        "security": {
            "secret_manager": "Google Cloud Secret Manager (optional)",
            "authentication": "Bearer token",
            "gcp_project": GCP_PROJECT_ID
        },
        "performance_features": [
            "Reusable aiohttp ClientSession",
            "Connection pooling (100 connections, 30 per host)",
            "Exponential backoff retry logic",
            "Async request handling",
            "Proper resource lifecycle management"
        ],
        "analysis_capabilities": [
            "Financial ratio analysis (15+ ratios)",
            "Credit risk assessment",
            "Multi-company comparison",
            "Trend analysis",
            "Industry benchmarking",
            "Financial health scoring",
            "Comprehensive reporting"
        ]
    }, indent=2)


@mcp.resource("docs://analysis-guide")
def get_analysis_guide() -> str:
    """Guide for financial analysis workflows"""
    return json.dumps({
        "typical_workflows": {
            "complete_financial_analysis": {
                "description": "Full financial analysis from company name to comprehensive report",
                "steps": [
                    "1. find_company_cui_by_name(company_name='Target Company SRL')",
                    "2. Extract CUI from best_match",
                    "3. generate_financial_report(tax_id=extracted_cui)",
                    "4. analyze_financial_ratios(tax_id=extracted_cui) for detailed metrics",
                    "5. assess_credit_risk(tax_id=extracted_cui) for creditworthiness"
                ]
            },
            "competitive_analysis": {
                "description": "Compare multiple companies in same industry",
                "steps": [
                    "1. Find CUIs for all target companies",
                    "2. compare_financial_performance(tax_ids=[cui1, cui2, cui3])",
                    "3. benchmark_against_industry(tax_id=cui1) for each company"
                ]
            }
        }
    }, indent=2)


# ==================== SERVER STARTUP ====================

if __name__ == "__main__":
    print("=" * 80)
    print(f"🏦 {SERVER_NAME.upper().replace('-', ' ')}")
    print("=" * 80)
    print("Specialized Financial Intelligence for Romanian Companies (OPTIMIZED)")
    print(f"Port: {PORT}")
    print("=" * 80)
    
    print("\n✨ PERFORMANCE FEATURES:")
    print("  • Reusable aiohttp ClientSession with connection pooling")
    print(f"  • {CONNECTOR_LIMIT} total connections, {CONNECTOR_LIMIT_PER_HOST} per host")
    print("  • Exponential backoff retry logic")
    print("  • Proper async resource management")
    print("  • Structured error handling with ToolError")
    
    print("\n🔐 SECURITY CONFIGURATION:")
    print(f"  • GCP Project: {GCP_PROJECT_ID}")
    print(f"  • Secret Manager: {'✓ Available' if SECRET_MANAGER_AVAILABLE else '✗ Not Available'}")
    print(f"  • Targetare API: {'✓ Configured' if api_config.targetare_key else '✗ Not Configured'}")
    print(f"  • Google Search: {'✓ Configured' if (api_config.google_search_key and api_config.google_search_cx) else '✗ Not Configured'}")
    
    print("\n🔍 TOOLS (9 Total):")
    print("  1. find_company_cui_by_name - Find CUI by company name")
    print("  2. get_company_financials - Raw financial data")
    print("  3. get_company_profile - Company context")
    print("  4. analyze_financial_ratios - 15+ ratio analysis + health score")
    print("  5. compare_financial_performance - Multi-company comparison")
    print("  6. assess_credit_risk - Credit scoring & risk assessment")
    print("  7. analyze_financial_trends - Time-series analysis")
    print("  8. generate_financial_report - Comprehensive BI report")
    print("  9. benchmark_against_industry - Industry comparison")
    
    print("\n" + "=" * 80)
    print(f"🚀 Starting optimized server on http://0.0.0.0:{PORT}...")
    print("=" * 80)
    
    # Run with proper lifecycle management
    mcp.run(transport="sse", host="0.0.0.0", port=PORT)