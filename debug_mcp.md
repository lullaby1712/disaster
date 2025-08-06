# MCP Inspector 调试指导

## 1. 安装 MCP Inspector

```bash
# 安装 MCP Inspector
npm install -g @modelcontextprotocol/inspector

# 或者使用 npx (推荐)
npx @modelcontextprotocol/inspector@latest
```

## 2. 启动 MCP Server 进行调试

### 方法1: 直接启动单个服务器
```bash
# 启动 Climada MCP 服务器
python -m src.MCP.servers.climada_server

# 启动 Lisflood MCP 服务器  
python -m src.MCP.servers.lisflood_server

# 启动主 MCP 服务器
python -m src.MCP.server
```

### 方法2: 使用 MCP Inspector 连接
```bash
# 连接到本地 MCP 服务器
npx @modelcontextprotocol/inspector python -m src.MCP.server

# 指定端口连接
npx @modelcontextprotocol/inspector --port 8000 python -m src.MCP.server

# 连接到特定模型服务器
npx @modelcontextprotocol/inspector python -m src.MCP.servers.climada_server
```

## 3. MCP Inspector 界面功能

### 3.1 工具检查
- **Tools**: 查看所有可用工具
- **Tool Schemas**: 检查工具参数定义
- **Tool Execution**: 测试工具调用

### 3.2 资源检查  
- **Resources**: 查看可用资源
- **Resource Content**: 检查资源内容

### 3.3 实时监控
- **Logs**: 查看服务器日志
- **Performance**: 监控性能指标
- **Error Tracking**: 错误追踪

## 4. 常用调试命令

### 4.1 健康检查
```bash
# 检查 MCP 服务器状态
curl http://localhost:8000/health

# 使用 Python 检查
python -c "
import asyncio
from src.MCP.client import mcp_client
asyncio.run(mcp_client.health_check())
"
```

### 4.2 工具测试
```python
# 测试 Climada 工具
import asyncio
from src.MCP.client import mcp_client

async def test_climada():
    result = await mcp_client.execute_tool(
        'climada_impact_assessment',
        {
            'hazard_type': 'wildfire',
            'location': {'lat': 37.7749, 'lng': -122.4194},
            'intensity': 0.8
        }
    )
    print(result)

asyncio.run(test_climada())
```

### 4.3 环境验证
```python
# 验证 Conda 环境
import asyncio
from src.MCP.core.environment_manager import environment_manager

async def check_environments():
    envs = await environment_manager.list_environments()
    for env in envs:
        print(f"Environment: {env['name']} - Path: {env['path']}")
        validation = await environment_manager.validate_environment(env['name'])
        print(f"Validation: {validation}")

asyncio.run(check_environments())
```

## 5. 调试配置文件

创建 `debug_config.json`:
```json
{
  "mcp_servers": {
    "climada": {
      "command": "python",
      "args": ["-m", "src.MCP.servers.climada_server"],
      "env": {
        "CLIMADA_HOST": "/data/Tiaozhanbei/Climada",
        "CONDA_BASE_PATH": "/home/lenovo/anaconda3"
      }
    },
    "lisflood": {
      "command": "python", 
      "args": ["-m", "src.MCP.servers.lisflood_server"],
      "env": {
        "LISFLOOD_HOST": "/data/Tiaozhanbei/Lisflood"
      }
    }
  },
  "inspector_config": {
    "port": 3001,
    "auto_connect": true,
    "log_level": "debug"
  }
}
```

## 6. 故障排除

### 6.1 常见问题
1. **端口冲突**: 更改 `MCP_BASE_PORT` 环境变量
2. **路径错误**: 检查 `.env` 文件中的路径配置
3. **依赖缺失**: 验证 Conda 环境和包安装
4. **权限问题**: 确保对模型目录有读取权限

### 6.2 日志调试
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看 MCP 日志
from src.MCP.core.router import mcp_router
mcp_router.enable_debug_logging()
```

### 6.3 性能监控
```bash
# 使用 htop 监控系统资源
htop

# 监控网络连接
netstat -tlnp | grep :8000

# 检查 Python 进程
ps aux | grep python
```

## 7. 自动化测试脚本

创建测试脚本 `test_mcp.py`:
```python
#!/usr/bin/env python3
import asyncio
import json
from src.MCP.client import mcp_client

async def run_tests():
    """运行 MCP 系统测试套件"""
    
    # 1. 健康检查
    print("1. Health Check...")
    health = await mcp_client.health_check()
    print(f"Health Status: {health}")
    
    # 2. 列出工具
    print("\\n2. Available Tools...")
    tools = await mcp_client.list_available_tools()
    for tool in tools[:5]:  # 显示前5个工具
        print(f"  - {tool['name']}: {tool['description']}")
    
    # 3. 测试工具执行
    print("\\n3. Testing Tool Execution...")
    if tools:
        test_result = await mcp_client.execute_tool(
            tools[0]['name'], 
            {}  # 空参数测试
        )
        print(f"Test Result: {test_result}")
    
    print("\\nMCP Testing Complete!")

if __name__ == "__main__":
    asyncio.run(run_tests())
```

运行测试:
```bash
python test_mcp.py
```