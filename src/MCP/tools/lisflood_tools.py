"""
Lisflood Tools for MCP

LangGraph-compatible tool definitions for Lisflood hydrological modeling.
Based on analysis of Lisflood's core functionality.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type, Union

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Parameter models for type validation
class FloodSimulationParams(BaseModel):
    """Parameters for flood simulation."""
    settings_file: str = Field(description="Path to Lisflood settings XML file")
    start_date: str = Field(description="Simulation start date (YYYY-MM-DD)")
    end_date: str = Field(description="Simulation end date (YYYY-MM-DD)")
    time_step: Optional[str] = Field("daily", description="Time step ('daily', 'hourly', '6hourly')")
    output_dir: str = Field(description="Output directory for results")
    catchment_mask: Optional[str] = Field(None, description="Path to catchment mask file")
    forcing_data_dir: Optional[str] = Field(None, description="Directory containing meteorological forcing data")


class WaterBalanceParams(BaseModel):
    """Parameters for water balance analysis."""
    settings_file: str = Field(description="Path to Lisflood settings file")
    analysis_period: List[str] = Field(description="Analysis period [start_date, end_date]")
    components: Optional[List[str]] = Field(None, description="Water balance components to analyze")
    spatial_aggregation: Optional[str] = Field("catchment", description="Spatial aggregation level")
    output_format: Optional[str] = Field("netcdf", description="Output format ('netcdf', 'csv', 'tss')")


class FloodForecastParams(BaseModel):
    """Parameters for flood forecasting."""
    settings_file: str = Field(description="Path to Lisflood settings file")
    forecast_start: str = Field(description="Forecast start date (YYYY-MM-DD)")
    forecast_horizon: int = Field(description="Forecast horizon in days")
    meteorological_forecast: str = Field(description="Path to meteorological forecast data")
    initial_conditions: Optional[str] = Field(None, description="Path to initial conditions file")
    ensemble_size: Optional[int] = Field(1, description="Number of ensemble members")


class RiverRoutingParams(BaseModel):
    """Parameters for river routing analysis."""
    settings_file: str = Field(description="Path to Lisflood settings file")
    discharge_points: List[Dict[str, float]] = Field(description="List of discharge measurement points [{'lat': x, 'lon': y}]")
    routing_method: Optional[str] = Field("kinematic", description="Routing method ('kinematic', 'dynamic')")
    time_period: List[str] = Field(description="Analysis time period [start_date, end_date]")
    calibration_data: Optional[str] = Field(None, description="Path to observed discharge data for calibration")


class LandUseScenarioParams(BaseModel):
    """Parameters for land use scenario analysis."""
    base_settings: str = Field(description="Path to base Lisflood settings file")
    scenario_name: str = Field(description="Name of the land use scenario")
    land_use_maps: Dict[str, str] = Field(description="Paths to land use maps {'land_use_type': 'file_path'}")
    scenario_period: List[str] = Field(description="Scenario analysis period [start_date, end_date]")
    compare_to_baseline: Optional[bool] = Field(True, description="Compare results to baseline scenario")


class ParameterCalibrationParams(BaseModel):
    """Parameters for model calibration."""
    settings_file: str = Field(description="Path to Lisflood settings file")
    calibration_period: List[str] = Field(description="Calibration period [start_date, end_date]")
    validation_period: List[str] = Field(description="Validation period [start_date, end_date]")
    observed_data: str = Field(description="Path to observed discharge/water level data")
    parameters_to_calibrate: List[str] = Field(description="List of parameter names to calibrate")
    optimization_method: Optional[str] = Field("nsga2", description="Optimization method")
    n_generations: Optional[int] = Field(100, description="Number of optimization generations")


# Tool classes
class LisfloodSimulationTool(BaseTool):
    """Tool for running Lisflood hydrological simulations."""
    
    name = "lisflood_simulation"
    description = "Run Lisflood hydrological model simulation for flood analysis"
    args_schema: Type[BaseModel] = FloodSimulationParams
    
    def _run(self, **kwargs) -> str:
        """This will be handled by the adapter."""
        return json.dumps({"tool": self.name, "parameters": kwargs})


class LisfloodWaterBalanceTool(BaseTool):
    """Tool for water balance analysis."""
    
    name = "lisflood_water_balance"
    description = "Analyze water balance components using Lisflood model"
    args_schema: Type[BaseModel] = WaterBalanceParams
    
    def _run(self, **kwargs) -> str:
        return json.dumps({"tool": self.name, "parameters": kwargs})


class LisfloodForecastTool(BaseTool):
    """Tool for flood forecasting."""
    
    name = "lisflood_forecast"
    description = "Generate flood forecasts using Lisflood model with meteorological predictions"
    args_schema: Type[BaseModel] = FloodForecastParams
    
    def _run(self, **kwargs) -> str:
        return json.dumps({"tool": self.name, "parameters": kwargs})


class LisfloodRiverRoutingTool(BaseTool):
    """Tool for river routing analysis."""
    
    name = "lisflood_river_routing"
    description = "Analyze river flow routing and discharge at specific locations"
    args_schema: Type[BaseModel] = RiverRoutingParams
    
    def _run(self, **kwargs) -> str:
        return json.dumps({"tool": self.name, "parameters": kwargs})


class LisfloodLandUseScenarioTool(BaseTool):
    """Tool for land use scenario analysis."""
    
    name = "lisflood_land_use_scenario"
    description = "Analyze impact of land use changes on hydrological processes"
    args_schema: Type[BaseModel] = LandUseScenarioParams
    
    def _run(self, **kwargs) -> str:
        return json.dumps({"tool": self.name, "parameters": kwargs})


class LisfloodCalibrationTool(BaseTool):
    """Tool for model parameter calibration."""
    
    name = "lisflood_calibration"
    description = "Calibrate Lisflood model parameters using observed data"
    args_schema: Type[BaseModel] = ParameterCalibrationParams
    
    def _run(self, **kwargs) -> str:
        return json.dumps({"tool": self.name, "parameters": kwargs})


# Tool registry for Lisflood
LISFLOOD_TOOLS = {
    "lisflood_simulation": {
        "class": LisfloodSimulationTool,
        "category": "simulation",
        "description": "Run hydrological simulations for flood analysis",
        "estimated_runtime": 900,  # 15 minutes
        "memory_requirements": "8GB",
        "tags": ["hydrology", "flood", "simulation", "water"],
        "examples": [
            {
                "name": "European flood simulation",
                "parameters": {
                    "start_date": "2021-06-01",
                    "end_date": "2021-08-31",
                    "time_step": "daily",
                    "output_dir": "/output/flood_2021"
                }
            }
        ]
    },
    "lisflood_water_balance": {
        "class": LisfloodWaterBalanceTool,
        "category": "analysis",
        "description": "Analyze water balance components",
        "estimated_runtime": 300,  # 5 minutes
        "memory_requirements": "4GB",
        "tags": ["water-balance", "hydrology", "analysis"],
        "examples": [
            {
                "name": "Annual water balance analysis",
                "parameters": {
                    "analysis_period": ["2020-01-01", "2020-12-31"],
                    "components": ["precipitation", "evapotranspiration", "runoff"],
                    "output_format": "csv"
                }
            }
        ]
    },
    "lisflood_forecast": {
        "class": LisfloodForecastTool,
        "category": "forecasting",
        "description": "Generate flood forecasts",
        "estimated_runtime": 600,  # 10 minutes
        "memory_requirements": "6GB",
        "tags": ["forecast", "prediction", "early-warning"],
        "examples": [
            {
                "name": "7-day flood forecast",
                "parameters": {
                    "forecast_start": "2024-03-15",
                    "forecast_horizon": 7,
                    "ensemble_size": 10
                }
            }
        ]
    },
    "lisflood_river_routing": {
        "class": LisfloodRiverRoutingTool,
        "category": "routing",
        "description": "Analyze river flow routing",
        "estimated_runtime": 450,  # 7.5 minutes
        "memory_requirements": "5GB",
        "tags": ["routing", "discharge", "rivers"],
        "examples": [
            {
                "name": "Danube river routing",
                "parameters": {
                    "discharge_points": [
                        {"lat": 48.2, "lon": 16.3},
                        {"lat": 44.8, "lon": 20.5}
                    ],
                    "routing_method": "kinematic",
                    "time_period": ["2020-01-01", "2020-12-31"]
                }
            }
        ]
    },
    "lisflood_land_use_scenario": {
        "class": LisfloodLandUseScenarioTool,
        "category": "scenario_analysis",
        "description": "Analyze land use change impacts",
        "estimated_runtime": 720,  # 12 minutes
        "memory_requirements": "7GB",
        "tags": ["land-use", "scenario", "change-impact"],
        "examples": [
            {
                "name": "Urbanization impact analysis",
                "parameters": {
                    "scenario_name": "urbanization_2050",
                    "land_use_maps": {
                        "urban": "/data/urban_2050.nc",
                        "forest": "/data/forest_2050.nc"
                    },
                    "scenario_period": ["2050-01-01", "2050-12-31"]
                }
            }
        ]
    },
    "lisflood_calibration": {
        "class": LisfloodCalibrationTool,
        "category": "calibration",
        "description": "Calibrate model parameters",
        "estimated_runtime": 3600,  # 1 hour
        "memory_requirements": "10GB",
        "tags": ["calibration", "optimization", "parameters"],
        "examples": [
            {
                "name": "Rhine basin calibration",
                "parameters": {
                    "calibration_period": ["2010-01-01", "2015-12-31"],
                    "validation_period": ["2016-01-01", "2020-12-31"],
                    "parameters_to_calibrate": ["manning_n", "soil_depth", "ksat"],
                    "optimization_method": "nsga2"
                }
            }
        ]
    }
}


def get_lisflood_tools() -> Dict[str, Dict[str, Any]]:
    """Get all Lisflood tool definitions."""
    return LISFLOOD_TOOLS


def create_lisflood_tool_instances() -> List[BaseTool]:
    """Create instances of all Lisflood tools."""
    tools = []
    for tool_name, tool_info in LISFLOOD_TOOLS.items():
        tool_class = tool_info["class"]
        tools.append(tool_class())
    return tools