"""Serve the built React app and FastAPI on the hosting provider's single port."""

import argparse
import os
from pathlib import Path
import sys

import uvicorn


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrueTicket 단일 서버")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--strictPort", action="store_true")
    args = parser.parse_args()
    os.environ["TRUETICKET_FEED_PORT"] = str(args.port)
    uvicorn.run("backend.app.main:app", host=args.host, port=args.port, workers=1)
