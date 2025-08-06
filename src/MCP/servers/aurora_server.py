#!/usr/bin/env python3
"""
Aurora MCP Server for atmospheric modeling.

This server provides Model Context Protocol (MCP) interface for Aurora
atmospheric foundation model.
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


class AuroraServer(BaseMCPModel):
    """Aurora MCP Server for atmospheric modeling."""
    
    def __init__(self):
        super().__init__("aurora", "Atmospheric foundation model")
        self.aurora_path = os.getenv("AURORA_HOST", "/data/Tiaozhanbei/aurora-main")
        self.environment_name = os.getenv("AURORA_ENV", "aurora")
        self.server = Server("aurora-server")
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self):
        """Setup Aurora-specific tools."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="aurora_forecast",
                    description="Generate atmospheric forecast using Aurora model",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "region": {
                                "type": "object",
                                "properties": {
                                    "north": {"type": "number"},
                                    "south": {"type": "number"},
                                    "east": {"type": "number"},
                                    "west": {"type": "number"}
                                }
                            },
                            "forecast_steps": {"type": "integer", "default": 40},
                            "resolution": {"type": "string", "default": "0.1deg"}
                        },
                        "required": ["region"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "aurora_forecast":
                    result = await self._run_forecast(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _setup_resources(self):
        """Setup Aurora resources."""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            return [
                Resource(
                    uri="aurora://model_checkpoints",
                    name="Aurora Model Checkpoints",
                    description="Pre-trained Aurora model checkpoints",
                    mimeType="application/json"
                )
            ]
    
    async def _run_forecast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run Aurora atmospheric forecast."""
        logger.info(f"Running Aurora forecast with params: {params}")
        
        # Mock forecast results
        return {
            "region": params["region"],
            "forecast_steps": params.get("forecast_steps", 40),
            "resolution": params.get("resolution", "0.1deg"),
            "atmospheric_variables": {
                "temperature_2m": "forecast_t2m.nc",
                "surface_pressure": "forecast_sp.nc",
                "wind_10m": "forecast_wind10m.nc",
                "total_precipitation": "forecast_tp.nc"
            },
            "model_confidence": 0.92,
            "processing_time": 245.8,  # seconds
            "status": "completed"
        }


async def main():
    """Run the Aurora MCP server."""
    server_instance = AuroraServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="aurora-server",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())