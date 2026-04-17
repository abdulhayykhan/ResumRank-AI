"""Vercel serverless entrypoint for the Flask app."""

import os
import sys

# Ensure project root is importable when running under Vercel's /var/task layout.
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app

# Vercel Python runtime looks for `app` (WSGI).
