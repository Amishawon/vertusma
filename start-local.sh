#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install -r requirements.txt
else
  . .venv/bin/activate
fi
python app.py
