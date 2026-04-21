#!/bin/bash
# Run the Django dev server locally with SQLite (no Postgres needed).
# Usage: ./dev.sh
# Then open http://127.0.0.1:8000

BACKEND="$(cd "$(dirname "$0")" && pwd)/backend"
VENV="$BACKEND/.venv/bin/python"

if [ ! -f "$VENV" ]; then
  echo "ERROR: venv not found at $BACKEND/.venv"
  echo "Run: /usr/local/bin/python3.13 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt"
  exit 1
fi

cd "$BACKEND"

DATABASE_URL=sqlite:///db.sqlite3 \
  "$VENV" manage.py migrate --run-syncdb 2>&1 | tail -5

echo ""
echo "  Starting dev server → http://127.0.0.1:8000"
echo "  (Ctrl+C to stop)"
echo ""

DATABASE_URL=sqlite:///db.sqlite3 \
  "$VENV" manage.py runserver
