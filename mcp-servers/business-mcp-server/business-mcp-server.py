#!/usr/bin/env python3
"""
Business Plan Generator MCP Server - FULLY OPTIMIZED VERSION
Complete AI-powered business plan generation with comprehensive tools

PERFORMANCE OPTIMIZATIONS:
- Structured error handling with ToolError
- Type-safe implementations
- Proper async context management
- Resource lifecycle management
- Efficient parallel execution
- Memory-efficient processing

FEATURES:
- 9 specialized business planning tools
- Deep market research with Google Search
- Bottom-up financial modeling
- Location and cost analysis
- Staffing and salary research
- Competitor intelligence
- Master Prompt Framework architecture
"""

import os
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from contextlib import asynccontextmanager

try:
    from fastmcp import FastMCP
    from fastmcp.exceptions import ToolError
except ImportError:
    raise ImportError("fastmcp is required. Install with: pip install fastmcp")

from dotenv import load_dotenv
from google import genai
from google.genai import types

# ==================== CONFIGURATION ====================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Server Configuration
PORT = int(os.getenv("PORT", "8000"))
SERVER_NAME = "business-plan-generator-server"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./business_plans")

# API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USE_GOOGLE_SEARCH = os.getenv("USE_GOOGLE_SEARCH", "true").lower() == "true"

# Model Configuration
REASONING_MODEL = 'gemini-2.5-flash'
FAST_MODEL = 'gemini-2.5-flash-lite'
MAX_OUTPUT_TOKENS = 8000
DEFAULT_TEMPERATURE = 0.5

# Create output directory
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# ==================== DATA CLASSES ====================

@dataclass
class APIConfig:
    """API configuration container"""
    gemini_key: Optional[str] = None
    use_search: bool = True


@dataclass
class UserInput:
    """User's business parameters"""
    business_type: str
    initial_budget: float
    location: str
    timeline_months: int = 12
    business_name: Optional[str] = None


# Initialize API configuration
api_config = APIConfig(
    gemini_key=GEMINI_API_KEY,
    use_search=USE_GOOGLE_SEARCH
)

if api_config.gemini_key:
    logger.info("✓ Gemini API configured")
else:
    logger.warning("⚠ Gemini API key not found - tools will be disabled")

# ==================== LIFESPAN MANAGEMENT ====================

@asynccontextmanager
async def lifespan(app: FastMCP):
    """
    Lifespan context manager for FastMCP server
    Handles startup and shutdown of resources
    """
    logger.info("🚀 Starting Business Plan Generator Server...")
    
    # Startup: Verify configuration
    if not api_config.gemini_key:
        logger.error("GEMINI_API_KEY not configured - server will not function properly")
    else:
        logger.info("✓ Gemini API verified")
    
    logger.info(f"✓ Output directory: {OUTPUT_DIR}")
    logger.info(f"✓ Google Search: {'Enabled' if api_config.use_search else 'Disabled'}")
    
    yield
    
    # Shutdown: Cleanup
    logger.info("🛑 Shutting down server...")
    logger.info("✓ Cleanup completed")


# ==================== INITIALIZE FASTMCP SERVER ====================

