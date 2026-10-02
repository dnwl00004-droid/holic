"""Run: python start_dashboard.py (no external packages required to view)."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from functools import partial
import webbrowser
if __name__=='__main__':
    root=Path(__file__).resolve().parent/'web';url='http://127.0.0.1:8000'
    print('RS Radar: '+url+' — press Ctrl+C to stop')
    webbrowser.open(url)
    try:ThreadingHTTPServer(('127.0.0.1',8000),partial(SimpleHTTPRequestHandler,directory=str(root))).serve_forever()
    except KeyboardInterrupt:pass
