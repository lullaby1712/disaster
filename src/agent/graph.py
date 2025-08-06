"""Main LangGraph implementation for the emergency management platform."""
import sys
import os
# 确保项目根目录在 Python 路径中，以便正确导入模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
import asyncio
import json # 新增：用于处理JSON
from typing import Dict, List, Any, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
load_dotenv()

# --- 导入 Langfuse 相关模块 ---
from langfuse import get_client # 用于获取 Langfuse 客户端实例
from langfuse.langchain import CallbackHandler # LangChain/LangGraph 的回调处理器
# ------------------------------------

# 从 src.core.models 导入数据模型
from src.core.models import (
    DisasterEvent, DisasterType, Location, AlertLevel,
    MultiModalInput, SensorData
)
# 从 src.core.llm 导入 LLM 客户端
from src.core.llm import llm_client
# 从 src.MCP.client 导入 MCP 客户端
from src.MCP.client import mcp_client
# 从 src.MCP.sdk 导入 MCP 工具执行器
from src.MCP.sdk import MCPClient, ToolExecutor as MCPToolExecutor
# 从 src.agent.coordinator 导入协调器实例
from src.agent.coordinator import disaster_coordinator

# --- 全局 Langfuse 客户端和回调处理器 ---
langfuse_client = get_client()
langfuse_handler = CallbackHandler()

if langfuse_client.auth_check():
    print("Langfuse client is authenticated and ready in graph.py!")
else:
    print("Authentication failed in graph.py. Please check your Langfuse credentials and host.")
# ----------------------------------------