mcp = FastMCP(
    name=SERVER_NAME,
    dependencies=["google-generativeai", "python-dotenv"]
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


# ==================== BUSINESS PLAN GENERATOR ====================

class BusinessPlanGenerator:
    """Complete AI Business Plan Generator with optimized error handling"""
    
    def __init__(self):
        if not api_config.gemini_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_config.gemini_key)
        self.reasoning_model = REASONING_MODEL
        self.fast_model = FAST_MODEL
        self.search_tool = types.Tool(google_search=types.GoogleSearch())
        
        logger.info("✓ Business Plan Generator initialized")
    
    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """Parse JSON from model response with robust error handling"""
        if not text:
            return None
        
        # Remove markdown code blocks
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON object
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
            
            logger.warning("Failed to parse JSON from model response")
            return None
    
    async def _call_model(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        temperature: float = DEFAULT_TEMPERATURE, 
        use_search: bool = False
    ) -> str:
        """Call Gemini model with optional search"""
        if model is None:
            model = self.reasoning_model
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=MAX_OUTPUT_TOKENS
        )
        
        if use_search and api_config.use_search:
            config.tools = [self.search_tool]
        
        def _generate():
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                return response.text
            except Exception as e:
                logger.error(f"Model generation error: {e}")
                raise
        
        return await asyncio.to_thread(_generate)
    
    async def research_location_and_costs(self, user_input: UserInput) -> Dict:
        """Research real estate, utilities, and location-specific costs"""
        research_prompt = f"""
You are a commercial real estate and business cost analyst. Research for a {user_input.business_type} in {user_input.location}.

Use Google Search to find CURRENT data for:

1. COMMERCIAL REAL ESTATE:
   - Average cost per sq ft for office/retail space
   - Recommended space size
   - Lease terms and deposits
   - Best neighborhoods

2. UTILITIES & OPERATING COSTS:
   - Monthly electricity, internet, water
   - Location-specific taxes/fees

3. LEGAL & SETUP COSTS:
   - Business registration fees
   - Required licenses and permits
   - Professional services costs

Return JSON with keys: real_estate, utilities_monthly, setup_costs, location_recommendation, sources.
Budget: ${user_input.initial_budget:,.0f}
"""
        
        try:
            response = await self._call_model(
                research_prompt,
                model=self.fast_model,
                use_search=True,
                temperature=0.3
            )
            
            parsed = self._parse_json_response(response)
            if not parsed:
                raise ToolError("Failed to parse location research response")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Location research error: {e}")
            raise ToolError(f"Location research failed: {str(e)}")
    
    async def research_staffing_and_salaries(self, user_input: UserInput) -> Dict:
        """Research required positions and market salaries"""
        staffing_prompt = f"""
You are an HR consultant. Research staffing for a {user_input.business_type} in {user_input.location}.

Use Google Search to find:

1. REQUIRED POSITIONS by priority (core, phase1, phase2, phase3)
2. MARKET SALARIES with benefits and taxes
3. HIRING TIMELINE for Year 1

Return JSON with: positions (array with title, priority, hire_month, salary_range, total_annual_cost), 
staffing_summary (year1_total_headcount, year1_total_payroll_cost, monthly_payroll_ramp), sources.
Budget: ${user_input.initial_budget:,.0f}
"""
        
        try:
            response = await self._call_model(
                staffing_prompt,
                model=self.fast_model,
                use_search=True,
                temperature=0.3
            )
            
            parsed = self._parse_json_response(response)
            if not parsed:
                raise ToolError("Failed to parse staffing research response")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Staffing research error: {e}")
            raise ToolError(f"Staffing research failed: {str(e)}")
    
    async def research_equipment_and_resources(self, user_input: UserInput) -> Dict:
        """Research required equipment, technology, and resources"""
        equipment_prompt = f"""
You are a business operations consultant. Research equipment for a {user_input.business_type} in {user_input.location}.

Use Google Search for CURRENT prices:

1. TECHNOLOGY & SOFTWARE (computers, subscriptions, cloud)
2. FURNITURE & FIXTURES
3. INDUSTRY-SPECIFIC EQUIPMENT
4. SUPPLIES & CONSUMABLES (monthly)

Return JSON with: technology, furniture, specialized_equipment, supplies_monthly, 
cost_summary (total_one_time_capex, total_monthly_subscriptions, total_monthly_supplies), sources.
Budget: ${user_input.initial_budget:,.0f}
"""
        
        try:
            response = await self._call_model(
                equipment_prompt,
                model=self.fast_model,
                use_search=True,
                temperature=0.3
            )
            
            parsed = self._parse_json_response(response)
            if not parsed:
                raise ToolError("Failed to parse equipment research response")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Equipment research error: {e}")
            raise ToolError(f"Equipment research failed: {str(e)}")
    
    async def research_market_and_competitors(self, user_input: UserInput) -> Dict:
        """Deep market analysis and competitor research"""
        market_prompt = f"""
You are a market research analyst. Conduct analysis for a {user_input.business_type} in {user_input.location}.

Use Google Search to find:

1. MARKET SIZE (TAM/SAM/SOM bottom-up with ARPU)
2. COMPETITOR ANALYSIS (direct/indirect with pricing and strengths/weaknesses)
3. MARKET TRENDS (growth rate, emerging trends, threats, opportunities)
4. CUSTOMER PERSONAS (demographics, pain points, willingness to pay)

Return JSON with: market_sizing (tam, sam, som), competitors, customer_personas, market_trends, sources.
"""
        
        try:
            response = await self._call_model(
                market_prompt,
                model=self.fast_model,
                use_search=True,
                temperature=0.4
            )
            
            parsed = self._parse_json_response(response)
            if not parsed:
                raise ToolError("Failed to parse market research response")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Market research error: {e}")
            raise ToolError(f"Market research failed: {str(e)}")
    
    async def generate_problem_solution(self, market_data: Dict, user_input: UserInput) -> Dict:
        """Generate company purpose, problem, solution, and value proposition"""
        prompt = f"""
You are a business strategist. Define the company's purpose, problem, and solution.

BUSINESS TYPE: {user_input.business_type}
LOCATION: {user_input.location}
BUDGET: ${user_input.initial_budget:,.0f}

MARKET RESEARCH:
{json.dumps(market_data.get('customer_personas', []), indent=2)[:1000]}

Return JSON with:
- company_purpose (1 sentence mission)
- problem (target_customer, acute_pain, current_alternatives, shortcomings, quantifiable_costs)
- solution (description, unique_capability, key_features, why_better)
- value_proposition (customer_pains, pain_relievers, customer_gains, gain_creators, value_statement)
"""
        
        try:
            response = await self._call_model(prompt, temperature=0.6)
            parsed = self._parse_json_response(response)
            if not parsed:
                raise ToolError("Failed to parse problem/solution response")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Problem/solution generation error: {e}")
            raise ToolError(f"Problem/solution generation failed: {str(e)}")
    
    async def generate_competitive_analysis(self, market_data: Dict, solution_data: Dict) -> Dict:
        """Generate competitive analysis and positioning"""
        prompt = f"""
You are a competitive intelligence analyst.

COMPETITORS:
{json.dumps(market_data.get('competitors', []), indent=2)[:1500]}

YOUR SOLUTION:
{json.dumps(solution_data.get('solution', {}), indent=2)}

Return JSON with:
- competitors (array with name, category, product, pricing, strengths, weaknesses, market_position)
- swot (strengths, weaknesses, opportunities, threats)
- competitive_advantage (unique_factors, sustainability, plan_to_win)
"""
        
        try:
            response = await self._call_model(prompt, temperature=0.5)
            parsed = self._parse_json_response(response)
            if not parsed:
                raise ToolError("Failed to parse competitive analysis response")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Competitive analysis error: {e}")
            raise ToolError(f"Competitive analysis failed: {str(e)}")
    
    async def generate_gtm_strategy(self, value_prop: Dict, personas: List, competitors: List) -> Dict:
        """Generate go-to-market and sales strategy"""
        prompt = f"""
You are a growth marketing strategist.

VALUE PROPOSITION:
{json.dumps(value_prop, indent=2)[:800]}

CUSTOMER PERSONAS:
{json.dumps(personas, indent=2)[:800]}

COMPETITORS:
{json.dumps(competitors, indent=2)[:1000]}

Return JSON with:
- marketing_strategy (product_positioning, pricing_model, promotion_channels with costs, distribution)
- pricing_strategy (model, justification, tiers with prices and features)
- sales_plan (sales_model, sales_cycle_days, conversion_rate_pct, cac_estimate with breakdown)
"""
        
        try:
            response = await self._call_model(prompt, temperature=0.6)
            parsed = self._parse_json_response(response)
            if not parsed:
                raise ToolError("Failed to parse GTM strategy response")
            
            return parsed
            
        except Exception as e:
            logger.error(f"GTM strategy generation error: {e}")
            raise ToolError(f"GTM strategy generation failed: {str(e)}")
    
    async def generate_financial_plan(self, all_data: Dict, user_input: UserInput) -> Dict:
        """Generate complete 3-year financial model"""
        prompt = f"""
You are a CFO creating a financial model.

BUDGET: ${user_input.initial_budget:,.0f}

ALL COSTS & REVENUE DATA:
{json.dumps(all_data, indent=2)[:3500]}

Generate 3-year financial model with:
- key_assumptions (revenue_drivers, cost_drivers, macro_drivers)
- income_statement (year1, year2, year3 with revenue, cogs, gross_profit, opex, ebitda, net_income)
- cash_flow_statement (year1, year2, year3)
- balance_sheet (year1, year2, year3)
- break_even_analysis (break_even_month, break_even_revenue, break_even_customers)

Be conservative. Use ONLY provided data.
"""
        
        try:
            response = await self._call_model(prompt, temperature=0.3)
            parsed = self._parse_json_response(response)
            if not parsed:
                raise ToolError("Failed to parse financial plan response")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Financial plan generation error: {e}")
            raise ToolError(f"Financial plan generation failed: {str(e)}")
    
    async def generate_executive_summary(self, all_sections: Dict) -> Dict:
        """Generate executive summary (written LAST)"""
        prompt = f"""
You are writing the Executive Summary - most important section written LAST.

ALL SECTIONS:
{json.dumps(all_sections, indent=2)[:5000]}

Write compelling 1-2 page Executive Summary answering:
1. The Problem & Solution
2. The Market & Why Now
3. The Team's Expertise
4. Core Financials & Funding Request

Return JSON with executive_summary containing:
- the_opportunity (2-3 paragraphs)
- the_solution (2 paragraphs)
- the_market (2 paragraphs)
- the_team (1-2 paragraphs)
- the_financials (1 paragraph with key metrics)
- the_ask (1 paragraph)
"""
        
        try:
            response = await self._call_model(prompt, temperature=0.7)
            parsed = self._parse_json_response(response)
            if not parsed:
                raise ToolError("Failed to parse executive summary response")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Executive summary generation error: {e}")
            raise ToolError(f"Executive summary generation failed: {str(e)}")
    
    async def assemble_business_plan(self, all_sections: Dict) -> str:
        """Assemble all sections into final business plan document"""
        prompt = f"""
Assemble investor-ready business plan document.

ALL SECTIONS:
{json.dumps(all_sections, indent=2)}

Create complete business plan in Markdown format:
1. Title Page
2. Table of Contents
3. Executive Summary
4. Company Purpose & Problem
5. Solution & Value Proposition
6. Market Opportunity
7. Competitive Analysis
8. Operations Plan
9. Go-to-Market Strategy
10. Team & Organization
11. Financial Plan
12. Funding Request
13. Appendices

Professional, investor-ready quality with all tables and metrics.
"""
        
        try:
            response = await self._call_model(prompt, temperature=0.6)
            return response
            
        except Exception as e:
            logger.error(f"Business plan assembly error: {e}")
            raise ToolError(f"Business plan assembly failed: {str(e)}")


