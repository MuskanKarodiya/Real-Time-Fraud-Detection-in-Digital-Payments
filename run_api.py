"""
Run script for the Fraud Detection API

Usage:
    python run_api.py         # Development mode with auto-reload
    python run_api.py --prod  # Production mode
"""
import uvicorn
import sys

if __name__ == "__main__":
    PORT = 8000

    if "--prod" in sys.argv:
        # Production mode: use 0.0.0.0 for external access (EC2, Docker)
        HOST = "0.0.0.0"
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            reload=False,
            workers=4
        )
    else:
        # Development mode: use 127.0.0.1 for Windows compatibility
        HOST = "127.0.0.1"
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            reload=True
        )
