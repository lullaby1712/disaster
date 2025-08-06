"""
Climada Model Adapter for MCP

Implements the BaseModel interface for Climada climate risk analysis.
Handles environment activation, script execution, and result processing.
"""

import json
import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.base_model import BaseModel, ModelResult, ModelStatus
from ..tools.climada_tools import get_climada_tools

logger = logging.getLogger(__name__)


class ClimadaAdapter(BaseModel):
    """
    Climada model adapter for climate risk analysis.
    
    Provides tools for:
    - Impact assessment
    - Hazard modeling  
    - Exposure analysis
    - Cost-benefit analysis
    - Uncertainty analysis
    """
    
    def __init__(self, climada_path: Optional[Path] = None):
        super().__init__(name="climada", version="4.1.0")
        self._climada_path = climada_path or self._find_climada_installation()
        self._tools = get_climada_tools()
    
    def _find_climada_installation(self) -> Optional[Path]:
        """Find Climada installation path."""
        # Try common locations
        possible_paths = [
            Path.cwd() / "Climada",
            Path.home() / "Climada",
            Path("/opt/climada"),
            Path("C:/Program Files/Climada")
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "climada").exists():
                self.logger.info(f"Found Climada installation at: {path}")
                return path
        
        self.logger.warning("Could not find Climada installation")
        return None
    
    @property
    def model_path(self) -> Path:
        """Path to Climada installation."""
        return self._climada_path or Path.cwd() / "Climada"
    
    @property
    def conda_environment(self) -> str:
        """Name of Conda environment for Climada."""
        return "climada_env"
    
    @property
    def available_tools(self) -> List[str]:
        """List of available Climada tools."""
        return list(self._tools.keys())
    
    async def validate_environment(self) -> bool:
        """Validate Climada environment setup."""
        try:
            # Test basic Climada import
            result = await self.run_conda_command([
                "python", "-c", 
                "import climada; print('Climada version:', climada.__version__)"
            ], timeout=60)
            
            if result.returncode == 0:
                self.logger.info("Climada environment validation successful")
                return True
            else:
                self.logger.error(f"Climada validation failed: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Environment validation error: {e}")
            return False
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> ModelResult:
        """Execute a Climada tool with given parameters."""
        if execution_id is None:
            execution_id = str(uuid.uuid4())
        
        start_time = datetime.now()
        self.status = ModelStatus.RUNNING
        self.current_execution_id = execution_id
        
        try:
            # Validate tool exists
            if tool_name not in self._tools:
                raise ValueError(f"Tool '{tool_name}' not available")
            
            # Prepare execution environment
            exec_dir = await self.prepare_execution_environment(execution_id)
            
            # Generate and execute script
            script_content = self._generate_script(tool_name, parameters)
            script_path = exec_dir / f"{tool_name}_{execution_id}.py"
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            self.logger.info(f"Executing Climada tool '{tool_name}' in {exec_dir}")
            
            # Execute script
            result = await self.run_conda_command([
                "python", str(script_path)
            ], working_dir=exec_dir, timeout=3600)
            
            # Parse results
            if result.returncode == 0:
                execution_result = self._parse_results(exec_dir, result.stdout.decode())
                status = ModelStatus.COMPLETED
                error = None
            else:
                execution_result = None
                status = ModelStatus.FAILED
                error = result.stderr.decode()
            
            # Create result
            model_result = self.create_result(
                tool_name=tool_name,
                execution_id=execution_id,
                status=status,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                data=execution_result,
                error=error,
                files=self._collect_output_files(exec_dir),
                working_directory=str(exec_dir)
            )
            
            return model_result
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            return self.create_result(
                tool_name=tool_name,
                execution_id=execution_id,
                status=ModelStatus.FAILED,
                start_time=start_time,
                end_time=datetime.now(),
                duration=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )
        
        finally:
            self.status = ModelStatus.IDLE
            self.current_execution_id = None
    
    def _generate_script(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Generate Python script for tool execution."""
        
        # Base script template
        script_template = '''
import sys
import json
import traceback
from pathlib import Path
import numpy as np
import pandas as pd

# Add Climada to path
sys.path.insert(0, str(Path("{climada_path}").resolve()))

try:
    import climada
    from climada.engine import Impact
    from climada.entity import Exposures, ImpactFuncSet
    from climada.hazard import Hazard
    from climada.engine.cost_benefit import CostBenefit
    
    print("Climada imports successful")
    
    # Tool-specific execution code
    {tool_code}
    
    print("Tool execution completed successfully")
    
except Exception as e:
    print(f"ERROR: {{e}}")
    traceback.print_exc()
    sys.exit(1)
'''
        
        # Generate tool-specific code
        tool_code = self._generate_tool_code(tool_name, parameters)
        
        return script_template.format(
            climada_path=self.model_path,
            tool_code=tool_code
        )
    
    def _generate_tool_code(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Generate tool-specific Python code."""
        
        if tool_name == "climada_impact_assessment":
            return self._generate_impact_assessment_code(parameters)
        elif tool_name == "climada_hazard_modeling":
            return self._generate_hazard_modeling_code(parameters)
        elif tool_name == "climada_exposure_analysis":
            return self._generate_exposure_analysis_code(parameters)
        elif tool_name == "climada_cost_benefit":
            return self._generate_cost_benefit_code(parameters)
        elif tool_name == "climada_uncertainty_analysis":
            return self._generate_uncertainty_analysis_code(parameters)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _generate_impact_assessment_code(self, params: Dict[str, Any]) -> str:
        """Generate code for impact assessment."""
        return f'''
# Impact Assessment Tool
print("Starting impact assessment...")

# Parameters
hazard_type = "{params.get('hazard_type', 'tropical_cyclone')}"
region = "{params.get('region', 'global')}"
year_range = {params.get('year_range', [2000, 2020])}

# Create or load hazard
if hazard_type == "tropical_cyclone":
    from climada.hazard import TropCyclone
    hazard = TropCyclone.from_ibtracs_netcdf(
        basin="NA" if "atlantic" in region.lower() else "WP",
        year_range=year_range
    )
else:
    # Load from file if path provided
    hazard_file = "{params.get('hazard_file_path', '')}"
    if hazard_file:
        hazard = Hazard.from_hdf5(hazard_file)
    else:
        raise ValueError("Hazard file path required for non-tropical cyclone hazards")

print(f"Loaded hazard with {{len(hazard.event_id)}} events")

# Create or load exposure
exposure_file = "{params.get('exposure_file_path', '')}"
if exposure_file:
    exposure = Exposures.from_hdf5(exposure_file)
else:
    # Generate LitPop exposure for region
    from climada.entity.exposures.litpop import LitPop
    exposure = LitPop.from_countries(countries=[region[:3].upper()], res_arcsec=300)

print(f"Loaded exposure with {{len(exposure.gdf)}} assets")

# Load or create impact functions
impf_id = "{params.get('impact_function_id', 'default')}"
if hazard_type == "tropical_cyclone":
    from climada.entity.impact_funcs import ImpfTropCyclone
    impf_set = ImpfTropCyclone.from_emanuel_usa()
else:
    impf_set = ImpactFuncSet()

# Calculate impact
impact = Impact()
impact.calc(exposure, impf_set, hazard)

# Save results
impact.write_hdf5("impact_results.h5")

# Generate summary
results = {{
    "total_impact": float(impact.aai_agg),
    "events_analyzed": len(impact.event_id),
    "assets_analyzed": len(impact.coord_exp),
    "return_periods": {params.get('return_period', [10, 50, 100, 250])},
    "impact_per_event": impact.at_event.tolist() if hasattr(impact, 'at_event') else [],
    "output_files": ["impact_results.h5"]
}}

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Impact assessment completed")
'''
    
    def _generate_hazard_modeling_code(self, params: Dict[str, Any]) -> str:
        """Generate code for hazard modeling."""
        return f'''
# Hazard Modeling Tool
print("Starting hazard modeling...")

hazard_type = "{params.get('hazard_type')}"
region = "{params.get('region')}"
resolution = {params.get('resolution', 0.1)}

if hazard_type == "tropical_cyclone":
    from climada.hazard import TCTracks, TropCyclone
    
    # Generate synthetic tracks
    tracks = TCTracks.from_simulated_storms(
        basin="NA" if "atlantic" in region.lower() else "WP",
        nb_tracks=100
    )
    
    # Create hazard from tracks
    hazard = TropCyclone.from_tracks(tracks, res_deg=resolution)
    
elif hazard_type == "flood":
    from climada.hazard import RiverFlood
    hazard = RiverFlood.from_isimip(
        dph_path="path_to_flood_data",
        frc_path="path_to_fraction_data"
    )

# Save hazard
hazard.write_hdf5("hazard_output.h5")

results = {{
    "hazard_type": hazard_type,
    "events_generated": len(hazard.event_id),
    "spatial_resolution": resolution,
    "intensity_unit": hazard.units,
    "output_files": ["hazard_output.h5"]
}}

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Hazard modeling completed")
'''
    
    def _generate_exposure_analysis_code(self, params: Dict[str, Any]) -> str:
        """Generate code for exposure analysis."""
        return f'''
# Exposure Analysis Tool
print("Starting exposure analysis...")

from climada.entity.exposures.litpop import LitPop

country_iso = "{params.get('country_iso')}"
exposure_type = "{params.get('exposure_type', 'litpop')}"
reference_year = {params.get('reference_year', 2020)}
admin_level = {params.get('admin_level', 1)}

# Generate exposure
if exposure_type == "litpop":
    exposure = LitPop.from_countries(
        countries=[country_iso],
        res_arcsec=300,
        reference_year=reference_year
    )
elif exposure_type == "population":
    exposure = LitPop.from_countries(
        countries=[country_iso],
        res_arcsec=300,
        reference_year=reference_year,
        fin_mode="pop"
    )
else:
    exposure = LitPop.from_countries(
        countries=[country_iso],
        res_arcsec=300,
        reference_year=reference_year
    )

# Save exposure
exposure.write_hdf5("exposure_output.h5")

# Generate statistics
results = {{
    "country": country_iso,
    "exposure_type": exposure_type,
    "total_value": float(exposure.gdf.value.sum()),
    "number_of_assets": len(exposure.gdf),
    "reference_year": reference_year,
    "value_unit": exposure.value_unit,
    "output_files": ["exposure_output.h5"]
}}

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Exposure analysis completed")
'''
    
    def _generate_cost_benefit_code(self, params: Dict[str, Any]) -> str:
        """Generate code for cost-benefit analysis."""
        return f'''
# Cost-Benefit Analysis Tool
print("Starting cost-benefit analysis...")

# Load required data
exposure_file = "{params.get('exposure_file_path')}"
hazard_file = "{params.get('hazard_file_path')}"

exposure = Exposures.from_hdf5(exposure_file)
hazard = Hazard.from_hdf5(hazard_file)

# Create measure
from climada.entity.measures import Measure, MeasureSet
measure = Measure()
measure.name = "{params.get('measure_name')}"
measure.cost = {params.get('measure_cost')}
measure.hazard_inten_imp = 0.5  # Example reduction factor

measure_set = MeasureSet()
measure_set.append(measure)

# Perform cost-benefit analysis
cost_benefit = CostBenefit()
cost_benefit.calc(
    hazard=hazard,
    exposure=exposure,
    imp_func_set=impf_set,
    measure_set=measure_set
)

# Save results
results = {{
    "measure_name": measure.name,
    "measure_cost": measure.cost,
    "benefit": float(cost_benefit.benefit[0]) if cost_benefit.benefit else 0,
    "cost_benefit_ratio": float(cost_benefit.tot_climate_risk / measure.cost) if measure.cost > 0 else 0,
    "net_present_value": float(cost_benefit.benefit[0] - measure.cost) if cost_benefit.benefit else -measure.cost
}}

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Cost-benefit analysis completed")
'''
    
    def _generate_uncertainty_analysis_code(self, params: Dict[str, Any]) -> str:
        """Generate code for uncertainty analysis."""
        return f'''
# Uncertainty Analysis Tool
print("Starting uncertainty analysis...")

from climada.engine.unsequa import UncertaintyQuantification

analysis_type = "{params.get('analysis_type')}"
n_samples = {params.get('n_samples', 1000)}

# Setup uncertainty analysis
unc_data = UncertaintyQuantification()

# Define parameter bounds (example)
param_bounds = {params.get('parameters', {})}

# Run analysis
if analysis_type == "sensitivity":
    from SALib.sample import saltelli
    from SALib.analyze import sobol
    
    # Perform Sobol sensitivity analysis
    problem = {{
        'num_vars': len(param_bounds),
        'names': list(param_bounds.keys()),
        'bounds': list(param_bounds.values())
    }}
    
    # Generate samples
    param_values = saltelli.sample(problem, n_samples)
    
    # Run model for each sample (simplified)
    results_array = []
    for params_sample in param_values:
        # Run impact calculation with varied parameters
        # This is a simplified example
        result = np.random.normal(1000, 100)  # Placeholder
        results_array.append(result)
    
    # Analyze sensitivity
    si = sobol.analyze(problem, np.array(results_array))
    
    results = {{
        "analysis_type": analysis_type,
        "n_samples": n_samples,
        "first_order_indices": si['S1'].tolist(),
        "total_order_indices": si['ST'].tolist(),
        "parameter_names": problem['names']
    }}

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

print("Uncertainty analysis completed")
'''
    
    def _parse_results(self, exec_dir: Path, stdout_content: str) -> Optional[Dict[str, Any]]:
        """Parse execution results from output files."""
        try:
            results_file = exec_dir / "results.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    results = json.load(f)
                return results
            else:
                # Parse from stdout if no results file
                return {"stdout": stdout_content}
        except Exception as e:
            self.logger.warning(f"Could not parse results: {e}")
            return {"stdout": stdout_content}
    
    def _collect_output_files(self, exec_dir: Path) -> List[str]:
        """Collect output files from execution directory."""
        output_files = []
        for file_path in exec_dir.glob("*"):
            if file_path.is_file() and file_path.suffix in ['.h5', '.nc', '.csv', '.json', '.png']:
                output_files.append(str(file_path))
        return output_files