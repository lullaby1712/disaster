#!/usr/bin/env python3
"""
Server startup script for Emergency Management System.

This script provides multiple ways to start the server:
1. LangGraph Dev Mode (recommended for development)
2. Direct FastAPI Mode (alternative approach)
3. Production Mode (for deployment)
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = ['langgraph', 'fastapi', 'uvicorn']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("📦 Install with: pip install -e . \"langgraph-cli[inmem]\"")
        return False
    
    return True


def start_langgraph_dev():
    """Start the server using LangGraph CLI (recommended)."""
    print("🚀 Starting Emergency Management System with LangGraph Dev...")
    print("🌐 Server will be available at: http://127.0.0.1:2024")
    print("📚 API docs: http://127.0.0.1:2024/docs")
    print("🎨 LangGraph Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024")
    print("💡 This is the recommended development mode.")
    print("-" * 60)
    
    try:
        # Start langgraph dev
        subprocess.run(["langgraph", "dev"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start LangGraph dev: {e}")
        print("💡 Make sure langgraph-cli is installed: pip install \"langgraph-cli[inmem]\"")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return True
    
    return True


def start_direct_mode():
    """Start the server using direct FastAPI execution."""
    print("🚀 Starting Emergency Management System in Direct Mode...")
    print("🌐 Server will be available at: http://127.0.0.1:2024")
    print("📚 API docs: http://127.0.0.1:2024/docs")
    print("⚠️  Note: LangGraph Studio won't be available in this mode.")
    print("-" * 60)
    
    try:
        # Add current directory to Python path
        sys.path.insert(0, str(Path(__file__).parent))
        
        # Import and run the main function
        from src.main import main
        main()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return True
    except Exception as e:
        print(f"❌ Failed to start direct mode: {e}")
        return False


def start_production_mode():
    """Start the server in production mode with gunicorn."""
    print("🚀 Starting Emergency Management System in Production Mode...")
    print("🌐 Server will be available at: http://127.0.0.1:2024")
    print("⚠️  This is for production deployment only.")
    print("-" * 60)
    
    try:
        subprocess.run([
            "gunicorn", 
            "src.main:app",
            "-w", "4",  # 4 worker processes
            "-k", "uvicorn.workers.UvicornWorker",
            "--bind", "127.0.0.1:2024",
            "--timeout", "120"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start production mode: {e}")
        print("💡 Make sure gunicorn is installed: pip install gunicorn")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        return True


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Start the Emergency Management System server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_server.py                    # Default: LangGraph dev mode
  python start_server.py --mode dev         # LangGraph dev mode
  python start_server.py --mode direct      # Direct FastAPI mode  
  python start_server.py --mode production  # Production mode with gunicorn
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["dev", "direct", "production"],
        default="dev",
        help="Server startup mode (default: dev)"
    )
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 60)
    print("🚨 EMERGENCY MANAGEMENT SYSTEM 🚨")
    print("Multi-Agent Disaster Response Platform")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("⚠️  Warning: .env file not found")
        print("💡 Copy .env.example to .env and configure your API keys")
        print()
    
    # Start server based on mode
    success = False
    if args.mode == "dev":
        success = start_langgraph_dev()
    elif args.mode == "direct":
        success = start_direct_mode()
    elif args.mode == "production":
        success = start_production_mode()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()