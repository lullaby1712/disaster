"""PostGIS database connection and operations for disaster management platform."""
import os
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncpg
import json
from dataclasses import asdict

from .models import DisasterEvent, ModelResult, Location, DisasterType


class PostGISDatabase:
    """PostGIS database manager for storing disaster management data."""
    
    def __init__(self):
        """Initialize database connection parameters."""
        self.db_config = {
            'user': 'zs_zzr',
            'password': '373291Moon',
            'host': 'localhost',
            'port': 5432,
            'database': 'zs_data'
        }
        self.schema = 'public'
        self.pool = None
    
    async def connect(self) -> bool:
        """Establish connection pool to PostGIS database."""
        try:
            self.pool = await asyncpg.create_pool(
                **self.db_config,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            
            # Test connection and ensure PostGIS extension
            async with self.pool.acquire() as conn:
                # Check PostGIS extension
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')"
                )
                if not result:
                    await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                
                # Create tables if they don't exist
                await self._create_tables(conn)
                
            print("✅ Connected to PostGIS database successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to PostGIS database: {e}")
            return False
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
    
    async def _create_tables(self, conn):
        """Create necessary tables for disaster management data."""
        
        # Disaster events table
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.disaster_events (
                id SERIAL PRIMARY KEY,
                event_id VARCHAR(100) UNIQUE NOT NULL,
                disaster_type VARCHAR(50) NOT NULL,
                alert_level VARCHAR(20) NOT NULL,
                location GEOMETRY(POINT, 4326),
                region VARCHAR(100),
                description TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                confidence FLOAT,
                status VARCHAR(20) DEFAULT 'active',
                metadata JSONB
            )
        """)
        
        # Model results table
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.model_results (
                id SERIAL PRIMARY KEY,
                result_id VARCHAR(100) UNIQUE NOT NULL,
                event_id VARCHAR(100) REFERENCES {self.schema}.disaster_events(event_id),
                model_name VARCHAR(50) NOT NULL,
                disaster_type VARCHAR(50) NOT NULL,
                prediction JSONB NOT NULL,
                confidence FLOAT,
                processing_time FLOAT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                input_data JSONB
            )
        """)
        
        # Sensor data table
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.sensor_data (
                id SERIAL PRIMARY KEY,
                sensor_id VARCHAR(100) NOT NULL,
                sensor_type VARCHAR(50) NOT NULL,
                location GEOMETRY(POINT, 4326),
                measurement_type VARCHAR(50) NOT NULL,
                value FLOAT NOT NULL,
                unit VARCHAR(20),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                quality_score FLOAT DEFAULT 1.0,
                metadata JSONB
            )
        """)
        
        # Response actions table
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.response_actions (
                id SERIAL PRIMARY KEY,
                action_id VARCHAR(100) UNIQUE NOT NULL,
                event_id VARCHAR(100) REFERENCES {self.schema}.disaster_events(event_id),
                action_type VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                priority VARCHAR(20) DEFAULT 'medium',
                assigned_resources JSONB,
                start_time TIMESTAMP WITH TIME ZONE,
                end_time TIMESTAMP WITH TIME ZONE,
                success_rate FLOAT,
                notes TEXT
            )
        """)
        
        # Create spatial indexes
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_disaster_events_location 
            ON {self.schema}.disaster_events USING GIST (location)
        """)
        
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_sensor_data_location 
            ON {self.schema}.sensor_data USING GIST (location)
        """)
        
        print("✅ Database tables created/verified successfully")
    
    async def save_disaster_event(self, event_data: Dict[str, Any]) -> bool:
        """Save disaster event to database."""
        try:
            async with self.pool.acquire() as conn:
                # Extract location data
                location_data = event_data.get('location', {})
                lat = location_data.get('latitude')
                lon = location_data.get('longitude')
                
                # Create PostGIS point if coordinates available
                location_geom = None
                if lat is not None and lon is not None:
                    location_geom = f'POINT({lon} {lat})'
                
                await conn.execute(f"""
                    INSERT INTO {self.schema}.disaster_events 
                    (event_id, disaster_type, alert_level, location, region, 
                     description, confidence, metadata)
                    VALUES ($1, $2, $3, ST_GeomFromText($4, 4326), $5, $6, $7, $8)
                    ON CONFLICT (event_id) DO UPDATE SET
                        alert_level = EXCLUDED.alert_level,
                        description = EXCLUDED.description,
                        confidence = EXCLUDED.confidence,
                        metadata = EXCLUDED.metadata
                """, 
                    event_data.get('alert_id', event_data.get('event_id')),
                    event_data.get('disaster_type'),
                    event_data.get('alert_level'),
                    location_geom,
                    location_data.get('region'),
                    event_data.get('description'),
                    event_data.get('confidence'),
                    json.dumps(event_data.get('metadata', {}))
                )
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to save disaster event: {e}")
            return False
    
    async def save_model_result(self, model_result: ModelResult) -> bool:
        """Save model prediction result to database."""
        try:
            async with self.pool.acquire() as conn:
                result_dict = asdict(model_result)
                
                await conn.execute(f"""
                    INSERT INTO {self.schema}.model_results 
                    (result_id, model_name, disaster_type, prediction, 
                     confidence, processing_time, input_data)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                    f"{model_result.model_name}_{model_result.timestamp.strftime('%Y%m%d_%H%M%S')}",
                    model_result.model_name,
                    model_result.disaster_type.value,
                    json.dumps(model_result.prediction),
                    model_result.confidence,
                    model_result.processing_time,
                    json.dumps(model_result.input_data)
                )
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to save model result: {e}")
            return False
    
    async def save_sensor_data(self, sensor_data: Dict[str, Any]) -> bool:
        """Save sensor data to database."""
        try:
            async with self.pool.acquire() as conn:
                location_data = sensor_data.get('location', {})
                lat = location_data.get('latitude')
                lon = location_data.get('longitude')
                
                location_geom = None
                if lat is not None and lon is not None:
                    location_geom = f'POINT({lon} {lat})'
                
                await conn.execute(f"""
                    INSERT INTO {self.schema}.sensor_data 
                    (sensor_id, sensor_type, location, measurement_type, 
                     value, unit, quality_score, metadata)
                    VALUES ($1, $2, ST_GeomFromText($3, 4326), $4, $5, $6, $7, $8)
                """,
                    sensor_data.get('sensor_id'),
                    sensor_data.get('sensor_type'),
                    location_geom,
                    sensor_data.get('measurement_type'),
                    sensor_data.get('value'),
                    sensor_data.get('unit'),
                    sensor_data.get('quality_score', 1.0),
                    json.dumps(sensor_data.get('metadata', {}))
                )
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to save sensor data: {e}")
            return False
    
    async def get_events_in_area(self, lat: float, lon: float, radius_km: float = 10.0) -> List[Dict[str, Any]]:
        """Get disaster events within specified radius of a location."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT event_id, disaster_type, alert_level, 
                           ST_X(location) as longitude, ST_Y(location) as latitude,
                           region, description, timestamp, confidence, status, metadata
                    FROM {self.schema}.disaster_events
                    WHERE ST_DWithin(
                        location::geography, 
                        ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                        $3 * 1000
                    )
                    ORDER BY timestamp DESC
                """, lat, lon, radius_km)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"❌ Failed to query events in area: {e}")
            return []
    
    async def get_recent_sensor_data(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent sensor data within specified time window."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT sensor_id, sensor_type, 
                           ST_X(location) as longitude, ST_Y(location) as latitude,
                           measurement_type, value, unit, timestamp, quality_score, metadata
                    FROM {self.schema}.sensor_data
                    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                    ORDER BY timestamp DESC
                """)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"❌ Failed to query recent sensor data: {e}")
            return []
    
    async def update_event_status(self, event_id: str, status: str) -> bool:
        """Update disaster event status."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(f"""
                    UPDATE {self.schema}.disaster_events 
                    SET status = $2, timestamp = NOW()
                    WHERE event_id = $1
                """, event_id, status)
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to update event status: {e}")
            return False
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health info."""
        try:
            async with self.pool.acquire() as conn:
                # Get table counts
                event_count = await conn.fetchval(f"SELECT COUNT(*) FROM {self.schema}.disaster_events")
                result_count = await conn.fetchval(f"SELECT COUNT(*) FROM {self.schema}.model_results")
                sensor_count = await conn.fetchval(f"SELECT COUNT(*) FROM {self.schema}.sensor_data")
                
                # Get recent activity
                recent_events = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM {self.schema}.disaster_events 
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                """)
                
                return {
                    "database_status": "connected",
                    "table_counts": {
                        "disaster_events": event_count,
                        "model_results": result_count,
                        "sensor_data": sensor_count
                    },
                    "recent_activity": {
                        "events_last_24h": recent_events
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "database_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global database instance
postgis_db = PostGISDatabase()