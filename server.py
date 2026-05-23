#!/usr/bin/env python3
"""GITNEWS — Server with AI proxy + RSS feed aggregation."""
import http.server
import json
import urllib.request
import urllib.error
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import threading
import time
import html
import re

PORT = int(os.environ.get('PORT', 8080))
DIR = os.path.dirname(os.path.abspath(__file__))

# RSS Feed Sources
RSS_FEEDS = [
    ('https://www.coindesk.com/arc/outboundfeeds/rss/', 'CoinDesk'),
    ('https://cointelegraph.com/rss', 'CoinTelegraph'),
    ('https://bitcoinmagazine.com/feed', 'Bitcoin Magazine'),
    ('https://decrypt.co/feed', 'Decrypt'),
    ('https://www.theblock.co/rss.xml', 'The Block'),
    ('https://blockworks.co/feed', 'Blockworks'),
    ('https://cryptonews.com/news/feed/', 'CryptoNews'),
    ('https://u.today/rss', 'U.Today'),
    ('https://beincrypto.com/feed/', 'BeInCrypto'),
    ('https://cryptoslate.com/feed/', 'CryptoSlate'),
    ('https://ambcrypto.com/feed/', 'AMBCrypto'),
    ('https://www.newsbtc.com/feed/', 'NewsBTC'),
    ('https://dailyhodl.com/feed/', 'Daily Hodl'),
    ('https://cryptobriefing.com/feed/', 'Crypto Briefing'),
    ('https://www.coingape.com/feed/', 'CoinGape'),
    ('https://coincodex.com/rss/news', 'CoinCodex'),
    ('https://www.investing.com/rss/news_301.rss', 'Investing.com Crypto'),
    ('https://bitcoinist.com/feed/', 'Bitcoinist'),
    ('https://www.financemagnates.com/cryptocurrency/feed/', 'Finance Magnates'),
    ('https://blog.kraken.com/feed', 'Kraken Blog'),
    ('https://blog.coinbase.com/feed', 'Coinbase Blog'),
    ('https://blog.binance.com/en/feed', 'Binance Blog'),
    ('https://defillama.com/rss', 'DefiLlama'),
    ('https://www.dlnews.com/arc/outboundfeeds/rss/', 'DL News'),
    ('https://techcrunch.com/category/crypto/feed/', 'TechCrunch Crypto'),
    ('https://nftnow.com/feed/', 'NFT Now'),
    ('https://www.thedefiant.io/feed', 'The Defiant'),
    ('https://unchainedcrypto.com/feed/', 'Unchained'),
    ('https://messari.io/rss', 'Messari'),
    # Global Macro & Geopolitics
    ('https://feeds.bbci.co.uk/news/world/rss.xml', 'BBC World'),
    ('https://rss.nytimes.com/services/xml/rss/nyt/World.xml', 'NYT World'),
    ('https://feeds.bbci.co.uk/news/business/rss.xml', 'BBC Business'),
    ('https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml', 'NYT Economy'),
    ('https://feeds.bbci.co.uk/news/technology/rss.xml', 'BBC Tech'),
    ('https://www.investing.com/rss/news.rss', 'Investing.com'),
    ('https://www.forexlive.com/feed/news', 'ForexLive'),
    ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC Top'),
    ('https://www.cnbc.com/id/100727362/device/rss/rss.html', 'CNBC Crypto'),
    ('https://www.marketwatch.com/rss/topstories', 'MarketWatch'),
    ('https://feeds.reuters.com/reuters/businessNews', 'Reuters Business'),
    ('https://feeds.reuters.com/reuters/worldNews', 'Reuters World'),
    # Regional Crypto
    ('https://es.cointelegraph.com/rss', 'CT Espa\u00f1ol'),
    ('https://br.cointelegraph.com/rss', 'CT Brasil'),
    ('https://jp.cointelegraph.com/rss', 'CT Japan'),
]

# Cache
news_cache = []
news_lock = threading.Lock()

