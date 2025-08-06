"""
Climada Tools for MCP

LangGraph-compatible tool definitions for Climada climate risk analysis.
Based on analysis of Climada's core functionality.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type, Union

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Parameter models for type validation
class ImpactAssessmentParams(BaseModel):
    """Parameters for impact assessment."""
    hazard_type: str = Field(description="Type of hazard (e.g., 'tropical_cyclone', 'flood', 'wildfire')")
    hazard_file_path: Optional[str] = Field(None, description="Path to hazard data file")
    exposure_file_path: Optional[str] = Field(None, description="Path to exposure data file")
    impact_function_id: Optional[str] = Field(None, description="Impact function identifier")
    region: Optional[str] = Field(None, description="Geographic region for analysis")
    year_range: Optional[List[int]] = Field(None, description="Year range for analysis [start_year, end_year]")
    return_period: Optional[List[int]] = Field(None, description="Return periods for analysis")


class HazardModelingParams(BaseModel):
    """Parameters for hazard modeling."""
    hazard_type: str = Field(description="Type of hazard to model")
    region: str = Field(description="Geographic region")
    resolution: Optional[float] = Field(0.1, description="Spatial resolution in degrees")
    time_range: Optional[List[str]] = Field(None, description="Time range ['YYYY-MM-DD', 'YYYY-MM-DD']")
    climate_scenario: Optional[str] = Field(None, description="Climate scenario (e.g., 'rcp26', 'rcp85')")
    wind_model: Optional[str] = Field(None, description="Wind model for tropical cyclones")


class ExposureAnalysisParams(BaseModel):
    """Parameters for exposure analysis."""
    country_iso: str = Field(description="ISO country code (e.g., 'USA', 'CHE')")
    admin_level: Optional[int] = Field(1, description="Administrative level (0=country, 1=state/province)")
    exposure_type: str = Field(description="Type of exposure ('litpop', 'population', 'assets')")
    reference_year: Optional[int] = Field(2020, description="Reference year for exposure data")
    resolution: Optional[float] = Field(0.1, description="Spatial resolution in degrees")


class CostBenefitParams(BaseModel):
    """Parameters for cost-benefit analysis."""
    measure_name: str = Field(description="Name of the adaptation measure")
    hazard_type: str = Field(description="Type of hazard")
    exposure_file_path: str = Field(description="Path to exposure data")
    hazard_file_path: str = Field(description="Path to hazard data")
    measure_cost: float = Field(description="Cost of the measure")
    discount_rate: Optional[float] = Field(0.03, description="Discount rate for analysis")
    time_horizon: Optional[int] = Field(30, description="Time horizon in years")


class UncertaintyAnalysisParams(BaseModel):
    """Parameters for uncertainty analysis."""
    analysis_type: str = Field(description="Type of analysis ('sensitivity', 'uncertainty')")
    parameters: Dict[str, Any] = Field(description="Parameters to vary in the analysis")
    n_samples: Optional[int] = Field(1000, description="Number of samples for Monte Carlo")
    base_case_file: str = Field(description="Path to base case configuration")


# Tool classes
class ClimadaImpactAssessmentTool(BaseTool):
    """Tool for conducting climate impact assessments using Climada."""
    
    name = "climada_impact_assessment" 
    description = "Assess the impact of climate hazards on exposed assets using Climada"
    args_schema: Type[BaseModel] = ImpactAssessmentParams
    
    def _run(self, **kwargs) -> str:
        """This will be handled by the adapter."""
        return json.dumps({"tool": self.name, "parameters": kwargs})


class ClimadaHazardModelingTool(BaseTool):
    """Tool for hazard modeling and event generation."""
    
    name = "climada_hazard_modeling"
    description = "Model climate hazards and generate hazard event sets using Climada"
    args_schema: Type[BaseModel] = HazardModelingParams
    
    def _run(self, **kwargs) -> str:
        return json.dumps({"tool": self.name, "parameters": kwargs})


class ClimadaExposureAnalysisTool(BaseTool):
    """Tool for exposure analysis and mapping."""
    
    name = "climada_exposure_analysis"
    description = "Analyze and map exposed assets and population using LitPop methodology"
    args_schema: Type[BaseModel] = ExposureAnalysisParams
    
    def _run(self, **kwargs) -> str:
        return json.dumps({"tool": self.name, "parameters": kwargs})


class ClimadaCostBenefitTool(BaseTool):
    """Tool for cost-benefit analysis of adaptation measures."""
    
    name = "climada_cost_benefit"
    description = "Conduct cost-benefit analysis of climate adaptation measures"
    args_schema: Type[BaseModel] = CostBenefitParams
    
    def _run(self, **kwargs) -> str:
        return json.dumps({"tool": self.name, "parameters": kwargs})


class ClimadaUncertaintyAnalysisTool(BaseTool):
    """Tool for uncertainty and sensitivity analysis."""
    
    name = "climada_uncertainty_analysis"
    description = "Perform uncertainty and sensitivity analysis for climate risk assessments"
    args_schema: Type[BaseModel] = UncertaintyAnalysisParams
    
    def _run(self, **kwargs) -> str:
        return json.dumps({"tool": self.name, "parameters": kwargs})


# Tool registry for Climada
CLIMADA_TOOLS = {
    "climada_impact_assessment": {
        "class": ClimadaImpactAssessmentTool,
        "category": "impact_analysis",
        "description": "Assess climate impacts on exposed assets",
        "estimated_runtime": 300,  # 5 minutes
        "memory_requirements": "4GB",
        "tags": ["climate", "impact", "risk", "assessment"],
        "examples": [
            {
                "name": "Tropical cyclone impact in Florida",
                "parameters": {
                    "hazard_type": "tropical_cyclone",
                    "region": "Florida, USA",
                    "year_range": [2000, 2020],
                    "return_period": [10, 50, 100, 250]
                }
            }
        ]
    },
    "climada_hazard_modeling": {
        "class": ClimadaHazardModelingTool,
        "category": "hazard_modeling",
        "description": "Model climate hazards and generate event sets",
        "estimated_runtime": 600,  # 10 minutes
        "memory_requirements": "8GB",
        "tags": ["hazard", "modeling", "events", "climate"],
        "examples": [
            {
                "name": "Hurricane modeling for Caribbean",
                "parameters": {
                    "hazard_type": "tropical_cyclone",
                    "region": "Caribbean",
                    "climate_scenario": "rcp85",
                    "resolution": 0.1
                }
            }
        ]
    },
    "climada_exposure_analysis": {
        "class": ClimadaExposureAnalysisTool,
        "category": "exposure_analysis",
        "description": "Analyze exposed assets and population",
        "estimated_runtime": 180,  # 3 minutes
        "memory_requirements": "2GB",
        "tags": ["exposure", "population", "assets", "litpop"],
        "examples": [
            {
                "name": "Switzerland exposure analysis",
                "parameters": {
                    "country_iso": "CHE",
                    "exposure_type": "litpop",
                    "reference_year": 2020,
                    "admin_level": 1
                }
            }
        ]
    },
    "climada_cost_benefit": {
        "class": ClimadaCostBenefitTool,
        "category": "economic_analysis",
        "description": "Cost-benefit analysis of adaptation measures",
        "estimated_runtime": 240,  # 4 minutes
        "memory_requirements": "3GB",
        "tags": ["adaptation", "economics", "cost-benefit", "measures"],
        "examples": [
            {
                "name": "Seawall cost-benefit analysis",
                "parameters": {
                    "measure_name": "coastal_seawall",
                    "hazard_type": "storm_surge",
                    "measure_cost": 1000000,
                    "time_horizon": 50
                }
            }
        ]
    },
    "climada_uncertainty_analysis": {
        "class": ClimadaUncertaintyAnalysisTool,
        "category": "uncertainty_analysis",
        "description": "Uncertainty and sensitivity analysis",
        "estimated_runtime": 900,  # 15 minutes
        "memory_requirements": "6GB",
        "tags": ["uncertainty", "sensitivity", "monte-carlo", "analysis"],
        "examples": [
            {
                "name": "Impact function sensitivity",
                "parameters": {
                    "analysis_type": "sensitivity",
                    "parameters": {
                        "impact_function_slope": [0.5, 1.0, 1.5],
                        "wind_threshold": [30, 35, 40]
                    },
                    "n_samples": 500
                }
            }
        ]
    }
}


def get_climada_tools() -> Dict[str, Dict[str, Any]]:
    """Get all Climada tool definitions."""
    return CLIMADA_TOOLS


def create_climada_tool_instances() -> List[BaseTool]:
    """Create instances of all Climada tools."""
    tools = []
    for tool_name, tool_info in CLIMADA_TOOLS.items():
        tool_class = tool_info["class"]
        tools.append(tool_class())
    return tools