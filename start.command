#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Menjalankan Noah Stream di http://localhost:3000 ..."
(sleep 1 && open "http://localhost:3000") &
python3 server.py

