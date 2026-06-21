#!/usr/bin/env python3
"""
Quran Page Viewer - Main Script
Runs the full pipeline: scrape data, download fonts, export protobuf, then serve.
"""

import argparse
import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STEPS = [
    ("Scrape verse data", "scraper.py"),
    ("Download TTF fonts", "download_fonts.py"),
    ("Export protobuf", "convert_to_pb.py"),
]


def run_step(name, script):
    print(f"\n{'=' * 50}")
    print(f"  {name}")
    print(f"{'=' * 50}\n")
    result = subprocess.run([sys.executable, os.path.join(BASE_DIR, script)])
    if result.returncode != 0:
        print(f"\nFailed at: {name}")
        sys.exit(result.returncode)


def serve(port):
    print(f"\n{'=' * 50}")
    print(f"  Serving at http://localhost:{port}")
    print(f"{'=' * 50}\n")
    subprocess.run([sys.executable, "-m", "http.server", str(port)], cwd=BASE_DIR)


def main():
    parser = argparse.ArgumentParser(description="Quran Page Viewer pipeline")
    parser.add_argument("command", nargs="?", default="all",
                        choices=["all", "scrape", "fonts", "protobuf", "serve"],
                        help="Step to run (default: all)")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port for the web server (default: 8000)")
    args = parser.parse_args()

    commands = {
        "scrape": [STEPS[0]],
        "fonts": [STEPS[1]],
        "protobuf": [STEPS[2]],
        "all": STEPS,
    }

    if args.command == "serve":
        serve(args.port)
        return

    for name, script in commands[args.command]:
        run_step(name, script)

    if args.command == "all":
        serve(args.port)


if __name__ == "__main__":
    main()