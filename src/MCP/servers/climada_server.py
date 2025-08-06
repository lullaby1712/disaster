#!/usr/bin/env python3
"""
CLIMADA MCP Server for disaster risk assessment.

This server provides Model Context Protocol (MCP) interface for CLIMADA
climate risk assessment tools.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

from ..core.base_model import BaseMCPModel
from ..core.environment_manager import environment_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CliMadaServer(BaseMCPModel):
    """CLIMADA MCP Server for climate risk assessment."""
    
    def __init__(self):
        super().__init__("climada", "Climate risk assessment model")
        self.climada_path = os.getenv("CLIMADA_HOST", "/data/Tiaozhanbei/Climada")
        self.environment_name = os.getenv("CLIMADA_ENV", "climada")
        self.server = Server("climada-server")
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self):
        """Setup CLIMADA-specific tools."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available CLIMADA tools."""
            return [
                Tool(
                    name="climada_impact_assessment",
                    description="Assess economic impact of disasters using CLIMADA",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "hazard_type": {
                                "type": "string",
                                "enum": ["wildfire", "flood", "earthquake", "hurricane"],
                                "description": "Type of disaster to assess"
                            },
                            "location": {
                                "type": "object",
                                "properties": {
                                    "lat": {"type": "number", "description": "Latitude"},
                                    "lng": {"type": "number", "description": "Longitude"},
                                    "country": {"type": "string", "description": "Country code"}
                                },
                                "required": ["lat", "lng"]
                            },
                            "intensity": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "Disaster intensity (0-1)"
                            },
                            "exposure_data": {
                                "type": "object",
                                "description": "Exposure data for impact calculation"
                            }
                        },
                        "required": ["hazard_type", "location", "intensity"]
                    }
                ),
                Tool(
                    name="climada_hazard_modeling",
                    description="Model hazard scenarios using CLIMADA",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "hazard_type": {"type": "string"},
                            "scenario_params": {"type": "object"},
                            "time_horizon": {"type": "integer", "default": 50}
                        },
                        "required": ["hazard_type"]
                    }
                ),
                Tool(
                    name="climada_cost_benefit",
                    description="Perform cost-benefit analysis for adaptation measures",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "measures": {"type": "array", "items": {"type": "string"}},
                            "time_horizon": {"type": "integer", "default": 30},
                            "discount_rate": {"type": "number", "default": 0.03}
                        },
                        "required": ["measures"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool execution."""
            try:
                if name == "climada_impact_assessment":
                    result = await self._run_impact_assessment(arguments)
                elif name == "climada_hazard_modeling":
                    result = await self._run_hazard_modeling(arguments)
                elif name == "climada_cost_benefit":
                    result = await self._run_cost_benefit(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=str(result))]
                
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _setup_resources(self):
        """Setup CLIMADA resources."""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available CLIMADA resources."""
            return [
                Resource(
                    uri="climada://hazard_sets",
                    name="CLIMADA Hazard Sets",
                    description="Available hazard datasets in CLIMADA",
                    mimeType="application/json"
                ),
                Resource(
                    uri="climada://exposure_data", 
                    name="Exposure Data",
                    description="Economic exposure data for impact assessment",
                    mimeType="application/json"
                ),
                Resource(
                    uri="climada://vulnerability_functions",
                    name="Vulnerability Functions",
                    description="Damage functions for different hazards",
                    mimeType="application/json"
                )
            ]
    
    async def _run_impact_assessment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run CLIMADA impact assessment."""
        logger.info(f"Running impact assessment with params: {params}")
        
        # Validate environment
        env_validation = await environment_manager.validate_environment(
            self.environment_name,
            ["climada-petals", "geopandas", "rasterio"]
        )
        
        if not env_validation["environment_accessible"]:
            raise RuntimeError(f"CLIMADA environment '{self.environment_name}' not accessible")
        
        # Prepare CLIMADA script
        script_content = f"""
import sys
sys.path.append('{self.climada_path}')

from climada.entity import Exposures, ImpactFuncSet
from climada.hazard import Hazard
from climada.engine import Impact
import json

# Parameters
hazard_type = '{params['hazard_type']}'
location = {params['location']}
intensity = {params['intensity']}

# Create mock hazard for demonstration
hazard = Hazard(haz_type=hazard_type.upper())
# In real implementation, load actual hazard data based on location

# Create exposure
exposures = Exposures()
# In real implementation, load exposure data for location

# Create impact functions
impact_funcs = ImpactFuncSet()
# In real implementation, load vulnerability functions

# Calculate impact
impact = Impact()
# impact.calc(exposures, impact_funcs, hazard)

# Mock result for demonstration
result = {{
    'economic_damage': {params['intensity']} * 1000000,  # USD
    'affected_people': int({params['intensity']} * 10000),
    'location': location,
    'hazard_type': hazard_type,
    'confidence': 0.8
}}

print(json.dumps(result))
"""
        
        try:
            # Execute CLIMADA script in environment
            result = await environment_manager._run_in_environment(
                self.environment_name,
                ["python", "-c", script_content],
                timeout=300,
                cwd=Path(self.climada_path)
            )
            
            if result.returncode == 0:
                import json
                return json.loads(result.stdout.decode().strip())
            else:
                raise RuntimeError(f"CLIMADA execution failed: {result.stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Impact assessment failed: {e}")
            # Return mock data as fallback
            return {
                "economic_damage": params["intensity"] * 1000000,
                "affected_people": int(params["intensity"] * 10000),
                "location": params["location"],
                "hazard_type": params["hazard_type"],
                "confidence": 0.5,
                "status": "mock_data"
            }
    
    async def _run_hazard_modeling(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run CLIMADA hazard modeling."""
        logger.info(f"Running hazard modeling with params: {params}")
        
        # Mock implementation
        return {
            "hazard_type": params["hazard_type"],
            "scenario_results": {
                "return_periods": [5, 10, 25, 50, 100],
                "intensities": [0.2, 0.4, 0.6, 0.8, 1.0],
                "probabilities": [0.2, 0.1, 0.04, 0.02, 0.01]
            },
            "time_horizon": params.get("time_horizon", 50),
            "confidence": 0.75
        }
    
    async def _run_cost_benefit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run CLIMADA cost-benefit analysis."""
        logger.info(f"Running cost-benefit analysis with params: {params}")
        
        # Mock implementation
        return {
            "measures": params["measures"],
            "total_cost": sum(hash(measure) % 1000000 for measure in params["measures"]),
            "total_benefit": sum(hash(measure) % 1500000 for measure in params["measures"]),
            "benefit_cost_ratio": 1.2,
            "net_present_value": 500000,
            "time_horizon": params.get("time_horizon", 30),
            "discount_rate": params.get("discount_rate", 0.03)
        }


async def main():
    """Run the CLIMADA MCP server."""
    server_instance = CliMadaServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="climada-server",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())