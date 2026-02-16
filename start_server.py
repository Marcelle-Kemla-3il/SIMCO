#!/usr/bin/env python3
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the app
import uvicorn

if __name__ == "__main__":
    print("Starting SIMCO server on http://127.0.0.1:8000")
    print("Demo page available at: http://127.0.0.1:8000/demo")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
