"""
Weather ADK Agent Package
Exports the root_agent for Cloud Run deployment
"""
from . import agent

# This allows Cloud Run to find the agent
__all__ = ['agent']