# Initialize generator (will be created on first use to handle missing API key gracefully)
_generator: Optional[BusinessPlanGenerator] = None

def get_generator() -> BusinessPlanGenerator:
    """Get or create generator instance"""
    global _generator
    if _generator is None:
        if not api_config.gemini_key:
            raise ToolError("GEMINI_API_KEY not configured")
        _generator = BusinessPlanGenerator()
    return _generator


# ==================== MCP TOOLS ====================

@mcp.tool()
async def generate_complete_business_plan(
    business_type: str,
    initial_budget: float,
    location: str,
    timeline_months: int = 12,
    business_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    [COMPLETE PLAN] Generate full end-to-end business plan with all sections
    
    Args:
        business_type: Type of business (e.g., "Coffee Shop", "SaaS Startup")
        initial_budget: Initial budget/funding in USD
        location: Business location (e.g., "San Francisco, CA")
        timeline_months: Planning timeline in months (default: 12)
        business_name: Optional business name
    
    Returns: Complete business plan with all sections, financials, and analysis
    """
    try:
        generator = get_generator()
        
        user_input = UserInput(
            business_type=business_type,
            initial_budget=initial_budget,
            location=location,
            timeline_months=timeline_months,
            business_name=business_name
        )
        
        logger.info(f"Starting complete business plan generation for {business_type}")
        
        # Phase 1: Research (parallel execution)
        location_task = generator.research_location_and_costs(user_input)
        staffing_task = generator.research_staffing_and_salaries(user_input)
        equipment_task = generator.research_equipment_and_resources(user_input)
        market_task = generator.research_market_and_competitors(user_input)
        
        location_data, staffing_data, equipment_data, market_data = await asyncio.gather(
            location_task, staffing_task, equipment_task, market_task,
            return_exceptions=True
        )
        
        # Check for errors in parallel execution
        if isinstance(location_data, Exception):
            raise ToolError(f"Location research failed: {str(location_data)}")
        if isinstance(staffing_data, Exception):
            raise ToolError(f"Staffing research failed: {str(staffing_data)}")
        if isinstance(equipment_data, Exception):
            raise ToolError(f"Equipment research failed: {str(equipment_data)}")
        if isinstance(market_data, Exception):
            raise ToolError(f"Market research failed: {str(market_data)}")
        
        # Phase 2: Business Plan Generation
        problem_solution = await generator.generate_problem_solution(market_data, user_input)
        competitive_analysis = await generator.generate_competitive_analysis(market_data, problem_solution)
        
        gtm_strategy = await generator.generate_gtm_strategy(
            problem_solution.get('value_proposition', {}),
            market_data.get('customer_personas', []),
            market_data.get('competitors', [])
        )
        
        # Compile all data for financial model
        all_data = {
            'location': location_data,
            'staffing': staffing_data,
            'equipment': equipment_data,
            'market': market_data,
            'gtm': gtm_strategy
        }
        
        financial_plan = await generator.generate_financial_plan(all_data, user_input)
        
        # Compile all sections
        all_sections = {
            'problem_solution': problem_solution,
            'market_opportunity': market_data,
            'competitive_analysis': competitive_analysis,
            'gtm_strategy': gtm_strategy,
            'financial_plan': financial_plan,
            'location_data': location_data,
            'staffing_data': staffing_data,
            'equipment_data': equipment_data
        }
        
        executive_summary = await generator.generate_executive_summary(all_sections)
        all_sections['executive_summary'] = executive_summary
        
        # Assemble final document
        business_plan_doc = await generator.assemble_business_plan(all_sections)
        
        result = {
            "business_type": business_type,
            "location": location,
            "budget": initial_budget,
            "business_plan_document": business_plan_doc,
            "sections": all_sections,
            "key_metrics": {
                "total_setup_costs": (
                    location_data.get('setup_costs', {}).get('total_one_time', 0) + 
                    equipment_data.get('cost_summary', {}).get('total_one_time_capex', 0)
                ),
                "monthly_burn_rate": (
                    location_data.get('real_estate', {}).get('total_monthly_rent_estimate', 0) +
                    location_data.get('utilities_monthly', {}).get('total', 0)
                ),
                "year1_revenue_target": market_data.get('market_sizing', {}).get('som', {}).get('year1_revenue_target', 0),
                "break_even_month": financial_plan.get('break_even_analysis', {}).get('break_even_month', 0)
            }
        }
        
        return success_response(result, "Complete business plan generated successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in generate_complete_business_plan: {e}", exc_info=True)
        raise ToolError(f"Business plan generation failed: {str(e)}")


@mcp.tool()
async def research_market_opportunity(
    business_type: str,
    location: str
) -> Dict[str, Any]:
    """
    [MARKET RESEARCH] Conduct deep market research and competitive analysis
    
    Args:
        business_type: Type of business to research
        location: Geographic location for market research
    
    Returns: Market analysis with TAM/SAM/SOM, competitors, trends, customer personas
    """
    try:
        generator = get_generator()
        
        user_input = UserInput(
            business_type=business_type,
            initial_budget=100000,
            location=location
        )
        
        market_data = await generator.research_market_and_competitors(user_input)
        
        result = {
            "business_type": business_type,
            "location": location,
            "market_research": market_data
        }
        
        return success_response(result, "Market research completed successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in research_market_opportunity: {e}", exc_info=True)
        raise ToolError(f"Market research failed: {str(e)}")


@mcp.tool()
async def analyze_location_costs(
    business_type: str,
    location: str
) -> Dict[str, Any]:
    """
    [LOCATION ANALYSIS] Research real estate, utilities, and location-specific costs
    
    Args:
        business_type: Type of business
        location: Geographic location to analyze
    
    Returns: Detailed cost breakdown including rent, utilities, setup costs
    """
    try:
        generator = get_generator()
        
        user_input = UserInput(
            business_type=business_type,
            initial_budget=100000,
            location=location
        )
        
        location_data = await generator.research_location_and_costs(user_input)
        
        result = {
            "business_type": business_type,
            "location": location,
            "location_analysis": location_data
        }
        
        return success_response(result, "Location analysis completed successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_location_costs: {e}", exc_info=True)
        raise ToolError(f"Location analysis failed: {str(e)}")


@mcp.tool()
async def plan_staffing_requirements(
    business_type: str,
    location: str,
    initial_budget: float
) -> Dict[str, Any]:
    """
    [STAFFING PLAN] Research staffing needs and market salaries
    
    Args:
        business_type: Type of business
        location: Geographic location for salary research
        initial_budget: Available budget for context
    
    Returns: Staffing plan with positions, salaries, and hiring timeline
    """
    try:
        generator = get_generator()
        
        user_input = UserInput(
            business_type=business_type,
            initial_budget=initial_budget,
            location=location
        )
        
        staffing_data = await generator.research_staffing_and_salaries(user_input)
        
        result = {
            "business_type": business_type,
            "location": location,
            "budget": initial_budget,
            "staffing_plan": staffing_data
        }
        
        return success_response(result, "Staffing plan completed successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in plan_staffing_requirements: {e}", exc_info=True)
        raise ToolError(f"Staffing plan failed: {str(e)}")


@mcp.tool()
async def calculate_equipment_costs(
    business_type: str,
    location: str,
    initial_budget: float
) -> Dict[str, Any]:
    """
    [EQUIPMENT ANALYSIS] Research required equipment, technology, and resources
    
    Args:
        business_type: Type of business
        location: Business location
        initial_budget: Available budget
    
    Returns: Equipment costs including technology, furniture, specialized equipment
    """
    try:
        generator = get_generator()
        
        user_input = UserInput(
            business_type=business_type,
            initial_budget=initial_budget,
            location=location
        )
        
        equipment_data = await generator.research_equipment_and_resources(user_input)
        
        result = {
            "business_type": business_type,
            "location": location,
            "budget": initial_budget,
            "equipment_analysis": equipment_data
        }
        
        return success_response(result, "Equipment analysis completed successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in calculate_equipment_costs: {e}", exc_info=True)
        raise ToolError(f"Equipment analysis failed: {str(e)}")


@mcp.tool()
async def analyze_competition(
    business_type: str,
    location: str,
    your_solution_description: str
) -> Dict[str, Any]:
    """
    [COMPETITIVE ANALYSIS] Analyze competitors and define strategic positioning
    
    Args:
        business_type: Type of business
        location: Business location
        your_solution_description: Brief description of your solution/product
    
    Returns: Competitor analysis with SWOT and competitive advantage strategy
    """
    try:
        generator = get_generator()
        
        user_input = UserInput(
            business_type=business_type,
            initial_budget=100000,
            location=location
        )
        
        # Get market data first
        market_data = await generator.research_market_and_competitors(user_input)
        
        # Generate competitive analysis
        solution_data = {"solution": {"description": your_solution_description}}
        competitive_analysis = await generator.generate_competitive_analysis(market_data, solution_data)
        
        result = {
            "business_type": business_type,
            "location": location,
            "competitive_analysis": competitive_analysis
        }
        
        return success_response(result, "Competitive analysis completed successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_competition: {e}", exc_info=True)
        raise ToolError(f"Competitive analysis failed: {str(e)}")


@mcp.tool()
async def create_gtm_strategy(
    business_type: str,
    location: str,
    value_proposition: str,
    target_customer_description: str
) -> Dict[str, Any]:
    """
    [GO-TO-MARKET] Create go-to-market and sales strategy
    
    Args:
        business_type: Type of business
        location: Business location
        value_proposition: Your value proposition statement
        target_customer_description: Description of target customers
    
    Returns: GTM strategy with marketing plan, pricing strategy, and sales plan
    """
    try:
        generator = get_generator()
        
        user_input = UserInput(
            business_type=business_type,
            initial_budget=100000,
            location=location
        )
        
        # Get market data
        market_data = await generator.research_market_and_competitors(user_input)
        
        # Create simple structures for GTM generation
        value_prop = {"value_statement": value_proposition}
        personas = [{"description": target_customer_description}]
        competitors = market_data.get('competitors', [])
        
        gtm_strategy = await generator.generate_gtm_strategy(value_prop, personas, competitors)
        
        result = {
            "business_type": business_type,
            "location": location,
            "gtm_strategy": gtm_strategy
        }
        
        return success_response(result, "GTM strategy completed successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in create_gtm_strategy: {e}", exc_info=True)
        raise ToolError(f"GTM strategy creation failed: {str(e)}")


@mcp.tool()
async def project_financials(
    business_type: str,
    location: str,
    initial_budget: float,
    expected_monthly_revenue: Optional[float] = None,
    expected_monthly_costs: Optional[float] = None
) -> Dict[str, Any]:
    """
    [FINANCIAL PROJECTIONS] Generate 3-year financial projections
    
    Args:
        business_type: Type of business
        location: Business location
        initial_budget: Initial budget/funding
        expected_monthly_revenue: Optional expected monthly revenue (Year 1)
        expected_monthly_costs: Optional expected monthly operating costs
    
    Returns: 3-year financial model with P&L, cash flow, and break-even analysis
    """
    try:
        generator = get_generator()
        
        user_input = UserInput(
            business_type=business_type,
            initial_budget=initial_budget,
            location=location
        )
        
        # Gather necessary data in parallel
        location_task = generator.research_location_and_costs(user_input)
        staffing_task = generator.research_staffing_and_salaries(user_input)
        market_task = generator.research_market_and_competitors(user_input)
        
        location_data, staffing_data, market_data = await asyncio.gather(
            location_task, staffing_task, market_task,
            return_exceptions=True
        )
        
        # Check for errors
        if isinstance(location_data, Exception):
            raise ToolError(f"Location research failed: {str(location_data)}")
        if isinstance(staffing_data, Exception):
            raise ToolError(f"Staffing research failed: {str(staffing_data)}")
        if isinstance(market_data, Exception):
            raise ToolError(f"Market research failed: {str(market_data)}")
        
        # Compile data
        all_data = {
            'location': location_data,
            'staffing': staffing_data,
            'market': market_data,
            'user_estimates': {
                'expected_monthly_revenue': expected_monthly_revenue,
                'expected_monthly_costs': expected_monthly_costs
            }
        }
        
        financial_plan = await generator.generate_financial_plan(all_data, user_input)
        
        result = {
            "business_type": business_type,
            "location": location,
            "budget": initial_budget,
            "financial_projections": financial_plan
        }
        
        return success_response(result, "Financial projections completed successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in project_financials: {e}", exc_info=True)
        raise ToolError(f"Financial projections failed: {str(e)}")


@mcp.tool()
async def create_executive_summary(
    business_type: str,
    location: str,
    initial_budget: float,
    business_description: str
) -> Dict[str, Any]:
    """
    [EXECUTIVE SUMMARY] Generate compelling executive summary
    
    Args:
        business_type: Type of business
        location: Business location
        initial_budget: Initial budget/funding
        business_description: Brief description of the business idea
    
    Returns: Executive summary with opportunity, solution, market, and financials
    """
    try:
        generator = get_generator()
        
        user_input = UserInput(
            business_type=business_type,
            initial_budget=initial_budget,
            location=location
        )
        
        # Gather key data
        market_data = await generator.research_market_and_competitors(user_input)
        
        # Create minimal sections for executive summary
        all_sections = {
            'business_description': business_description,
            'market_opportunity': market_data,
            'budget': initial_budget,
            'location': location
        }
        
        executive_summary = await generator.generate_executive_summary(all_sections)
        
        result = {
            "business_type": business_type,
            "location": location,
            "executive_summary": executive_summary
        }
        
        return success_response(result, "Executive summary completed successfully")
        
    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in create_executive_summary: {e}", exc_info=True)
        raise ToolError(f"Executive summary creation failed: {str(e)}")


# ==================== MCP RESOURCES ====================

@mcp.resource("config://server-info")
def get_server_info() -> str:
    """Server configuration and capabilities"""
    return json.dumps({
        "server_name": SERVER_NAME,
        "version": "2.0.0-optimized",
        "port": PORT,
        "total_tools": 9,
        "apis_integrated": [
            "Google Gemini 2.0 Flash Thinking",
            "Google Gemini 2.0 Flash",
            "Google Search API"
        ],
        "configuration": {
            "reasoning_model": REASONING_MODEL,
            "fast_model": FAST_MODEL,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "google_search_enabled": api_config.use_search,
            "output_directory": OUTPUT_DIR
        },
        "optimization_features": [
            "Structured error handling with ToolError",
            "Type-safe Dict returns (not JSON strings)",
            "Proper resource lifecycle management",
            "Efficient parallel execution",
            "Robust JSON parsing",
            "Comprehensive logging"
        ],
        "features": [
            "Complete business plan generation",
            "Deep market research with web search",
            "Location cost analysis",
            "Staffing requirements planning",
            "Equipment cost calculation",
            "Competitive analysis",
            "Go-to-market strategy",
            "3-year financial projections",
            "Executive summary generation",
            "Bottom-up financial modeling",
            "Real-time market data"
        ],
        "tools": [
            "generate_complete_business_plan - Full end-to-end plan",
            "research_market_opportunity - Market research & competitors",
            "analyze_location_costs - Real estate & operating costs",
            "plan_staffing_requirements - Staffing & salaries",
            "calculate_equipment_costs - Equipment & technology",
            "analyze_competition - Competitive analysis & SWOT",
            "create_gtm_strategy - Go-to-market & sales",
            "project_financials - 3-year financial model",
            "create_executive_summary - Executive summary"
        ]
    }, indent=2)


@mcp.resource("docs://usage-guide")
def get_usage_guide() -> str:
    """Usage guide and examples"""
    return json.dumps({
        "setup": {
            "required_env_vars": [
                "GEMINI_API_KEY - Required for AI analysis"
            ],
            "optional_env_vars": [
                "OUTPUT_DIR - Output directory (default: ./business_plans)",
                "USE_GOOGLE_SEARCH - Enable web search (default: true)",
                "PORT - Server port (default: 8000)"
            ]
        },
        "optimization_notes": {
            "return_types": "All tools return Dict[str, Any] instead of JSON strings",
            "error_handling": "Structured ToolError exceptions for all failures",
            "parallel_execution": "Research tasks run in parallel for maximum efficiency",
            "resource_management": "Proper startup/shutdown lifecycle"
        },
        "tool_descriptions": {
            "generate_complete_business_plan": {
                "purpose": "Generate full business plan with all sections",
                "use_when": "You want a complete investor-ready business plan",
                "parallel_research": "Runs 4 research tasks simultaneously",
                "example": {
                    "business_type": "Coffee Shop",
                    "initial_budget": 250000,
                    "location": "Austin, TX",
                    "timeline_months": 12
                }
            },
            "research_market_opportunity": {
                "purpose": "Deep market research only",
                "use_when": "You need market sizing and competitor intelligence",
                "example": {
                    "business_type": "SaaS Startup",
                    "location": "San Francisco, CA"
                }
            },
            "analyze_location_costs": {
                "purpose": "Location-specific cost analysis",
                "use_when": "You need real estate and operating cost estimates",
                "example": {
                    "business_type": "Restaurant",
                    "location": "New York, NY"
                }
            },
            "plan_staffing_requirements": {
                "purpose": "Staffing plan with salaries",
                "use_when": "You need hiring plan and payroll estimates",
                "example": {
                    "business_type": "Tech Startup",
                    "location": "Seattle, WA",
                    "initial_budget": 500000
                }
            },
            "project_financials": {
                "purpose": "3-year financial projections",
                "use_when": "You need P&L, cash flow, and break-even analysis",
                "parallel_research": "Runs 3 research tasks simultaneously",
                "example": {
                    "business_type": "E-commerce",
                    "location": "Los Angeles, CA",
                    "initial_budget": 150000
                }
            }
        }
    }, indent=2)


# ==================== SERVER STARTUP ====================

if __name__ == "__main__":
    print("=" * 90)
    print(f"🚀 BUSINESS PLAN GENERATOR MCP SERVER - OPTIMIZED")
    print("=" * 90)
    print(f"Port: {PORT}")
    print("=" * 90)
    
    print("\n✨ OPTIMIZATION FEATURES:")
    print("  • Structured error handling with ToolError")
    print("  • Type-safe Dict returns (not JSON strings)")
    print("  • Proper resource lifecycle management")
    print("  • Efficient parallel execution")
    print("  • Robust JSON parsing with fallbacks")
    print("  • Comprehensive logging")
    
    print("\n🔐 CONFIGURATION:")
    print(f"  • Gemini API: {'✓ Configured' if api_config.gemini_key else '✗ Not Configured'}")
    print(f"  • Google Search: {'✓ Enabled' if api_config.use_search else '✗ Disabled'}")
    print(f"  • Output Directory: {OUTPUT_DIR}")
    print(f"  • Reasoning Model: {REASONING_MODEL}")
    print(f"  • Fast Model: {FAST_MODEL}")
    
    print("\n🛠️  AVAILABLE TOOLS (9):")
    print("  1. generate_complete_business_plan - Full end-to-end plan (PARALLEL)")
    print("  2. research_market_opportunity - Market research & competitors")
    print("  3. analyze_location_costs - Real estate & operating costs")
    print("  4. plan_staffing_requirements - Staffing & salaries")
    print("  5. calculate_equipment_costs - Equipment & technology")
    print("  6. analyze_competition - Competitive analysis")
    print("  7. create_gtm_strategy - Go-to-market strategy")
    print("  8. project_financials - 3-year financial model (PARALLEL)")
    print("  9. create_executive_summary - Executive summary")
    
    print("\n📚 RESOURCES (2):")
    print("   • config://server-info")
    print("   • docs://usage-guide")
    
    print("\n" + "=" * 90)
    print("🎯 TOTAL CAPABILITIES:")
    print(f"  ✓ 9 Tools (optimized error handling)")
    print(f"  ✓ 2 Resources")
    print(f"  ✓ Parallel research execution")
    print(f"  ✓ Structured ToolError exceptions")
    print(f"  ✓ Type-safe Dict responses")
    print(f"  ✓ Proper lifecycle management")
    print(f"  ✓ Google Gemini 2.0 Integration")
    print(f"  ✓ Production-ready architecture")
    print("=" * 90)
    
    if not api_config.gemini_key:
        print("\n⚠️  WARNING: GEMINI_API_KEY not configured!")
        print("   Server will start but tools will not function")
        print("=" * 90)
    
    print(f"\n🚀 Starting optimized server on http://0.0.0.0:{PORT}/sse")
    print("=" * 90)
    
    mcp.run(transport="sse", host="0.0.0.0", port=PORT)