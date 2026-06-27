#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
pip install -q flask 2>/dev/null || true
python3 mini_sap_pm_web.py