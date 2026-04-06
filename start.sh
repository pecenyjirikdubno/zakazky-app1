#!/bin/bash
# start.sh – startovací skript pro Render

# 1️⃣ Inicializace databáze (jen pokud tabulky ještě nejsou)
python init_db.py

# 2️⃣ Spuštění aplikace přes Gunicorn
exec gunicorn app:app \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 2 \
    --timeout 120
