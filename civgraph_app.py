"""
CivGraph — Standalone application launcher.

Opens the browser automatically and runs the server.
Used as the entry point for the PyInstaller binary.
"""

import os
import sys
import threading
import time
import webbrowser

# When running as a PyInstaller bundle, adjust the working directory
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
    # Add the bundle directory to the path
    bundle_dir = sys._MEIPASS
    sys.path.insert(0, bundle_dir)
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

PORT = 8420
HOST = "127.0.0.1"


def open_browser():
    """Open browser after a short delay to let the server start."""
    time.sleep(2)
    webbrowser.open(f"http://{HOST}:{PORT}")


def main():
    print(f"""
    +-----------------------------------------+
    |            C I V G R A P H              |
    |   Agent-Based Urban Social Dynamics     |
    +-----------------------------------------+

    Starting server on http://{HOST}:{PORT}
    Opening browser...

    Press Ctrl+C to quit.
    """)

    # Open browser in a background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Start the server
    import uvicorn
    uvicorn.run(
        "server:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
