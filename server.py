#!/usr/bin/env python3
"""GITNEWS — AI Proxy Server (news handled by frontend)."""
import http.server
import json
import urllib.request
import urllib.error
import os
import sys
import gzip
import time

PORT = int(os.environ.get('PORT', 8080))

# AI Cache
ai_cache = {}
ai_cache_lock = __import__('threading').Lock()
AI_CACHE_FILE = '/tmp/ai_cache.json'

def load_ai_cache():
    global ai_cache
    try:
        if os.path.exists(AI_CACHE_FILE):
            with open(AI_CACHE_FILE, 'r', encoding='utf-8') as f:
                ai_cache = json.load(f)
                print(f'[cache] loaded {len(ai_cache)} AI analyses')
                sys.stdout.flush()
    except:
        pass

def save_ai_cache():
    try:
        with open(AI_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(ai_cache, f)
    except:
        pass

class Handler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/':
            self._send_json({'status': 'ok', 'service': 'GITNEWS AI Proxy'})
            return
        if path == '/api/ai-cache':
            with ai_cache_lock:
                self._send_json({'cache': ai_cache, 'total': len(ai_cache)})
            return
        self.send_error(404)

    def do_POST(self):
        if self.path.startswith('/api/ai'):
            self._proxy_ai()
        else:
            self.send_error(404)

    def _proxy_ai(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            body_json = json.loads(body)
            api_key = os.environ.get('OPENAI_API_KEY', '')

            # Generate cache key from article title
            messages = body_json.get('messages', [])
            user_msg = next((m['content'] for m in messages if m.get('role') == 'user'), '')
            title_match = __import__('re').search(r'Title:\s*(.+)', user_msg)
            cache_key = title_match.group(1).strip()[:200] if title_match else user_msg[:200]

            # Check cache
            no_cache = 'nocache=1' in self.path
            if not no_cache:
                with ai_cache_lock:
                    if cache_key in ai_cache:
                        cached = ai_cache[cache_key]
                        if time.time() - cached.get('ts', 0) < 3600:
                            self._send_json(json.loads(cached['response']))
                            return

            req = urllib.request.Request(
                'https://opengateway.gitlawb.com/v1/chat/completions',
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}',
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read()

                # Cache result
                try:
                    result_json = json.loads(data)
                    content = result_json.get('choices', [{}])[0].get('message', {}).get('content', '')
                    if content:
                        with ai_cache_lock:
                            ai_cache[cache_key] = {
                                'response': data.decode('utf-8', errors='replace'),
                                'ts': time.time()
                            }
                            save_ai_cache()
                except:
                    pass

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self._cors()
                self.end_headers()
                self.wfile.write(data)

        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(err_body)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _send_json(self, data):
        raw = json.dumps(data).encode()
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._cors()
            self.end_headers()
            self.wfile.write(raw)
        except:
            pass

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def log_message(self, format, *args):
        pass

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except:
            pass

if __name__ == '__main__':
    print(f'GITNEWS AI Proxy running on port {PORT}')
    sys.stdout.flush()
    load_ai_cache()
    http.server.HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
