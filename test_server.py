#!/usr/bin/env python3
"""
Test script for Emergency Management System server endpoints.

This script tests both the LangGraph dev server and direct FastAPI server
to ensure they respond correctly to requests.
"""

import asyncio
import json
import sys
from typing import Dict, Any
import aiohttp
import time


async def test_endpoint(session: aiohttp.ClientSession, url: str, method: str = "GET", data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Test a single endpoint and return the result."""
    try:
        if method.upper() == "GET":
            async with session.get(url) as response:
                status = response.status
                content = await response.json()
                return {"success": True, "status": status, "data": content}
        elif method.upper() == "POST":
            async with session.post(url, json=data) as response:
                status = response.status
                content = await response.json()
                return {"success": True, "status": status, "data": content}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def test_server_health():
    """Test server health endpoint."""
    print("🔍 Testing server health...")
    
    base_url = "http://127.0.0.1:2024"
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        # Test root endpoint
        print("  📍 Testing root endpoint...")
        result = await test_endpoint(session, f"{base_url}/")
        if result["success"]:
            print(f"    ✅ Root endpoint: Status {result['status']}")
            if result["status"] == 200:
                print(f"    📝 Message: {result['data'].get('message', 'N/A')}")
        else:
            print(f"    ❌ Root endpoint failed: {result['error']}")
            return False
        
        # Test health endpoint
        print("  🏥 Testing health endpoint...")
        result = await test_endpoint(session, f"{base_url}/system_health")
        if result["success"]:
            print(f"    ✅ Health endpoint: Status {result['status']}")
            if result["status"] == 200:
                system_health = result['data'].get('system_health', {})
                print(f"    📊 Overall status: {system_health.get('overall_status', 'Unknown')}")
        else:
            print(f"    ❌ Health endpoint failed: {result['error']}")
            return False
        
        return True


async def test_emergency_processing():
    """Test emergency event processing endpoint."""
    print("🚨 Testing emergency processing...")
    
    base_url = "http://127.0.0.1:2024"
    
    # Sample test data
    test_input_data = {
        "input_data": {
            "user_question": "Test question: What should I do in case of a wildfire?",
            "region": "California",
            "emergency_type": "wildfire",
            "severity_level": "medium",
            "timestamp": "2024-01-15T10:30:00Z",
            "model_info": {
                "name": "test_model",
                "type": "emergency_analysis"
            },
            "datasets": [
                {"name": "fire_risk_data", "source": "NFDRS"}
            ]
        }
    }
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        print("  🔄 Sending emergency processing request...")
        result = await test_endpoint(
            session, 
            f"{base_url}/process_emergency_event",
            method="POST",
            data=test_input_data
        )
        
        if result["success"]:
            print(f"    ✅ Emergency processing: Status {result['status']}")
            if result["status"] == 200:
                response_data = result['data']
                if 'final_report' in response_data:
                    print("    📋 Final report generated successfully")
                    final_report = response_data['final_report']
                    
                    # Check for key components
                    if 'processing_log' in final_report:
                        print(f"    📝 Processing steps: {len(final_report['processing_log'])}")
                    if 'alerts' in final_report:
                        print(f"    🚨 Alerts generated: {len(final_report.get('alerts', []))}")
                    if 'recommendations' in final_report:
                        print(f"    💡 Recommendations: {len(final_report.get('recommendations', []))}")
                else:
                    print("    ⚠️  No final_report in response")
            else:
                print(f"    ❌ Unexpected status: {result['status']}")
                print(f"    📝 Response: {result['data']}")
        else:
            print(f"    ❌ Emergency processing failed: {result['error']}")
            return False
        
        return True


async def test_graph_info():
    """Test graph information endpoint (if available)."""
    print("📊 Testing graph info endpoint...")
    
    base_url = "http://127.0.0.1:2024"
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        result = await test_endpoint(session, f"{base_url}/graph/info")
        if result["success"]:
            print(f"    ✅ Graph info: Status {result['status']}")
            if result["status"] == 200:
                graph_info = result['data']
                print(f"    🏗️  Graph type: {graph_info.get('graph_type', 'Unknown')}")
                print(f"    🔗 Nodes: {len(graph_info.get('nodes', []))}")
                print(f"    🚪 Entry point: {graph_info.get('entry_point', 'Unknown')}")
        else:
            print(f"    ℹ️  Graph info endpoint not available: {result['error']}")
        
        return True


async def main():
    """Main test function."""
    print("=" * 60)
    print("🧪 EMERGENCY MANAGEMENT SYSTEM - SERVER TESTS")
    print("=" * 60)
    print()
    
    # Check if server is running
    print("🔍 Checking if server is running on http://127.0.0.1:2024...")
    print()
    
    # Wait a moment for server to be ready
    await asyncio.sleep(2)
    
    try:
        # Run all tests
        tests = [
            ("Server Health", test_server_health),
            ("Emergency Processing", test_emergency_processing),
            ("Graph Information", test_graph_info),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"🧪 Running test: {test_name}")
            try:
                success = await test_func()
                results.append((test_name, success))
                print(f"   {'✅ PASSED' if success else '❌ FAILED'}")
            except Exception as e:
                print(f"   ❌ FAILED with exception: {e}")
                results.append((test_name, False))
            print()
        
        # Print summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"  {test_name:<25} {status}")
        
        print()
        print(f"📈 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Server is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check server configuration.")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test script failed: {e}")
        sys.exit(1)