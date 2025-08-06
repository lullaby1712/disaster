"""Main entry point for the Emergency Management System.

This module provides both direct FastAPI server execution and LangGraph dev compatibility.
The system can be started in two ways:
1. Using LangGraph CLI: `langgraph dev` (recommended for development)
2. Direct execution: `python src/main.py` (alternative method)
"""

import sys
import os
import asyncio
import uvicorn
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

# --- Import dotenv and load environment variables ---
from dotenv import load_dotenv
load_dotenv()
# ----------------------------------------

# Add project root to Python path
# 这一步是为了确保可以正确导入 `src.agent.graph` 和其他模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- Import Langfuse and create a global instance ---
# This is a key modification: after importing the class, you need to instantiate it.
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler # 导入回调处理器

# 确保环境变量已设置，否则实例化将失败。
try:
    langfuse_client = Langfuse(
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
        host=os.environ.get("LANGFUSE_HOST")
    )
    # 创建一个全局的 Langfuse 回调处理器实例
    langfuse_handler = CallbackHandler()
    print("Langfuse client initialized successfully.")
except Exception as e:
    # 如果初始化失败，我们可以打印警告但继续运行，因为 LangGraph 已经配置了 Langfuse
    print(f"⚠️ Langfuse client initialization failed: {e}. Running without tracing.")
    langfuse_handler = None
    langfuse_client = None
# -------------------------------------------

# 从 agent.graph 导入我们的 LangGraph 实例和处理函数
# 这是修复后的导入路径
from src.agent.graph import process_emergency_event, get_system_health
from src.core.config import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown tasks."""
    # Startup
    print("Emergency Management System starting up...")
    # Perform any initialization here
    try:
        # Test the graph initialization health
        health_status = await get_system_health()
        print(f"System health check passed: {health_status['system_health']['overall_status']}")
    except Exception as e:
        print(f"⚠️ System health check warning: {e}")
    
    print("Emergency Management System ready!")
    yield
    
    # Shutdown
    print("Emergency Management System shutting down...")
    # --- Modification: Flush and close the Langfuse client instance upon application shutdown ---
    if langfuse_client:
        print("Flushing Langfuse events...")
        langfuse_client.flush()
        langfuse_client.shutdown()
        print("Langfuse client shut down.")
    # ----------------------------------------------------


app = FastAPI(
    title=config.app_title,
    description=config.app_description,
    version=config.app_version,
    lifespan=lifespan
)
@app.get("/")
async def root():
    """提供系统信息的根端点。"""
    return {
        "message": "欢迎使用应急管理系统 API！",
        "version": config.app_version,
        "status": "operational",
        "endpoints": {
            "health": "/system_health",
            "process": "/process_emergency_event",
            "docs": "/docs"
        }
    }
# --- Add CORS middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
# -----------------------------

# --- API Endpoints ---

@app.post("/process_emergency_event")
async def process_emergency_event_api(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an emergency event and get the final report, including a human-readable summary.
    """
    try:
        if not input_data:
            raise HTTPException(status_code=400, detail="Missing 'input_data' in request body")
        
        # Process the emergency event through the graph
        # process_emergency_event 现在会返回包含 final_report 和 human_readable_summary 的完整 state
        result_state = await process_emergency_event(input_data)
        
        # 提取并返回需要的字段
        final_report = result_state.get("final_report", {})
        human_readable_summary = result_state.get("human_readable_summary", "抱歉，无法生成摘要。")

        return {
            "final_report": final_report,
            "human_readable_summary": human_readable_summary
        }
        
    except Exception as e:
        # Improved error handling for better debugging
        print(f"Emergency processing failed: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail=f"Emergency processing failed: {str(e)}")


@app.get("/system_health")
async def get_system_health_api():
    """Get overall system health status."""
    try:
        return await get_system_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/graph/info")
async def get_graph_info():
    """Get information about the graph structure."""
    # 更新节点列表，包含新的摘要生成节点
    return {
        "graph_type": "EmergencyManagementGraph",
        "nodes": [
            "input_processing",
            "threat_detection", 
            "alert_generation",
            "agent_coordination",
            "response_execution",
            "damage_assessment",
            "reporting",
            "generate_human_readable_summary" # 新增节点
        ],
        "entry_point": "input_processing",
        "description": "Multi-agent emergency management workflow"
    }


def main():
    """Main function for direct execution."""
    print("Starting Emergency Management System directly...")
    print("For development, consider using: langgraph dev")
    print("API documentation will be available at: http://127.0.0.1:2024/docs")
    
    # Start the FastAPI server
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=2024,
        reload=True,
        log_level="info",
        reload_dirs=["src"]
    )


if __name__ == "__main__":
    main()
