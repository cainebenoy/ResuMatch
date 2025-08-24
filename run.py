#!/usr/bin/env python3
"""
ResuMatch Startup Script
Simple script to run the Flask application with proper error handling.
"""

import sys
import subprocess
import os

def check_dependencies():
    """Check if required packages are installed."""
    try:
        import flask
        import sklearn
        import flask_cors
        print("✓ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def main():
    """Main startup function."""
    print("🚀 Starting ResuMatch...")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print("\n📋 Starting Flask server...")
    print("🌐 Backend will be available at: http://localhost:5000")
    print("📱 Frontend: Open index.html in your browser")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Import and run the Flask app
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
