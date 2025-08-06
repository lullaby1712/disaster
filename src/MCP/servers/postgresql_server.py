#!/usr/bin/env python3
"""
PostgreSQL MCP Server with schema checking for emergency management data.

This server provides read-only database access with schema validation
for emergency management system data.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import asyncpg
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

from ..core.base_model import BaseMCPModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PostgreSQLServer(BaseMCPModel):
    """PostgreSQL MCP Server with schema checking."""
    
    def __init__(self):
        super().__init__("postgresql", "Read-only PostgreSQL database access with schema validation")
        self.server = Server("postgresql-server")
        
        # Database connection parameters
        self.db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DB", "emergency_management"),
            "user": os.getenv("POSTGRES_USER", "readonly_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "")
        }
        
        # Allowed schemas and tables for security
        self.allowed_schemas = {
            "emergency_events",
            "disaster_assessments", 
            "resource_allocations",
            "weather_data",
            "geographic_data",
            "public"
        }
        
        # Read-only user restrictions
        self.allowed_operations = {"SELECT", "EXPLAIN", "SHOW"}
        
        self.connection_pool = None
        self._setup_tools()
        self._setup_resources()
    
    async def _get_connection(self) -> asyncpg.Connection:
        """Get database connection from pool."""
        if self.connection_pool is None:
            try:
                self.connection_pool = await asyncpg.create_pool(
                    **self.db_config,
                    min_size=1,
                    max_size=5,
                    command_timeout=30
                )
                logger.info("Database connection pool created")
            except Exception as e:
                logger.error(f"Failed to create database connection pool: {e}")
                raise
        
        return await self.connection_pool.acquire()
    
    def _validate_query(self, query: str) -> bool:
        """Validate that query is safe and read-only."""
        query_upper = query.upper().strip()
        
        # Check if query starts with allowed operations
        for operation in self.allowed_operations:
            if query_upper.startswith(operation):
                break
        else:
            return False
        
        # Forbidden keywords that could modify data
        forbidden_keywords = {
            "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", 
            "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
        }
        
        for keyword in forbidden_keywords:
            if keyword in query_upper:
                return False
        
        return True
    
    def _setup_tools(self):
        """Setup PostgreSQL tools."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            return [
                Tool(
                    name="execute_query",
                    description="Execute a read-only SQL query with schema validation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL query to execute (SELECT only)"
                            },
                            "parameters": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Query parameters for parameterized queries",
                                "default": []
                            },
                            "limit": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 1000,
                                "default": 100,
                                "description": "Maximum number of rows to return"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="describe_table",
                    description="Get schema information for a table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table to describe"
                            },
                            "schema_name": {
                                "type": "string",
                                "default": "public",
                                "description": "Schema name (default: public)"
                            }
                        },
                        "required": ["table_name"]
                    }
                ),
                Tool(
                    name="list_tables",
                    description="List all accessible tables in allowed schemas",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schema_name": {
                                "type": "string",
                                "description": "Schema name to list tables from (optional)"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_query_plan",
                    description="Get execution plan for a query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL query to analyze"
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            try:
                if name == "execute_query":
                    result = await self._execute_query(arguments)
                elif name == "describe_table":
                    result = await self._describe_table(arguments)
                elif name == "list_tables":
                    result = await self._list_tables(arguments)
                elif name == "get_query_plan":
                    result = await self._get_query_plan(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _setup_resources(self):
        """Setup PostgreSQL resources."""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            return [
                Resource(
                    uri="postgresql://schemas",
                    name="Database Schemas",
                    description="Available database schemas for emergency management",
                    mimeType="application/json"
                ),
                Resource(
                    uri="postgresql://emergency_events",
                    name="Emergency Events Data",
                    description="Historical emergency events and incidents",
                    mimeType="application/json"
                ),
                Resource(
                    uri="postgresql://disaster_assessments",
                    name="Disaster Assessments",
                    description="Damage assessments and impact evaluations",
                    mimeType="application/json"
                ),
                Resource(
                    uri="postgresql://weather_data",
                    name="Weather Data",
                    description="Historical and current weather observations",
                    mimeType="application/json"
                )
            ]
    
    async def _execute_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a read-only SQL query."""
        query = params["query"].strip()
        query_params = params.get("parameters", [])
        limit = params.get("limit", 100)
        
        # Validate query safety
        if not self._validate_query(query):
            raise ValueError("Query contains forbidden operations or keywords")
        
        # Add LIMIT if not present
        if "LIMIT" not in query.upper() and query.upper().startswith("SELECT"):
            query += f" LIMIT {limit}"
        
        try:
            conn = await self._get_connection()
            try:
                # Execute query
                if query_params:
                    rows = await conn.fetch(query, *query_params)
                else:
                    rows = await conn.fetch(query)
                
                # Convert to list of dictionaries
                results = []
                for row in rows:
                    results.append(dict(row))
                
                return {
                    "query": query,
                    "row_count": len(results),
                    "results": results,
                    "status": "success"
                }
                
            finally:
                await self.connection_pool.release(conn)
                
        except asyncpg.PostgresError as e:
            logger.error(f"Database error: {e}")
            return {
                "query": query,
                "error": str(e),
                "error_code": e.sqlstate if hasattr(e, 'sqlstate') else None,
                "status": "error"
            }
    
    async def _describe_table(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get table schema information."""
        table_name = params["table_name"]
        schema_name = params.get("schema_name", "public")
        
        if schema_name not in self.allowed_schemas:
            raise PermissionError(f"Access denied to schema: {schema_name}")
        
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns 
        WHERE table_schema = $1 AND table_name = $2
        ORDER BY ordinal_position
        """
        
        try:
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(query, schema_name, table_name)
                
                columns = []
                for row in rows:
                    columns.append({
                        "name": row["column_name"],
                        "type": row["data_type"],
                        "nullable": row["is_nullable"] == "YES",
                        "default": row["column_default"],
                        "max_length": row["character_maximum_length"],
                        "precision": row["numeric_precision"],
                        "scale": row["numeric_scale"]
                    })
                
                # Get table constraints
                constraint_query = """
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_schema = $1 AND table_name = $2
                """
                
                constraint_rows = await conn.fetch(constraint_query, schema_name, table_name)
                constraints = [dict(row) for row in constraint_rows]
                
                return {
                    "schema": schema_name,
                    "table": table_name,
                    "columns": columns,
                    "constraints": constraints,
                    "column_count": len(columns),
                    "status": "success"
                }
                
            finally:
                await self.connection_pool.release(conn)
                
        except asyncpg.PostgresError as e:
            return {
                "schema": schema_name,
                "table": table_name,
                "error": str(e),
                "status": "error"
            }
    
    async def _list_tables(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List accessible tables."""
        schema_name = params.get("schema_name")
        
        if schema_name and schema_name not in self.allowed_schemas:
            raise PermissionError(f"Access denied to schema: {schema_name}")
        
        if schema_name:
            query = """
            SELECT schemaname, tablename, tableowner, hasindexes, hasrules, hastriggers
            FROM pg_tables 
            WHERE schemaname = $1
            ORDER BY tablename
            """
            query_params = [schema_name]
        else:
            # List tables from all allowed schemas
            placeholders = ",".join(f"${i+1}" for i in range(len(self.allowed_schemas)))
            query = f"""
            SELECT schemaname, tablename, tableowner, hasindexes, hasrules, hastriggers
            FROM pg_tables 
            WHERE schemaname IN ({placeholders})
            ORDER BY schemaname, tablename
            """
            query_params = list(self.allowed_schemas)
        
        try:
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(query, *query_params)
                
                tables = []
                for row in rows:
                    tables.append({
                        "schema": row["schemaname"],
                        "name": row["tablename"],
                        "owner": row["tableowner"],
                        "has_indexes": row["hasindexes"],
                        "has_rules": row["hasrules"],
                        "has_triggers": row["hastriggers"]
                    })
                
                return {
                    "schema_filter": schema_name,
                    "tables": tables,
                    "table_count": len(tables),
                    "allowed_schemas": list(self.allowed_schemas),
                    "status": "success"
                }
                
            finally:
                await self.connection_pool.release(conn)
                
        except asyncpg.PostgresError as e:
            return {
                "schema_filter": schema_name,
                "error": str(e),
                "status": "error"
            }
    
    async def _get_query_plan(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get query execution plan."""
        query = params["query"].strip()
        
        if not self._validate_query(query):
            raise ValueError("Query contains forbidden operations or keywords")
        
        explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE FALSE) {query}"
        
        try:
            conn = await self._get_connection()
            try:
                rows = await conn.fetch(explain_query)
                plan = rows[0][0] if rows else {}
                
                return {
                    "query": query,
                    "execution_plan": plan,
                    "status": "success"
                }
                
            finally:
                await self.connection_pool.release(conn)
                
        except asyncpg.PostgresError as e:
            return {
                "query": query,
                "error": str(e),
                "status": "error"
            }


async def main():
    """Run the PostgreSQL MCP server."""
    server_instance = PostgreSQLServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="postgresql-server",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())