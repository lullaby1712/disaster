#!/usr/bin/env python3
"""
Test script to verify the LangGraph fix is working correctly.

This script tests:
1. That the graph variable is now a proper StateGraph instance
2. That the module-level functions work correctly
3. That LangGraph CLI can recognize the graph
"""

import sys
import os
import asyncio
from typing import Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

def test_graph_variable():
    """Test that the graph variable is a StateGraph instance."""
    print("🧪 Testing graph variable type...")
    
    try:
        from src.agent.graph import graph
        from langgraph.pregel import Pregel
        
        # Check if graph is a StateGraph (compiled form is Pregel)
        if isinstance(graph, Pregel):
            print("  ✅ graph is a Pregel instance (compiled StateGraph)")
            return True
        else:
            print(f"  ❌ graph is {type(graph)}, expected Pregel")
            return False
            
    except Exception as e:
        print(f"  ❌ Failed to import or check graph: {e}")
        return False


def test_module_functions():
    """Test that the module-level functions are available."""
    print("🧪 Testing module-level functions...")
    
    try:
        from src.agent.graph import process_emergency_event, get_system_health
        
        # Check if they are callable
        if callable(process_emergency_event) and callable(get_system_health):
            print("  ✅ Module functions are callable")
            return True
        else:
            print("  ❌ Module functions are not callable")
            return False
            
    except ImportError as e:
        print(f"  ❌ Failed to import module functions: {e}")
        return False


async def test_function_execution():
    """Test that the module functions execute correctly."""
    print("🧪 Testing function execution...")
    
    try:
        from src.agent.graph import process_emergency_event, get_system_health
        
        # Test health check
        print("  🏥 Testing get_system_health...")
        health_result = await get_system_health()
        
        if isinstance(health_result, dict) and 'system_health' in health_result:
            print("  ✅ get_system_health works correctly")
            print(f"    Status: {health_result['system_health'].get('overall_status', 'Unknown')}")
        else:
            print("  ❌ get_system_health returned unexpected format")
            return False
        
        # Test emergency processing with minimal data
        print("  🚨 Testing process_emergency_event...")
        test_data = {
            "user_question": "Test question",
            "region": "Test Region",
            "emergency_type": "test",
            "severity_level": "low",
            "timestamp": "2024-01-15T10:30:00Z"
        }
        
        emergency_result = await process_emergency_event(test_data)
        
        if isinstance(emergency_result, dict) and 'final_report' in emergency_result:
            print("  ✅ process_emergency_event works correctly")
            print(f"    Generated report with {len(emergency_result['final_report'].get('processing_log', []))} log entries")
        else:
            print("  ❌ process_emergency_event returned unexpected format")
            return False
            
        return True
        
    except Exception as e:
        print(f"  ❌ Function execution failed: {e}")
        return False


def test_langgraph_config():
    """Test that langgraph.json points to the correct location."""
    print("🧪 Testing langgraph.json configuration...")
    
    try:
        import json
        
        with open("langgraph.json", "r") as f:
            config = json.load(f)
        
        expected_path = "./src/agent/graph.py:graph"
        actual_path = config.get("graphs", {}).get("agent")
        
        if actual_path == expected_path:
            print(f"  ✅ langgraph.json points to correct path: {actual_path}")
            return True
        else:
            print(f"  ❌ langgraph.json points to wrong path: {actual_path} (expected: {expected_path})")
            return False
            
    except Exception as e:
        print(f"  ❌ Failed to read langgraph.json: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 LANGGRAPH FIX VERIFICATION TESTS")
    print("=" * 60)
    print()
    
    tests = [
        ("Graph Variable Type", test_graph_variable, False),
        ("Module Functions", test_module_functions, False),
        ("LangGraph Config", test_langgraph_config, False),
        ("Function Execution", test_function_execution, True),  # This one is async
    ]
    
    results = []
    
    for test_name, test_func, is_async in tests:
        print(f"🧪 Running: {test_name}")
        try:
            if is_async:
                success = await test_func()
            else:
                success = test_func()
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
        print("🎉 All tests passed! The LangGraph fix is working correctly.")
        print()
        print("✨ You can now run:")
        print("   langgraph dev")
        print("   (The ValueError should be resolved)")
        return True
    else:
        print("⚠️  Some tests failed. The fix may need additional work.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test script failed: {e}")
        sys.exit(1)