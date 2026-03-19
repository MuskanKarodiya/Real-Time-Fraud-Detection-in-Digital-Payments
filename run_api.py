"""
Run script for the Fraud Detection API

Usage:
    python run_api.py         # Development mode with auto-reload
    python run_api.py --prod  # Production mode
"""
import uvicorn
import sys

if __name__ == "__main__":
    # Use 127.0.0.1 for Windows compatibility (0.0.0.0 doesn't work on Windows)
    HOST = "127.0.0.1"
    PORT = 8000

    if "--prod" in sys.argv:
        # Production mode
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            reload=False,
            workers=4
        )
    else:
        # Development mode with auto-reload
        uvicorn.run(
            "app.main:app",
            host=HOST,
            port=PORT,
            reload=True
        )
