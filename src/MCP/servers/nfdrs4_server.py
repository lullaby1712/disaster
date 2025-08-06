#!/usr/bin/env python3
"""
NFDRS4 MCP Server for fire danger rating.

This server provides Model Context Protocol (MCP) interface for NFDRS4
National Fire Danger Rating System.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

from ..core.base_model import BaseMCPModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NFDRS4Server(BaseMCPModel):
    """NFDRS4 MCP Server for fire danger rating."""
    
    def __init__(self):
        super().__init__("nfdrs4", "National Fire Danger Rating System v4")
        self.nfdrs4_path = os.getenv("NFDRS4_HOST", "/data/Tiaozhanbei/NFDRS4")
        self.environment_name = os.getenv("NFDRS4_ENV", "nfdrs4")
        self.server = Server("nfdrs4-server")
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self):
        """Setup NFDRS4-specific tools."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="nfdrs4_fire_danger",
                    description="Calculate fire danger rating using NFDRS4",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "weather_data": {
                                "type": "object",
                                "properties": {
                                    "temperature": {"type": "number"},
                                    "humidity": {"type": "number"},
                                    "wind_speed": {"type": "number"},
                                    "precipitation": {"type": "number"}
                                },
                                "required": ["temperature", "humidity", "wind_speed"]
                            },
                            "fuel_model": {
                                "type": "string",
                                "enum": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
                                "default": "G"
                            },
                            "slope": {"type": "number", "default": 0},
                            "aspect": {"type": "number", "default": 180}
                        },
                        "required": ["weather_data"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "nfdrs4_fire_danger":
                    result = await self._calculate_fire_danger(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _setup_resources(self):
        """Setup NFDRS4 resources."""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            return [
                Resource(
                    uri="nfdrs4://fuel_models",
                    name="NFDRS4 Fuel Models",
                    description="Standard fuel models used in NFDRS4 calculations",
                    mimeType="application/json"
                )
            ]
    
    async def _calculate_fire_danger(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate fire danger rating."""
        logger.info(f"Calculating fire danger with params: {params}")
        
        weather = params["weather_data"]
        fuel_model = params.get("fuel_model", "G")
        
        # Mock fire danger calculation
        # In real implementation, this would use NFDRS4 algorithms
        danger_rating = min(100, max(0, 
            (weather["temperature"] * 0.5) + 
            ((100 - weather["humidity"]) * 0.3) + 
            (weather["wind_speed"] * 0.2)
        ))
        
        return {
            "fire_danger_rating": int(danger_rating),
            "danger_class": self._get_danger_class(danger_rating),
            "fuel_model": fuel_model,
            "components": {
                "spread_component": int(danger_rating * 0.8),
                "energy_release_component": int(danger_rating * 0.9),
                "burning_index": int(danger_rating * 0.7),
                "ignition_component": int(danger_rating * 0.6)
            },
            "weather_inputs": weather,
            "recommendations": self._get_recommendations(danger_rating)
        }
    
    def _get_danger_class(self, rating: float) -> str:
        """Get danger class from rating."""
        if rating < 20:
            return "LOW"
        elif rating < 40:
            return "MODERATE"
        elif rating < 60:
            return "HIGH"
        elif rating < 80:
            return "VERY_HIGH"
        else:
            return "EXTREME"
    
    def _get_recommendations(self, rating: float) -> List[str]:
        """Get recommendations based on fire danger rating."""
        if rating < 20:
            return ["Normal fire precautions"]
        elif rating < 40:
            return ["Increased awareness", "Monitor conditions"]
        elif rating < 60:
            return ["High alert", "Restrict outdoor burning", "Prepare resources"]
        elif rating < 80:
            return ["Very high alert", "Ban outdoor burning", "Pre-position resources"]
        else:
            return ["Extreme alert", "Total fire ban", "Maximum preparedness"]


async def main():
    """Run the NFDRS4 MCP server."""
    server_instance = NFDRS4Server()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="nfdrs4-server",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())