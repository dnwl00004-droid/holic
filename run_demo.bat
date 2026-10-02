@echo off
echo Open http://localhost:8000
python -m http.server 8000 -d web
pause