class EmergencyManagementGraph:
    """Main graph for emergency management multi-agent system."""
    
    def __init__(self):
        # self.graph 将存储编译后的 LangGraph 实例
        self.graph = self._build_graph()
        # 协调器实例已在文件顶部定义并导入
        self.coordinator = disaster_coordinator
    
    def _build_graph(self) -> StateGraph:
        """Build the main emergency management workflow graph."""
        
        workflow = StateGraph(dict)
        
        # 添加各个节点到工作流中
        # 这些节点方法都定义在 EmergencyManagementGraph 类内部
        workflow.add_node("input_processing", self._process_input)
        workflow.add_node("threat_detection", self._detect_threats)
        workflow.add_node("alert_generation", self._generate_alerts)
        workflow.add_node("agent_coordination", self._coordinate_agents)
        workflow.add_node("response_execution", self._execute_response)
        workflow.add_node("damage_assessment", self._assess_damage)
        workflow.add_node("reporting", self._generate_reports)
        # 新增一个生成人类可读摘要的节点
        workflow.add_node("generate_human_readable_summary", self._generate_human_readable_summary)
        
        # 定义工作流的边
        workflow.set_entry_point("input_processing")
        
        workflow.add_edge("input_processing", "threat_detection")
        workflow.add_edge("threat_detection", "alert_generation")
        workflow.add_edge("alert_generation", "agent_coordination")
        workflow.add_edge("agent_coordination", "response_execution")
        workflow.add_edge("response_execution", "damage_assessment")
        workflow.add_edge("damage_assessment", "reporting")
        # 将 "reporting" 节点连接到新的摘要生成节点
        workflow.add_edge("reporting", "generate_human_readable_summary")
        # 将新的摘要生成节点连接到 END
        workflow.add_edge("generate_human_readable_summary", END)
        
        # 编译工作流，并配置 Langfuse 回调
        return workflow.compile().with_config({"callbacks": [langfuse_handler]})
    
    async def _process_input(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process multi-modal input data."""
        
        input_data = state.get("input", {})
        
        # 从前端输入中提取特定选择，并存储到 state 中
        state["selected_region"] = input_data.get("region", "Unknown")
        state["selected_model_choice"] = input_data.get("model", {})
        state["selected_datasets"] = input_data.get("datasets", [])

        # Create MultiModalInput object
        multi_input = MultiModalInput(
            input_id=f"input_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            input_type=input_data.get("type", "sensor"),
            content=input_data.get("content", {}),
            metadata=input_data.get("metadata", {}),
            timestamp=datetime.now(),
            location=Location(
                latitude=input_data.get("latitude", 0.0),
                longitude=input_data.get("longitude", 0.0),
                region=input_data.get("region", "Unknown")
            ) if input_data.get("latitude") else None
        )
        
        # Process with LLM
        processed_data = await llm_client.process_multimodal_input(
            multi_input.to_dict(),
            multi_input.input_type
        )
        
        state["processed_input"] = processed_data
        state["multi_input"] = multi_input
        state["processing_log"] = state.get("processing_log", []) + [f"Input processed at {datetime.now()}"]
        return state
    
    async def _detect_threats(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Detect potential disaster threats from processed input."""
        
        processed_input = state.get("processed_input", {})
        multi_input = state.get("multi_input")
        
        # Threat detection logic
        disaster_indicators = processed_input.get("disaster_indicators", [])
        severity_indicators = processed_input.get("severity", "unknown")
        
        # Calculate threat level
        threat_score = 0.0
        detected_threats = []
        
        for indicator in disaster_indicators:
            if any(keyword in indicator.lower() for keyword in [
                "fire", "smoke", "burn", "heat", "flame"
            ]):
                threat_score += 0.3
                detected_threats.append({
                    "type": "wildfire",
                    "indicator": indicator,
                    "confidence": 0.7
                })
            
            elif any(keyword in indicator.lower() for keyword in [
                "flood", "water", "rain", "overflow", "surge"
            ]):
                threat_score += 0.3
                detected_threats.append({
                    "type": "flood",
                    "indicator": indicator,
                    "confidence": 0.8
                })
            
            elif any(keyword in indicator.lower() for keyword in [
                "earthquake", "seismic", "tremor", "shake", "quake"
            ]):
                threat_score += 0.4
                detected_threats.append({
                    "type": "earthquake",
                    "indicator": indicator,
                    "confidence": 0.9
                })
            
            elif any(keyword in indicator.lower() for keyword in [
                "hurricane", "storm", "wind", "cyclone", "typhoon"
            ]):
                threat_score += 0.3
                detected_threats.append({
                    "type": "hurricane",
                    "indicator": indicator,
                    "confidence": 0.75
                })
        
        # Determine alert level
        if threat_score >= 0.8:
            alert_level = AlertLevel.CRITICAL
        elif threat_score >= 0.6:
            alert_level = AlertLevel.HIGH
        elif threat_score >= 0.3:
            alert_level = AlertLevel.MODERATE
        else:
            alert_level = AlertLevel.LOW
        
        state["threat_detection"] = {
            "threat_score": threat_score,
            "detected_threats": detected_threats,
            "alert_level": alert_level,
            "detection_timestamp": datetime.now().isoformat()
        }
        
        state["processing_log"].append(f"Threats detected: {len(detected_threats)} (score: {threat_score:.2f})")
        
        return state
    
    async def _generate_alerts(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate disaster alerts based on threat detection."""
        
        threat_detection = state.get("threat_detection", {})
        multi_input = state.get("multi_input")
        
        detected_threats = threat_detection.get("detected_threats", [])
        alert_level = threat_detection.get("alert_level", AlertLevel.LOW)
        
        alerts = []
        
        for threat in detected_threats:
            if threat.get("confidence", 0) > 0.5:
                event_id = f"alert_{threat['type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                alert = {
                    "alert_id": event_id,
                    "disaster_type": threat["type"],
                    "alert_level": alert_level.value,
                    "confidence": threat["confidence"],
                    "location": multi_input.location.to_dict() if multi_input and multi_input.location else {},
                    "description": f"Potential {threat['type']} detected: {threat['indicator']}",
                    "timestamp": datetime.now().isoformat(),
                    "requires_immediate_response": alert_level in [AlertLevel.HIGH, AlertLevel.CRITICAL],
                    "estimated_impact": self._estimate_impact(threat, alert_level)
                }
                
                alerts.append(alert)
        
        state["alerts"] = alerts
        state["processing_log"].append(f"Generated {len(alerts)} alerts")
        
        return state
    
    def _estimate_impact(self, threat: Dict[str, Any], alert_level: AlertLevel) -> Dict[str, Any]:
        """Estimate potential impact of the threat."""
        
        base_impact = {
            "estimated_affected_population": 1000,
            "estimated_affected_area": 10.0,  # km²
            "economic_impact_estimate": 1000000,  # USD
            "infrastructure_risk": "moderate"
        }
        
        # Adjust based on alert level
        multiplier = {
            AlertLevel.LOW: 0.5,
            AlertLevel.MODERATE: 1.0,
            AlertLevel.HIGH: 2.0,
            AlertLevel.CRITICAL: 3.0
        }.get(alert_level, 1.0)
        
        # Adjust based on disaster type
        disaster_multipliers = {
            "wildfire": 1.2,
            "flood": 1.5,
            "earthquake": 2.0,
            "hurricane": 1.8
        }
        
        disaster_multiplier = disaster_multipliers.get(threat.get("type", ""), 1.0)
        final_multiplier = multiplier * disaster_multiplier
        
        return {
            "estimated_affected_population": int(base_impact["estimated_affected_population"] * final_multiplier),
            "estimated_affected_area": base_impact["estimated_affected_area"] * final_multiplier,
            "economic_impact_estimate": int(base_impact["economic_impact_estimate"] * final_multiplier),
            "infrastructure_risk": "critical" if final_multiplier > 2.5 else "high" if final_multiplier > 1.5 else "moderate"
        }
    
    async def _coordinate_agents(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate multi-agent response."""
        
        alerts = state.get("alerts", [])
        
        coordination_results = []
        
        for alert in alerts:
            if alert.get("requires_immediate_response", False):
                # Use the disaster coordinator for multi-agent coordination
                coordination_input = {
                    "type": "alert",
                    "alert_data": alert,
                    "location": alert.get("location", {}),
                    "severity": alert.get("alert_level", "moderate")
                }
                
                try:
                    # 调用全局的 disaster_coordinator 实例
                    coordination_result = await self.coordinator.process_disaster_alert(coordination_input)
                    coordination_results.append(coordination_result)
                except Exception as e:
                    coordination_results.append({
                        "error": str(e),
                        "alert_id": alert.get("alert_id", "unknown")
                    })
        
        state["coordination_results"] = coordination_results
        state["processing_log"].append(f"Coordinated response for {len(coordination_results)} critical alerts")
        
        return state
    
    async def _execute_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coordinated response actions."""
        
        coordination_results = state.get("coordination_results", [])
        
        response_execution = []
        
        for result in coordination_results:
            if "final_report" in result:
                final_report = result["final_report"]
                coordination_summary = final_report.get("coordination_summary", {})
                
                # Simulate response execution
                execution_result = {
                    "event_id": coordination_summary.get("event_id", "unknown"),
                    "execution_timestamp": datetime.now().isoformat(),
                    "deployed_resources": result.get("resource_allocation", {}),
                    "response_teams": coordination_summary.get("activated_experts", []),
                    "execution_status": "in_progress",
                    "estimated_completion": "4-6 hours",
                    "success_probability": final_report.get("success_probability", 0.7)
                }
                
                response_execution.append(execution_result)
        
        state["response_execution"] = response_execution
        state["processing_log"].append(f"Initiated response execution for {len(response_execution)} events")
        
        return state
    
    async def _assess_damage(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Assess damage using MCP tools (CLIMADA and Lisflood models)."""
        
        coordination_results = state.get("coordination_results", [])
        threat_detection = state.get("threat_detection", {})
        
        damage_assessments = []
        
        # Initialize MCP client
        async with MCPClient() as mcp_client_instance: # 避免和全局的 mcp_client 变量冲突，改名
            executor = MCPToolExecutor(mcp_client_instance)
            
            for result in coordination_results:
                # 假设 result 中包含可以用于评估的事件数据
                if "disaster_event" in result:
                    disaster_event_data = result["disaster_event"]
                    
                    # Extract location and disaster info
                    location_data = disaster_event_data.get("location", {})
                    disaster_type_str = disaster_event_data.get("disaster_type", "wildfire")
                    event_id = disaster_event_data.get("event_id", "unknown")
                    
                    try:
                        assessment_tasks = []
                        
                        # Use Climada for impact assessment
                        if disaster_type_str.lower() in ["hurricane", "wildfire", "earthquake", "flood"]:
                            assessment_tasks.append(
                                executor.run_climada_impact_assessment(
                                    hazard_type=disaster_type_str.lower(),
                                    region=location_data.get("region", "Unknown"),
                                    year_range=[2020, 2024]
                                )
                            )
                            
                            # Add exposure analysis
                            if "country_iso" in location_data:
                                assessment_tasks.append(
                                    executor.run_climada_exposure_analysis(
                                        country_iso=location_data["country_iso"],
                                        exposure_type="litpop"
                                    )
                                )
                            
                        # Use Lisflood for flood-related disasters
                        if disaster_type_str.lower() in ["flood", "hurricane", "storm"]:
                            assessment_tasks.append(
                                executor.run_lisflood_simulation(
                                    start_date="2024-01-01",
                                    end_date="2024-12-31",
                                    settings_file=f"config/{location_data.get('region', 'default')}_settings.xml",
                                    output_dir=f"./damage_assessment/{event_id}"
                                )
                            )
                            
                        # Execute all assessment tasks
                        if assessment_tasks:
                            assessment_results = await asyncio.gather(*assessment_tasks, return_exceptions=True)
                            
                            # Process results
                            damage_assessment = {
                                "event_id": event_id,
                                "disaster_type": disaster_type_str,
                                "location": location_data,
                                "assessment_timestamp": datetime.now().isoformat(),
                                "models_used": [],
                                "results": {}
                            }
                            
                            for i, result in enumerate(assessment_results):
                                if isinstance(result, Exception):
                                    damage_assessment["results"][f"assessment_{i}"] = {
                                        "error": str(result),
                                        "status": "failed"
                                    }
                                else:
                                    # Determine which model was used based on index and conditions
                                    # 注意：这里需要更精确地判断是哪个工具的结果，可以根据返回的结构或之前定义
                                    # 的顺序进行判断。这里的逻辑可能需要根据MCPToolExecutor的实际返回调整。
                                    if i == 0 and disaster_type_str.lower() in ["hurricane", "wildfire", "earthquake", "flood"]:
                                        damage_assessment["models_used"].append("climada_impact")
                                        damage_assessment["results"]["climada_impact"] = result
                                    elif "country_iso" in location_data and len(assessment_tasks) > 1 and i == 1: # 如果 Climada impact 和 exposure 都运行
                                        damage_assessment["models_used"].append("climada_exposure")
                                        damage_assessment["results"]["climada_exposure"] = result
                                    elif disaster_type_str.lower() in ["flood", "hurricane", "storm"]: # Lisflood
                                        # Lisflood 可能是第二个或第三个任务，取决于之前的条件
                                        # 更严谨的判断需要基于 assessment_tasks 的具体内容
                                        damage_assessment["models_used"].append("lisflood_simulation")
                                        damage_assessment["results"]["lisflood_simulation"] = result
                                    
                                    # Generate summary metrics
                                    damage_assessment["summary"] = self._generate_damage_summary(
                                        damage_assessment["results"], 
                                        disaster_type_str
                                    )
                                    
                            damage_assessments.append(damage_assessment)
                        else:
                            # No applicable models found
                            damage_assessments.append({
                                "event_id": event_id,
                                "disaster_type": disaster_type_str,
                                "error": "No applicable damage assessment models for this disaster type",
                                "status": "skipped"
                            })
                            
                    except Exception as e:
                        damage_assessments.append({
                            "event_id": event_id,
                            "disaster_type": disaster_type_str,
                            "error": str(e),
                            "status": "failed"
                        })
        
        state["damage_assessments"] = damage_assessments
        state["processing_log"].append(f"Completed damage assessment for {len(damage_assessments)} events using MCP tools")
        
        return state
    
    def _generate_damage_summary(self, results: Dict[str, Any], disaster_type: str) -> Dict[str, Any]:
        """Generate summary metrics from damage assessment results."""
        summary = {
            "total_economic_damage": 0,
            "affected_population": 0,
            "risk_level": "unknown",
            "confidence": 0.0
        }
        
        try:
            # Process Climada impact results
            if "climada_impact" in results:
                climada_data = results["climada_impact"].get("data", {})
                if "economic_damage" in climada_data:
                    summary["total_economic_damage"] = climada_data["economic_damage"]
                if "affected_population" in climada_data:
                    summary["affected_population"] = climada_data["affected_population"]
                if "confidence" in climada_data:
                    summary["confidence"] = max(summary["confidence"], climada_data["confidence"])
            
            # Process Lisflood results for flood impact
            if "lisflood_simulation" in results:
                lisflood_data = results["lisflood_simulation"].get("data", {})
                if "max_water_depth" in lisflood_data:
                    depth = lisflood_data["max_water_depth"]
                    if depth > 2.0:
                        summary["risk_level"] = "high"
                    elif depth > 1.0:
                        summary["risk_level"] = "medium"
                    else:
                        summary["risk_level"] = "low"
            
            # Determine overall risk level
            if summary["total_economic_damage"] > 5000000:  # $5M threshold
                summary["risk_level"] = "critical"
            elif summary["total_economic_damage"] > 1000000:  # $1M threshold
                summary["risk_level"] = "high"
            elif summary["total_economic_damage"] > 100000:  # $100K threshold
                summary["risk_level"] = "medium"
            else:
                summary["risk_level"] = "low"
                
        except Exception as e:
            summary["error"] = f"Failed to generate summary: {str(e)}"
        
        return summary
    
    async def _generate_reports(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive reports."""
        
        # Compile all information into final report
        final_report = {
            "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "report_timestamp": datetime.now().isoformat(),
            "processing_summary": {
                "input_processed": bool(state.get("processed_input")),
                "threats_detected": len(state.get("threat_detection", {}).get("detected_threats", [])),
                "alerts_generated": len(state.get("alerts", [])),
                "coordination_executed": len(state.get("coordination_results", [])),
                "response_initiated": len(state.get("response_execution", [])),
                "damage_assessed": len(state.get("damage_assessments", []))
            },
            "alerts": state.get("alerts", []),
            "coordination_results": state.get("coordination_results", []),
            "response_execution": state.get("response_execution", []),
            "damage_assessments": state.get("damage_assessments", []),
            "processing_log": state.get("processing_log", []),
            "system_status": "operational",
            "recommendations": [
                "Continue monitoring situation",
                "Maintain resource readiness",
                "Update stakeholders",
                "Prepare for potential escalation"
            ]
        }
        
        state["final_report"] = final_report
        state["processing_log"].append("Final report generated")
        
        return state

    async def _generate_human_readable_summary(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据最终报告，生成一个友好、人类可读的自然语言摘要。
        """
        final_report = state.get("final_report")
        if not final_report:
            state["human_readable_summary"] = "抱歉，系统处理失败，无法生成报告。"
            return state

        # 构造 LLM Prompt
        prompt = f"""
        你是一位专业的应急管理助手。你刚刚完成了对一个突发事件的分析。
        请根据以下JSON格式的分析报告，用简洁、友好、自然语言的方式，向用户进行口头汇报。
        你需要覆盖以下要点：
        1. 报告摘要，说明事件是否被成功处理。
        2. 如果有威胁被检测到，请说明威胁的类型和数量。
        3. 如果有警报生成，请说明警报的数量和级别。
        4. 如果有模型被调用，请说明调用的模型和结果摘要。
        
        以下是详细的JSON报告：
        {json.dumps(final_report, ensure_ascii=False, indent=2)}

        请直接输出口头汇报内容，不要包含任何多余的解释。
        """
        
        messages = [{"role": "system", "content": prompt}]
        
        try:
            summary = await llm_client.generate_response(messages=messages, temperature=0.2)
            state["human_readable_summary"] = summary.strip()
        except Exception as e:
            state["human_readable_summary"] = f"抱歉，分析完成，但生成摘要时发生错误：{e}。"
            
        return state
    
    async def process_emergency(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for processing emergency situations."""
        initial_state = {"input": input_data}
        
        # 调用编译后的图，它会执行整个工作流，包括生成人类可读摘要
        result = await self.graph.ainvoke(initial_state)
        
        # 返回整个状态字典，其中包含 final_report 和 human_readable_summary
        return result
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        
        # Check MCP connections
        mcp_health = await mcp_client.health_check()
        
        # Get coordinator status
        coordinator_status = await self.coordinator.get_system_status()
        
        return {
            "system_health": {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy",
                "mcp_connections": mcp_health,
                "coordinator_status": coordinator_status,
                "graph_status": "operational"
            }
        }

# Create global graph manager instance for API endpoints
_graph_manager = EmergencyManagementGraph()

# Expose the StateGraph instance for LangGraph CLI
# 这个 'graph' 变量现在包含了 Langfuse 的追踪配置
graph = _graph_manager.graph

# Expose manager methods for API endpoints
async def process_emergency_event(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process emergency event through the graph manager."""
    # 直接调用 _graph_manager 的方法，该方法会触发已配置 Langfuse 的 graph.ainvoke
    return await _graph_manager.process_emergency(input_data)

async def get_system_health() -> Dict[str, Any]:
    """Get system health from the graph manager."""
    return await _graph_manager.get_system_health()
