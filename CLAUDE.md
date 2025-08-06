# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
- Run unit tests: `make test` or `python -m pytest tests/unit_tests/`
- Run integration tests: `make integration_tests` or `python -m pytest tests/integration_tests`
- Run specific test file: `make test TEST_FILE=tests/unit_tests/test_configuration.py`
- Watch mode for tests: `make test_watch`

### Code Quality
- Format code: `make format` (uses ruff)
- Lint code: `make lint` (runs ruff check, format --diff, and mypy)
- Type check: `python -m mypy --strict src/`

### Installation & Setup
- Install dependencies: `pip install -e . "langgraph-cli[inmem]"`
- Start LangGraph server: `langgraph dev`
- Copy environment file: `cp .env.example .env` (configure API keys)

## Architecture Overview

This is an **emergency management multi-agent system** built with LangGraph that processes disaster events through a coordinated workflow:

### Core Workflow (src/agent/graph.py)
The main `EmergencyManagementGraph` processes disasters through these phases:
1. **Input Processing** - Multi-modal input (sensor, text, images) → structured data
2. **Threat Detection** - Analyze indicators → classify disaster type & severity  
3. **Alert Generation** - Create alerts based on threat levels
4. **Agent Coordination** - Activate disaster experts via coordinator
5. **Response Execution** - Deploy resources and response teams
6. **Damage Assessment** - Use CLIMADA model for impact analysis
7. **Reporting** - Generate comprehensive final reports

### Multi-Agent System
- **Disaster Coordinator** (`src/agent/coordinator.py`) - Central orchestrator that:
  - Assesses situations and classifies disaster types
  - Activates appropriate expert agents
  - Coordinates resource allocation
  - Monitors response progress

- **Disaster Experts** (`src/agent/disaster_experts.py`) - Specialized agents for:
  - **WildfireExpert** - Fire behavior analysis, suppression strategies
  - **FloodExpert** - Flood risk assessment, evacuation planning  
  - **EarthquakeExpert** - Seismic analysis, search & rescue coordination
  - **HurricaneExpert** - Storm impact assessment, evacuation timing

### External Model Integration (MCP)
- **MCP Client** (`src/MCP/client.py`) - Connects to disaster simulation models:
  - Cell2Fire (wildfire spread)
  - CLIMADA (damage assessment)
  - LisFlood (flood modeling)
  - NFDRS4 (fire danger rating)
  - Pangu/Aurora (weather prediction)

### Core Infrastructure
- **Models** (`src/core/models.py`) - Data structures for disasters, locations, alerts
- **Configuration** (`src/core/config.py`) - API keys, MCP endpoints, disaster thresholds
- **LLM Client** (`src/core/llm.py`) - DeepSeek API integration for analysis
- **Database** (`src/core/database.py`) - Event storage and retrieval

## Key Design Patterns

### State Management
Each workflow maintains state dictionaries that flow through LangGraph nodes, accumulating:
- Processed inputs, threat detections, coordination results
- Processing logs for debugging and audit trails

### Agent Coordination  
The coordinator uses a hub-and-spoke model where it:
- Receives alerts → classifies disasters → activates relevant experts
- Collects expert analyses → synthesizes coordination plans → allocates resources

### Model Integration
MCP (Model Context Protocol) provides standardized interface to various disaster models, allowing the system to:
- Query multiple models in parallel
- Combine predictions for better accuracy
- Handle model failures gracefully

## Configuration Notes

### Environment Variables
- `DEEPSEEK_API_KEY` - For LLM analysis (required)
- `LANGFUSE_*` - For observability and tracing
- `*_HOST` variables - Paths to disaster model installations

### LangGraph Configuration
- Graph entry point: `src/agent/graph.py:graph`
- Dependency: Current directory (`.`)
- Uses Wolfi Linux distribution for containerization