def fetch_single_rss(url, source_name, timeout=8):
    """Fetch and parse a single RSS feed."""
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'GITNEWS/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode('utf-8', errors='replace')

        root = ET.fromstring(data)

        # Handle both RSS 2.0 and Atom
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        items = root.findall('.//item') or root.findall('.//atom:entry', ns)

        for item in items[:20]:
            title = (item.findtext('title') or item.findtext('atom:title', namespaces=ns) or '').strip()
            link = (item.findtext('link') or '')
            if not link:
                link_el = item.find('atom:link', ns)
                link = link_el.get('href', '') if link_el is not None else ''
            link = link.strip()

            desc = (item.findtext('description') or item.findtext('atom:summary', namespaces=ns) or '').strip()
            desc = re.sub(r'<[^>]+>', '', desc)[:200]
            if len(desc) >= 200:
                desc += '...'

            content = (item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or
                       item.findtext('atom:content', namespaces=ns) or desc)

            pub = (item.findtext('pubDate') or item.findtext('atom:published', namespaces=ns) or
                   item.findtext('atom:updated', namespaces=ns) or '')

            # Parse date
            ts = parse_date(pub)

            # Image
            image = ''
            enc = item.find('enclosure')
            if enc is not None and 'image' in (enc.get('type', '')):
                image = enc.get('url', '')
            if not image:
                media = item.find('{http://search.yahoo.com/mrss/}content')
                if media is not None:
                    image = media.get('url', '')
            if not image:
                thumb = item.find('{http://search.yahoo.com/mrss/}thumbnail')
                if thumb is not None:
                    image = thumb.get('url', '')

            # Categories
            cats = [c.text.strip() for c in item.findall('category') if c.text]

            if title and len(title) > 5:
                articles.append({
                    'id': f'{source_name}-{hash(title) % 10000000}',
                    'title': title,
                    'description': desc,
                    'body': content[:500] if content else desc,
                    'source': source_name,
                    'url': link,
                    'image': image,
                    'timestamp': ts,
                    'tags': cats,
                })
    except Exception as e:
        pass
    return articles

def parse_date(date_str):
    """Parse various date formats to timestamp."""
    if not date_str:
        return 0
    date_str = date_str.strip()
    # Normalize
    date_str = date_str.replace(' GMT', ' +0000').replace(' UTC', ' +0000')
    # Remove trailing timezone names that aren't offsets
    date_str = re.sub(r'\s+[A-Z]{2,4}$', '', date_str)

    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%d %b %Y %H:%M:%S',
        '%d %B %Y %H:%M:%S',
        '%b %d, %Y',
        '%B %d, %Y',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str[:35], fmt)
            ts = int(dt.timestamp() * 1000)
            if ts > 946684800000:  # After year 2000
                return ts
        except:
            pass

    # Last resort: try to extract date parts with regex
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return int(dt.timestamp() * 1000)
        except:
            pass

    return 0  # Return 0 if can't parse — don't use current time

def refresh_news():
    """Fetch all RSS feeds and update cache."""
    global news_cache
    all_articles = []

    threads = []
    results = [[] for _ in RSS_FEEDS]

    def fetcher(idx, url, name):
        results[idx] = fetch_single_rss(url, name)

    for i, (url, name) in enumerate(RSS_FEEDS):
        t = threading.Thread(target=fetcher, args=(i, url, name))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=12)

    for r in results:
        all_articles.extend(r)

    # Dedup
    seen = set()
    deduped = []
    for a in all_articles:
        key = re.sub(r'[^a-z0-9]', '', a['title'].lower())[:40]
        if key not in seen and len(key) > 5:
            seen.add(key)
            deduped.append(a)

    # Sort: articles with valid timestamps first (newest), then undated ones at bottom
    deduped.sort(key=lambda x: x['timestamp'] if x['timestamp'] > 0 else 0, reverse=True)

    with news_lock:
        news_cache = deduped

    print(f'[news] refreshed {len(deduped)} articles from {len(RSS_FEEDS)} sources')
    sys.stdout.flush()

def news_refresh_loop():
    """Background thread: refresh news every 2 minutes."""
    while True:
        refresh_news()
        time.sleep(120)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]

        if path == '/api/news':
            self._serve_news()
            return
        if path == '/api/ai':
            # Allow GET for AI too
            self.send_error(405, 'Use POST')
            return

        # Serve static files
        if path == '/':
            path = '/index.html'
        filepath = os.path.join(DIR, path.lstrip('/'))
        if os.path.isfile(filepath):
            ext = os.path.splitext(filepath)[1]
            content_types = {
                '.html': 'text/html; charset=utf-8',
                '.css': 'text/css; charset=utf-8',
                '.js': 'application/javascript; charset=utf-8',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon',
            }
            ct = content_types.get(ext, 'application/octet-stream')
            with open(filepath, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ct)
            self.send_header('Cache-Control', 'no-cache')
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/api/ai':
            self._proxy_ai()
        else:
            self.send_error(404)

    def _serve_news(self):
        with news_lock:
            raw = json.dumps({'articles': news_cache, 'total': len(news_cache), 'sources': len(RSS_FEEDS)}).encode()
        # Gzip compress to avoid BrokenPipeError on large responses
        import gzip
        compressed = gzip.compress(raw)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(compressed)))
        self._cors()
        self.end_headers()
        self.wfile.write(compressed)

    def _proxy_ai(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            auth = self.headers.get('Authorization', '')

            req = urllib.request.Request(
                'https://opengateway.gitlawb.com/v1/chat/completions',
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': auth,
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
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

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    print(f'GITNEWS running on http://localhost:{PORT}')
    sys.stdout.flush()

    # Start background news refresh
    t = threading.Thread(target=news_refresh_loop, daemon=True)
    t.start()

    http.server.HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
