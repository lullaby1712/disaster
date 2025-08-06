#!/usr/bin/env python3
"""
MCP Server Manager for Emergency Management System.

This module manages multiple MCP servers and provides a unified interface
for starting, stopping, and monitoring all disaster model servers.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manager for multiple MCP servers."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "mcp_servers.yaml"
        self.servers: Dict[str, subprocess.Popen] = {}
        self.server_configs = {}
        self.running = False
        
        # Load server configurations
        self._load_config()
    
    def _load_config(self):
        """Load MCP server configurations."""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                self.server_configs = config.get('servers', {})
                logger.info(f"Loaded configuration for {len(self.server_configs)} servers")
            except Exception as e:
                logger.error(f"Failed to load config file {config_path}: {e}")
                self._create_default_config()
        else:
            logger.info(f"Config file {config_path} not found, creating default")
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default server configuration."""
        self.server_configs = {
            "climada": {
                "module": "src.MCP.servers.climada_server",
                "description": "CLIMADA climate risk assessment",
                "port": 8001,
                "environment": "climada",
                "enabled": True,
                "restart_on_failure": True
            },
            "lisflood": {
                "module": "src.MCP.servers.lisflood_server",
                "description": "LISFLOOD hydrological modeling",
                "port": 8002,
                "environment": "lisflood",
                "enabled": True,
                "restart_on_failure": True
            },
            "cell2fire": {
                "module": "src.MCP.servers.cell2fire_server",
                "description": "Cell2Fire wildfire simulation",
                "port": 8003,
                "environment": "cell2fire",
                "enabled": True,
                "restart_on_failure": True
            },
            "pangu": {
                "module": "src.MCP.servers.pangu_server",
                "description": "Pangu Weather forecasting",
                "port": 8004,
                "environment": "pangu",
                "enabled": True,
                "restart_on_failure": True
            },
            "aurora": {
                "module": "src.MCP.servers.aurora_server",
                "description": "Aurora atmospheric modeling",
                "port": 8005,
                "environment": "aurora",
                "enabled": True,
                "restart_on_failure": True
            },
            "nfdrs4": {
                "module": "src.MCP.servers.nfdrs4_server",
                "description": "NFDRS4 fire danger rating",
                "port": 8006,
                "environment": "nfdrs4",
                "enabled": True,
                "restart_on_failure": True
            },
            "filesystem": {
                "module": "src.MCP.servers.filesystem_server",
                "description": "Secure filesystem operations",
                "port": 8007,
                "environment": "base",
                "enabled": True,
                "restart_on_failure": True
            },
            "postgresql": {
                "module": "src.MCP.servers.postgresql_server",
                "description": "PostgreSQL database access",
                "port": 8008,
                "environment": "base",
                "enabled": False,  # Requires database setup
                "restart_on_failure": True
            }
        }
        
        # Save default config
        self._save_config()
    
    def _save_config(self):
        """Save current configuration to file."""
        config = {
            "servers": self.server_configs,
            "global_settings": {
                "log_level": "INFO",
                "restart_delay": 5,
                "max_restarts": 3
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    async def start_server(self, server_name: str) -> bool:
        """Start a specific MCP server."""
        if server_name not in self.server_configs:
            logger.error(f"Unknown server: {server_name}")
            return False
        
        config = self.server_configs[server_name]
        if not config.get("enabled", True):
            logger.info(f"Server {server_name} is disabled")
            return False
        
        if server_name in self.servers and self.servers[server_name].poll() is None:
            logger.info(f"Server {server_name} is already running")
            return True
        
        try:
            # Prepare environment
            env = os.environ.copy()
            if "environment" in config and config["environment"] != "base":
                env["CONDA_DEFAULT_ENV"] = config["environment"]
            
            # Start server process
            cmd = [sys.executable, "-m", config["module"]]
            
            logger.info(f"Starting {server_name} server: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.servers[server_name] = process
            
            # Wait a moment to check if it started successfully
            await asyncio.sleep(1)
            
            if process.poll() is None:
                logger.info(f"Server {server_name} started successfully (PID: {process.pid})")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"Server {server_name} failed to start:")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to start server {server_name}: {e}")
            return False
    
    async def stop_server(self, server_name: str) -> bool:
        """Stop a specific MCP server."""
        if server_name not in self.servers:
            logger.info(f"Server {server_name} is not running")
            return True
        
        process = self.servers[server_name]
        
        try:
            if process.poll() is None:
                logger.info(f"Stopping server {server_name} (PID: {process.pid})")
                
                # Try graceful shutdown first
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    await asyncio.wait_for(
                        asyncio.create_task(self._wait_for_process(process)),
                        timeout=10
                    )
                    logger.info(f"Server {server_name} stopped gracefully")
                except asyncio.TimeoutError:
                    # Force kill if graceful shutdown fails
                    logger.warning(f"Server {server_name} did not stop gracefully, force killing")
                    process.kill()
                    await asyncio.create_task(self._wait_for_process(process))
            
            del self.servers[server_name]
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop server {server_name}: {e}")
            return False
    
    async def _wait_for_process(self, process: subprocess.Popen):
        """Wait for process to terminate."""
        while process.poll() is None:
            await asyncio.sleep(0.1)
    
    async def start_all_servers(self) -> Dict[str, bool]:
        """Start all enabled servers."""
        results = {}
        
        for server_name, config in self.server_configs.items():
            if config.get("enabled", True):
                logger.info(f"Starting {server_name}...")
                results[server_name] = await self.start_server(server_name)
            else:
                logger.info(f"Skipping disabled server: {server_name}")
                results[server_name] = False
        
        return results
    
    async def stop_all_servers(self) -> Dict[str, bool]:
        """Stop all running servers."""
        results = {}
        
        for server_name in list(self.servers.keys()):
            logger.info(f"Stopping {server_name}...")
            results[server_name] = await self.stop_server(server_name)
        
        return results
    
    async def restart_server(self, server_name: str) -> bool:
        """Restart a specific server."""
        logger.info(f"Restarting server {server_name}")
        
        stop_success = await self.stop_server(server_name)
        if not stop_success:
            logger.error(f"Failed to stop server {server_name}")
            return False
        
        # Wait a moment before restarting
        await asyncio.sleep(2)
        
        start_success = await self.start_server(server_name)
        return start_success
    
    def get_server_status(self) -> Dict[str, Dict[str, any]]:
        """Get status of all servers."""
        status = {}
        
        for server_name, config in self.server_configs.items():
            server_status = {
                "enabled": config.get("enabled", True),
                "description": config.get("description", ""),
                "port": config.get("port"),
                "environment": config.get("environment", "base"),
                "running": False,
                "pid": None
            }
            
            if server_name in self.servers:
                process = self.servers[server_name]
                if process.poll() is None:
                    server_status["running"] = True
                    server_status["pid"] = process.pid
                    
            status[server_name] = server_status
        
        return status
    
    async def health_check(self) -> Dict[str, Dict[str, any]]:
        """Perform health check on all servers."""
        status = self.get_server_status()
        
        # TODO: Add actual health checks by calling server endpoints
        # For now, just check if processes are running
        
        return status
    
    async def monitor_servers(self):
        """Monitor servers and restart failed ones."""
        logger.info("Starting server monitoring")
        
        while self.running:
            try:
                for server_name, config in self.server_configs.items():
                    if not config.get("enabled", True):
                        continue
                    
                    if server_name not in self.servers:
                        continue
                    
                    process = self.servers[server_name]
                    
                    # Check if process is still running
                    if process.poll() is not None:
                        logger.warning(f"Server {server_name} has stopped unexpectedly")
                        
                        if config.get("restart_on_failure", True):
                            logger.info(f"Attempting to restart {server_name}")
                            del self.servers[server_name]  # Remove dead process
                            await self.start_server(server_name)
                        else:
                            logger.info(f"Auto-restart disabled for {server_name}")
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in server monitoring: {e}")
                await asyncio.sleep(30)
    
    async def run(self):
        """Run the server manager."""
        self.running = True
        
        # Setup signal handlers
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, self._signal_handler)
        
        try:
            # Start all enabled servers
            logger.info("Starting MCP Server Manager")
            start_results = await self.start_all_servers()
            
            successful_starts = sum(1 for success in start_results.values() if success)
            logger.info(f"Started {successful_starts}/{len(start_results)} servers")
            
            # Start monitoring
            await self.monitor_servers()
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.shutdown()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    async def shutdown(self):
        """Shutdown all servers."""
        logger.info("Shutting down MCP Server Manager")
        self.running = False
        
        stop_results = await self.stop_all_servers()
        successful_stops = sum(1 for success in stop_results.values() if success)
        logger.info(f"Stopped {successful_stops}/{len(stop_results)} servers")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Server Manager for Emergency Management")
    parser.add_argument("--config", default="mcp_servers.yaml", help="Configuration file path")
    parser.add_argument("--action", choices=["start", "stop", "restart", "status"], 
                       default="start", help="Action to perform")
    parser.add_argument("--server", help="Specific server name (optional)")
    
    args = parser.parse_args()
    
    manager = MCPServerManager(args.config)
    
    if args.action == "start":
        if args.server:
            success = await manager.start_server(args.server)
            sys.exit(0 if success else 1)
        else:
            await manager.run()
    
    elif args.action == "stop":
        if args.server:
            success = await manager.stop_server(args.server)
            sys.exit(0 if success else 1)
        else:
            await manager.stop_all_servers()
    
    elif args.action == "restart":
        if args.server:
            success = await manager.restart_server(args.server)
            sys.exit(0 if success else 1)
        else:
            await manager.stop_all_servers()
            await asyncio.sleep(2)
            await manager.start_all_servers()
    
    elif args.action == "status":
        status = manager.get_server_status()
        print(json.dumps(status, indent=2))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)