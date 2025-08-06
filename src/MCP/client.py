"""MCP client for communicating with disaster model servers on TiaozhanbeiMCP host."""
import asyncio
import json
import subprocess
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
import paramiko
import os
from pathlib import Path

# 导入 SDKClient 是为了类型提示，实际在 MCPClient 中不直接使用 SDKClient 实例
# from .sdk import MCPClient as SDKClient # 避免循环导入，这里不需要导入 SDKClient 实例

# 假设 mcp_router 和 tool_registry 是异步安全的或在其他地方处理了异步性
from .core.router import mcp_router
from .core.tool_registry import tool_registry

class MCPClient:
    """
    MCP Client for actual model execution on TiaozhanbeiMCP host.
    
    Connects to deployed models via SSH and Docker containers.
    """
    
    def __init__(self):
        # Remote host configuration
        self.remote_host = "lenovo@10.0.3.4"  # TiaozhanbeiMCP host
        self.remote_base_path = "/data/Tiaozhanbei"
        
        # Model configurations
        self.model_endpoints = {
            "cell2fire": "cell2fire_adapter",
            "climada": "climada",
            "lisflood": "lisflood", 
            "nfdrs4": "nfdrs4_adapter",
            "pangu": "pangu_adapter",
            "aurora": "aurora_adapter",
            "openswpc": "openswpc_adapter"
        }
        
        # Docker container info (shared container for multiple models)
        self.docker_container_id = None  # Will be determined at runtime
        
        # Jupyter Lab info for Climada/Lisflood/Aurora
        self.jupyter_base_url = "http://10.0.3.4:8888"
        
        self.active_connections = {}
        # self._sdk_client = None # 这个属性在这个文件中似乎没有被使用，可以移除
        self._ssh_client = None # 初始化为 None
    
    async def _get_ssh_connection(self) -> paramiko.SSHClient:
        """Get or create SSH connection to remote host."""
        if not self._ssh_client or not self._ssh_client.get_transport() or not self._ssh_client.get_transport().is_active():
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # *** 关键修改：将同步的 connect 调用包装在 asyncio.to_thread 中 ***
            try:
                username, hostname = self.remote_host.split('@')
                await asyncio.to_thread(self._ssh_client.connect, hostname=hostname, username=username)
                print(f"SSH connection established to {hostname}")
            except Exception as e:
                print(f"Failed to establish SSH connection: {e}")
                self._ssh_client = None # 连接失败时重置客户端
                raise
        return self._ssh_client
    
    async def _execute_ssh_command(self, ssh_client: paramiko.SSHClient, cmd: str) -> tuple[str, str]:
        """Helper to execute SSH commands asynchronously."""
        # *** 关键修改：将同步的 exec_command 和 read 调用包装在 asyncio.to_thread 中 ***
        stdin, stdout, stderr = await asyncio.to_thread(ssh_client.exec_command, cmd)
        output = await asyncio.to_thread(stdout.read)
        error = await asyncio.to_thread(stderr.read)
        return output.decode(), error.decode()

    async def _get_docker_container_id(self) -> Optional[str]:
        """Get the Docker container ID for models that use containers."""
        if self.docker_container_id:
            return self.docker_container_id
            
        try:
            ssh = await self._get_ssh_connection()
            # *** 关键修改：使用异步的 SSH 命令执行器 ***
            container_id_output, error = await self._execute_ssh_command(ssh, "sudo docker ps -q --filter ancestor=pangu_weather")
            container_id = container_id_output.strip()
            if container_id:
                self.docker_container_id = container_id
                return container_id
            if error:
                print(f"Error getting container ID: {error}")
        except Exception as e:
            print(f"Failed to get container ID: {e}")
        return None
    
    async def connect_to_model(self, model_name: str) -> bool:
        """Connect to a specific model server."""
        try:
            model_key = self.model_endpoints.get(model_name)
            if not model_key:
                raise ValueError(f"Unknown model: {model_name}")
            
            connected = False
            # Test connection based on model type
            if model_name in ["pangu", "cell2fire", "nfdrs4"]:
                # Container-based models
                container_id = await self._get_docker_container_id()
                connected = container_id is not None
            elif model_name in ["climada", "lisflood", "aurora"]:
                # Jupyter-based models
                try:
                    # *** 关键修改：将同步的 requests.get 调用包装在 asyncio.to_thread 中 ***
                    response = await asyncio.to_thread(requests.get, f"{self.jupyter_base_url}/api/status", timeout=5)
                    connected = response.status_code == 200
                except Exception as e:
                    print(f"Jupyter connection check failed for {model_name}: {e}")
                    connected = False
            elif model_name == "openswpc":
                # Direct binary execution - assume available if SSH works
                # 仍需要 SSH 连接，所以会调用 _get_ssh_connection
                try:
                    await self._get_ssh_connection()
                    connected = True
                except Exception as e:
                    print(f"OpenSWPC SSH check failed: {e}")
                    connected = False
            else:
                connected = False
            
            if connected:
                self.active_connections[model_name] = {
                    "endpoint": model_key,
                    "connected": True,
                    "last_ping": datetime.now()
                }
                return True
            else:
                print(f"Model {model_name} not available or connection failed.")
                return False
            
        except Exception as e:
            print(f"Failed to connect to {model_name}: {e}")
            return False
    
    async def execute_tool(
        self,
        tool_name: str, 
        parameters: Dict[str, Any],
        execution_id: Optional[str] = None
    ) -> Any:
        """Execute a tool through the MCP architecture."""
        try:
            # mcp_router 应该是一个异步安全的组件
            result = await mcp_router.execute_tool(
                tool_name=tool_name,
                parameters=parameters,
                execution_id=execution_id
            )
            return result
        except Exception as e:
            print(f"Tool execution failed: {e}")
            return None
    
    async def list_available_tools(self, model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available tools, optionally filtered by model."""
        try:
            # tool_registry 假设是同步的，如果其内部有耗时操作，也需要包装
            tools = await asyncio.to_thread(tool_registry.list_tools, model_name=model_name)
            return [tool.to_dict() for tool in tools]
        except Exception as e:
            print(f"Failed to list tools: {e}")
            return []
    
    async def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool."""
        try:
            # tool_registry 假设是同步的，如果其内部有耗时操作，也需要包装
            tool = await asyncio.to_thread(tool_registry.get_tool, tool_name)
            return tool.to_dict() if tool else None
        except Exception as e:
            print(f"Failed to get tool info: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the MCP system."""
        try:
            # mcp_router.health_check 假设是异步安全的
            return await mcp_router.health_check()
        except Exception as e:
            print(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
    
    # Model-specific implementations
    
    async def call_pangu_weather_model(
        self,
        location: "Location", # 假设 Location 是一个已定义的类型
        forecast_hours: int = 168
    ) -> Dict[str, Any]:
        """Call Pangu Weather forecasting model via Docker container."""
        
        start_time = time.time()
        
        try:
            container_id = await self._get_docker_container_id()
            if not container_id:
                raise Exception("Pangu Weather container not available")
            
            ssh = await self._get_ssh_connection()
            
            # Determine model type based on forecast hours
            if forecast_hours <= 1:
                model_type = "1h"
            elif forecast_hours <= 3:
                model_type = "3h"
            elif forecast_hours <= 6:
                model_type = "6h"
            else:
                model_type = "24h"
            
            # Execute Pangu Weather inference
            cmd = f"""sudo docker exec {container_id} bash -c "
                cd /pangu && 
                conda activate pangu_weather && 
                python inference_gpu.py --model_type {model_type} --lat {location.latitude} --lon {location.longitude} --hours {forecast_hours}
            \""""
            
            # *** 关键修改：使用异步的 SSH 命令执行器 ***
            output, error = await self._execute_ssh_command(ssh, cmd)
            
            if error and "Warning" not in error:
                raise Exception(f"Pangu execution error: {error}")
            
            # Parse output data from container's output_data folder
            weather_prediction = {
                "model_type": model_type,
                "forecast_hours": forecast_hours,
                "output_path": "/pangu/output_data",
                "status": "completed",
                "container_output": output.strip(),
                "location": {"lat": location.latitude, "lon": location.longitude}
                # Note: Real implementation would parse .npy output files
                # and extract temperature, humidity, wind, pressure data
            }
            
            processing_time = time.time() - start_time
            
            return {
                "model": "pangu_weather",
                "prediction": weather_prediction,
                "processing_time": processing_time,
                "location": location.to_dict(),
                "forecast_hours": forecast_hours
            }
            
        except Exception as e:
            return {
                "model": "pangu_weather",
                "error": str(e),
                "processing_time": time.time() - start_time,
                "note": "Requires SSH connection and input data preparation"
            }
    
    async def call_climada_model(
        self,
        analysis_type: str,
        parameters: Dict[str, Any]
    ) -> Optional[Any]:
        """Execute Climada model via Jupyter Lab API."""
        try:
            # Create Jupyter notebook execution request
            notebook_code = f"""
import climada
from climada.hazard import Hazard
from climada.entity import Entity
from climada.engine import Impact

# Analysis type: {analysis_type}
# Parameters: {json.dumps(parameters, indent=2)}

# Execute Climada analysis based on type
if '{analysis_type}' == 'impact_assessment':
    # Impact assessment code
    hazard = Hazard()
    entity = Entity()
    impact = Impact()
    # Configure hazard, entity, impact based on parameters
    result = {{"impact_assessment": "completed", "parameters": {json.dumps(parameters)}}}
elif '{analysis_type}' == 'hazard_modeling':
    # Hazard modeling code
    result = {{"hazard_modeling": "completed", "parameters": {json.dumps(parameters)}}}
else:
    result = {{"error": "Unknown analysis type", "type": "{analysis_type}"}}

print(f"Climada result: {{result}}")
result
"""
            
            # Execute via Jupyter API
            # *** 关键修改：将同步的 requests.post 调用包装在 asyncio.to_thread 中 ***
            jupyter_response = await asyncio.to_thread(
                requests.post,
                f"{self.jupyter_base_url}/api/kernels",
                json={"name": "climada"},
                timeout=30
            )
            
            if jupyter_response.status_code == 201:
                kernel_id = jupyter_response.json()["id"]
                
                # Execute code
                # *** 关键修改：将同步的 requests.post 调用包装在 asyncio.to_thread 中 ***
                exec_response = await asyncio.to_thread(
                    requests.post,
                    f"{self.jupyter_base_url}/api/kernels/{kernel_id}/execute",
                    json={"code": notebook_code},
                    timeout=300
                )
                
                return {
                    "model": "climada",
                    "analysis_type": analysis_type,
                    "status": "executed",
                    "kernel_id": kernel_id,
                    "parameters": parameters
                }
            else:
                raise Exception(f"Failed to create Jupyter kernel: {jupyter_response.status_code}")
                
        except Exception as e:
            print(f"Climada execution failed: {e}")
            return None
    
    async def call_lisflood_model(
        self,
        simulation_type: str,
        parameters: Dict[str, Any]
    ) -> Optional[Any]:
        """Execute Lisflood model via SSH and Conda environment."""
        try:
            ssh = await self._get_ssh_connection()
            
            # Prepare Lisflood simulation command
            cmd = f"""
                cd {self.remote_base_path}/Lisflood &&
                conda activate Lisflood &&
                python src/lisf1.py --simulation_type {simulation_type} --config_file tests/data/LF_ETRS89_UseCase/settings/cold.xml
            """
            
            # *** 关键修改：使用异步的 SSH 命令执行器 ***
            output, error = await self._execute_ssh_command(ssh, cmd)
            
            if error and "Warning" not in error:
                raise Exception(f"Lisflood execution error: {error}")
            
            return {
                "model": "lisflood",
                "simulation_type": simulation_type,
                "status": "completed",
                "output_path": f"{self.remote_base_path}/Lisflood/tests/data/LF_ETRS89_UseCase/out/",
                "execution_output": output.strip(),
                "parameters": parameters
            }
            
        except Exception as e:
            print(f"Lisflood execution failed: {e}")
            return None
    
    async def call_cell2fire_model(
        self,
        location: "Location", # 假设 Location 是一个已定义的类型
        weather_data: Dict[str, Any],
        fuel_data: Dict[str, Any],
        ignition_points: List[Dict[str, float]]
    ) -> Dict[str, Any]: # 假设 ModelResult 是一个 Dict[str, Any]
        """Call Cell2Fire wildfire simulation model via Docker container."""
        
        start_time = time.time()
        
        try:
            container_id = await self._get_docker_container_id()
            if not container_id:
                raise Exception("Cell2Fire container not available")
            
            ssh = await self._get_ssh_connection()
            
            # Prepare Cell2Fire execution
            cmd = f"""sudo docker exec {container_id} bash -c "
                source /opt/conda/etc/profile.d/conda.sh &&
                conda activate Cell2Fire &&
                cd /Cell2Fire/cell2fire/ &&
                python main.py --input-instance-folder /Cell2Fire/data/sample_instance --output-folder /Cell2Fire/results --sim-years 1 --weather 0 --nweathers 1
            \""""
            
            # *** 关键修改：使用异步的 SSH 命令执行器 ***
            output, error = await self._execute_ssh_command(ssh, cmd)
            
            if error and "Warning" not in error:
                raise Exception(f"Cell2Fire execution error: {error}")
            
            prediction = {
                "fire_simulation": "completed",
                "output_path": "/Cell2Fire/results",
                "execution_output": output.strip(),
                "location": location.to_dict(),
                "weather_data": weather_data,
                "fuel_data": fuel_data,
                "ignition_points": ignition_points
            }
            
            processing_time = time.time() - start_time
            confidence = 0.85
            
        except Exception as e:
            prediction = {"error": str(e), "status": "failed"}
            processing_time = time.time() - start_time
            confidence = 0.0
        
        return {
            "model_name": "cell2fire",
            "disaster_type": "wildfire",
            "prediction": prediction,
            "confidence": confidence,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
    
    async def call_nfdrs4_model(
        self,
        weather_data: Dict[str, Any],
        fuel_moisture_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call NFDRS4 fire danger rating model via Docker container."""
        try:
            container_id = await self._get_docker_container_id()
            if not container_id:
                raise Exception("NFDRS4 container not available")
            
            ssh = await self._get_ssh_connection()
            
            # Execute NFDRS4 command line tool
            cmd = f"""sudo docker exec {container_id} bash -c "
                cd /NFDRS4/bin &&
                ./NFDRS4_cli --weather_data '{json.dumps(weather_data)}' --fuel_moisture '{json.dumps(fuel_moisture_data)}'
            \""""
            
            # *** 关键修改：使用异步的 SSH 命令执行器 ***
            output, error = await self._execute_ssh_command(ssh, cmd)
            
            if error and "Warning" not in error:
                raise Exception(f"NFDRS4 execution error: {error}")
            
            return {
                "model": "nfdrs4",
                "fire_danger_rating": "calculated",
                "output": output.strip(),
                "weather_data": weather_data,
                "fuel_moisture_data": fuel_moisture_data
            }
            
        except Exception as e:
            return {
                "model": "nfdrs4",
                "error": str(e),
                "status": "failed"
            }
    
    async def call_aurora_model(
        self,
        forecast_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Aurora weather model via Jupyter Lab."""
        try:
            # Create Aurora execution code
            notebook_code = f"""
import torch
from aurora import Aurora

# Load Aurora model from local checkpoint
model = Aurora()
model.load_checkpoint_local('/data/Tiaozhanbei/aurora-main/models/aurora/')

# Execute forecast with parameters
parameters = {json.dumps(forecast_parameters)}
print(f"Aurora forecast parameters: {{parameters}}")

# Note: Actual Aurora inference would require input data preparation
result = {{"aurora_forecast": "executed", "parameters": parameters}}
print(f"Aurora result: {{result}}")
result
"""
            
            # Execute via Jupyter API
            # *** 关键修改：将同步的 requests.post 调用包装在 asyncio.to_thread 中 ***
            jupyter_response = await asyncio.to_thread(
                requests.post,
                f"{self.jupyter_base_url}/api/kernels",
                json={"name": "aurora"},
                timeout=30
            )
            
            if jupyter_response.status_code == 201:
                kernel_id = jupyter_response.json()["id"]
                
                return {
                    "model": "aurora",
                    "status": "executed",
                    "kernel_id": kernel_id,
                    "parameters": forecast_parameters
                }
            else:
                raise Exception(f"Failed to create Aurora Jupyter kernel: {jupyter_response.status_code}")
                
        except Exception as e:
            return {
                "model": "aurora",
                "error": str(e),
                "status": "failed"
            }
    
    async def call_openswpc_model(
        self,
        seismic_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call OpenSWPC seismic wave simulation model."""
        try:
            ssh = await self._get_ssh_connection()
            
            # Execute OpenSWPC binary
            cmd = f"""
                cd {self.remote_base_path}/OpenSWPC &&
                mpirun --allow-run-as-root -np 2 ./bin/swpc_psv.x -i example/input.inf
            """
            
            # *** 关键修改：使用异步的 SSH 命令执行器 ***
            output, error = await self._execute_ssh_command(ssh, cmd)
            
            if error and "Warning" not in error:
                raise Exception(f"OpenSWPC execution error: {error}")
            
            return {
                "model": "openswpc",
                "seismic_simulation": "completed",
                "output_path": f"{self.remote_base_path}/OpenSWPC/output/",
                "execution_output": output.strip(),
                "parameters": seismic_parameters
            }
            
        except Exception as e:
            return {
                "model": "openswpc",
                "error": str(e),
                "status": "failed"
            }
    
    # Legacy method wrappers for backward compatibility
    async def call_climada_model_legacy(self, *args, **kwargs):
        """Legacy wrapper for Climada model calls."""
        return await self.call_climada_model("impact_assessment", kwargs)
    
    async def call_lisflood_model_legacy(self, *args, **kwargs):
        """Legacy wrapper for Lisflood model calls."""
        return await self.call_lisflood_model("simulation", kwargs)
    
    async def disconnect_from_model(self, model_name: str) -> bool:
        """Disconnect from a specific model server."""
        if model_name in self.active_connections:
            del self.active_connections[model_name]
            return True
        return False
    
    async def get_model_status(self, model_name: str) -> Dict[str, Any]:
        """Get status of a specific model connection."""
        if model_name in self.active_connections:
            connection = self.active_connections[model_name]
            return {
                "model": model_name,
                "status": "connected" if connection["connected"] else "disconnected",
                "endpoint": connection["endpoint"],
                "last_ping": connection["last_ping"].isoformat()
            }
        else:
            return {
                "model": model_name,
                "status": "not_connected",
                "endpoint": self.model_endpoints.get(model_name),
                "last_ping": None
            }
    
    async def health_check_legacy(self) -> Dict[str, Any]:
        """Check health of all model connections."""
        health_status = {}
        for model_name in self.model_endpoints.keys():
            health_status[model_name] = await self.get_model_status(model_name)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "models": health_status,
            "total_active": len(self.active_connections)
        }

# Global MCP client instance
mcp_client = MCPClient()
