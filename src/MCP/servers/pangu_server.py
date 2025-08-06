#!/usr/bin/env python3
"""
Pangu Weather MCP Server for weather forecasting.

This server provides Model Context Protocol (MCP) interface for Pangu Weather
AI-based weather prediction model.
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


class PanguServer(BaseMCPModel):
    """Pangu Weather MCP Server for AI weather forecasting."""
    
    def __init__(self):
        super().__init__("pangu", "AI-based weather forecasting model")
        self.pangu_path = os.getenv("PANGU_HOST", "/data/Tiaozhanbei/Pangu_weather")
        self.environment_name = os.getenv("PANGU_ENV", "pangu")
        self.server = Server("pangu-server")
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self):
        """Setup Pangu Weather tools."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="pangu_forecast",
                    description="Generate weather forecast using Pangu Weather model",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "object", 
                                "properties": {
                                    "lat": {"type": "number"},
                                    "lng": {"type": "number"}
                                },
                                "required": ["lat", "lng"]
                            },
                            "forecast_hours": {
                                "type": "integer",
                                "minimum": 6,
                                "maximum": 168,
                                "default": 120
                            },
                            "variables": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["temperature", "humidity", "wind", "precipitation", "pressure"]
                                },
                                "default": ["temperature", "humidity", "wind", "precipitation"]
                            }
                        },
                        "required": ["location"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "pangu_forecast":
                    result = await self._run_forecast(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _setup_resources(self):
        """Setup Pangu Weather resources."""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            return [
                Resource(
                    uri="pangu://model_weights",
                    name="Pangu Model Weights",
                    description="Pre-trained model weights for different forecast horizons",
                    mimeType="application/json"
                )
            ]
    
    async def _run_forecast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run Pangu Weather forecast."""
        logger.info(f"Running Pangu forecast with params: {params}")
        
        location = params["location"]
        forecast_hours = params.get("forecast_hours", 120)
        
        # Mock forecast results
        forecast_data = {
            "location": location,
            "forecast_hours": forecast_hours,
            "issue_time": "2024-01-15T00:00:00Z",
            "forecast": {
                "temperature": [22.5, 24.1, 26.8, 25.3, 23.7],  # °C
                "humidity": [65, 58, 72, 69, 61],  # %
                "wind_speed": [12.3, 15.7, 8.9, 11.2, 14.5],  # km/h
                "wind_direction": [225, 230, 180, 200, 215],  # degrees
                "precipitation": [0, 2.3, 15.7, 8.2, 0],  # mm
                "pressure": [1013.2, 1015.8, 1009.4, 1011.6, 1014.3]  # hPa
            },
            "confidence": 0.89,
            "model_version": "pangu-weather-v1.0"
        }
        
        return forecast_data


async def main():
    """Run the Pangu Weather MCP server."""
    server_instance = PanguServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="pangu-server",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())