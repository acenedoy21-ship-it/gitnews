#!/usr/bin/env python3
"""GITNEWS — Server with AI proxy + RSS feed aggregation."""
import http.server
import json
import urllib.request
import urllib.error
import os
import sys
import gzip
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
    ('https://es.cointelegraph.com/rss', 'CT Espa\u00f1ol'),
    ('https://br.cointelegraph.com/rss', 'CT Brasil'),
    ('https://jp.cointelegraph.com/rss', 'CT Japan'),
    # Reddit
    ('https://www.reddit.com/r/CryptoCurrency/hot/.rss', 'Reddit r/Crypto'),
    ('https://www.reddit.com/r/Bitcoin/hot/.rss', 'Reddit r/Bitcoin'),
    ('https://www.reddit.com/r/ethereum/hot/.rss', 'Reddit r/Ethereum'),
    ('https://www.reddit.com/r/CryptoMarkets/hot/.rss', 'Reddit r/CryptoMarkets'),
    ('https://www.reddit.com/r/defi/hot/.rss', 'Reddit r/DeFi'),
    ('https://www.reddit.com/r/SatoshiStreetBets/hot/.rss', 'Reddit r/SatoshiBets'),
    ('https://www.reddit.com/r/cryptocurrencynews/hot/.rss', 'Reddit r/CryptoNews'),
    # YouTube & Podcasts
    ('https://www.youtube.com/feeds/videos.xml?channel=UCqK_GSMbpiV8spgD3ZGloSw', 'Coin Bureau YT'),
    ('https://www.youtube.com/feeds/videos.xml?channel=UCjemQfjaXAvA0ACrMnF3QNg', 'BitBoy YT'),
    ('https://www.youtube.com/feeds/videos.xml?channel=UCRvqjQPSeaWn-uEx-w0XOIg', 'Digital Asset News YT'),
    ('https://www.youtube.com/feeds/videos.xml?channel=UCHbD1bKjB9uYjLPVQsOYBSA', 'Altcoin Daily YT'),
    ('https://www.youtube.com/feeds/videos.xml?channel=UCVLcl7oMMXRoJv6qI9fbhLw', 'Benjamin Cowen YT'),
    ('https://feeds.simplecast.com/JGE3yC0V', 'Bankless Podcast'),
    ('https://anchor.fm/s/171a868/podcast/rss', 'Unchained Podcast'),
    ('https://podcast.coingecko.com/feed', 'CoinGecko Podcast'),
    # Newsletter & Research
    ('https://www.theblock.co/rss/all', 'The Block All'),
    ('https://blog.chain.link/feed/', 'Chainlink Blog'),
    ('https://medium.com/feed/@VitalikButerin', 'Vitalik Blog'),
    ('https://medium.com/feed/l2beat', 'L2Beat Blog'),
    ('https://a16zcrypto.com/feed/', 'a16z Crypto'),
    ('https://paradigm.xyz/feed.xml', 'Paradigm Research'),
    ('https://www.circle.com/blog/rss.xml', 'Circle Blog'),
    ('https://blog.tether.to/feed/', 'Tether Blog'),
    ('https://medium.com/feed/the-ethereum-name-service', 'ENS Blog'),
    ('https://blog.opensea.io/rss', 'OpenSea Blog'),
    ('https://blog.uniswap.org/rss.xml', 'Uniswap Blog'),
    ('https://aave.com/blog/feed/', 'Aave Blog'),
    ('https://solana.com/news/rss.xml', 'Solana Blog'),
    ('https://polkadot.network/blog/feed/', 'Polkadot Blog'),
    ('https://cardanians.io/en/feed', 'Cardano Feed'),
    # Additional Crypto
    ('https://www.coindesk.com/arc/outboundfeeds/podcast/rss/', 'CoinDesk Podcast'),
    ('https://cointelegraph.com/editors_rss', 'CT Editors Pick'),
    ('https://www.investing.com/rss/news_285.rss', 'Investing.com Commodities'),
    ('https://www.investing.com/rss/news_14.rss', 'Investing.com Forex'),
    ('https://www.fxstreet.com/rss', 'FXStreet'),
    ('https://www.zerohedge.com/fullrss2.xml', 'ZeroHedge'),
    ('https://www.coindesk.com/arc/outboundfeeds/arc/outboundfeeds/rss/', 'CoinDesk All'),
    # Google News Crypto
    ('https://news.google.com/rss/search?q=cryptocurrency+bitcoin+crypto&hl=en-US&gl=US&ceid=US:en', 'Google News Crypto'),
    ('https://news.google.com/rss/search?q=ethereum+defi+web3&hl=en-US&gl=US&ceid=US:en', 'Google News DeFi'),
    ('https://news.google.com/rss/search?q=crypto+regulation+sec&hl=en-US&gl=US&ceid=US:en', 'Google News Regulation'),
    ('https://news.google.com/rss/search?q=war+conflict+sanctions+tariff&hl=en-US&gl=US&ceid=US:en', 'Google News Geopolitics'),
    ('https://news.google.com/rss/search?q=federal+reserve+inflation+recession&hl=en-US&gl=US&ceid=US:en', 'Google News Macro'),
    ('https://news.google.com/rss/search?q=banking+crisis+stock+market+crash&hl=en-US&gl=US&ceid=US:en', 'Google News Banking'),
    # More crypto media
    ('https://www.coingape.com/feed', 'CoinGape 2'),
    ('https://bitcoinmagazine.com/.rss/full/', 'Bitcoin Magazine Full'),
    ('https://cointelegraph.com/rss/category/altcoin-news', 'CT Altcoin'),
    ('https://cointelegraph.com/rss/category/regulation-news', 'CT Regulation'),
    ('https://cointelegraph.com/rss/category/defi-news', 'CT DeFi'),
    ('https://cointelegraph.com/rss/category/nft-news', 'CT NFT'),
    ('https://cointelegraph.com/rss/category/technology-news', 'CT Technology'),
    ('https://cryptonews.com/exclusive/feed/', 'CryptoNews Exclusive'),
    ('https://www.financemagnates.com/forex/feed/', 'Finance Magnates Forex'),
    ('https://www.financemagnates.com/fintech/feed/', 'Finance Magnates FinTech'),
]

# Cache
news_cache = []
news_lock = threading.Lock()
is_loading = True
NEWS_CACHE_FILE = '/tmp/news_cache.json'

# AI Cache
ai_cache = {}
ai_cache_lock = threading.Lock()
AI_CACHE_FILE = '/tmp/ai_cache.json'

# ===== CACHE PERSISTENCE =====
def save_json_cache(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except:
        pass

def load_json_cache(filepath, default=None):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return default if default is not None else {}

def load_all_caches():
    global news_cache, is_loading, ai_cache
    cached_news = load_json_cache(NEWS_CACHE_FILE, [])
    if cached_news and len(cached_news) > 0:
        with news_lock:
            news_cache = cached_news
            is_loading = False
        print(f'[cache] loaded {len(cached_news)} articles from disk')
    cached_ai = load_json_cache(AI_CACHE_FILE, {})
    if cached_ai:
        with ai_cache_lock:
            ai_cache = cached_ai
        print(f'[cache] loaded {len(cached_ai)} AI analyses from disk')
    sys.stdout.flush()

# ===== RSS PARSING =====
def fetch_single_rss(url, source_name, timeout=10):
    articles = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'GITNEWS/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode('utf-8', errors='replace')
        root = ET.fromstring(data)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        items = root.findall('.//item') or root.findall('.//atom:entry', ns)
        for item in items[:15]:
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
            ts = parse_date(pub)
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
    except Exception:
        pass
    return articles

def parse_date(date_str):
    if not date_str:
        return 0
    date_str = date_str.strip()
    date_str = date_str.replace(' GMT', ' +0000').replace(' UTC', ' +0000')
    date_str = re.sub(r'\s+[A-Z]{2,4}$', '', date_str)
    formats = [
        '%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S', '%Y-%m-%d',
        '%d %b %Y %H:%M:%S', '%d %B %Y %H:%M:%S',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str[:35], fmt)
            ts = int(dt.timestamp() * 1000)
            if ts > 946684800000:
                return ts
        except:
            pass
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return int(dt.timestamp() * 1000)
        except:
            pass
    return 0

# Placeholder images by category
PLACEHOLDER_IMAGES = {
    'bitcoin': 'https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=400',
    'ethereum': 'https://images.unsplash.com/photo-1622790698141-94e30467e1e3?w=400',
    'crypto': 'https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=400',
    'market': 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=400',
    'default': 'https://images.unsplash.com/photo-1516245834210-c4c142787335?w=400',
}

def is_crypto_related(article):
    """Check if article is related to crypto/blockchain/finance."""
    text = f"{article['title']} {article['description']} {' '.join(article.get('tags', []))}".lower()

    # Always pass if from crypto-specific source
    crypto_sources = [
        'coindesk', 'cointelegraph', 'bitcoin', 'decrypt', 'the block', 'blockworks',
        'cryptonews', 'beincrypto', 'cryptoslate', 'ambcrypto', 'newsbtc', 'daily hodl',
        'crypto brief', 'coingape', 'coincodex', 'bitcoinist', 'defillama', 'dl news',
        'nft now', 'thedefiant', 'unchained', 'messari', 'kraken', 'coinbase', 'binance',
        'coingape', 'investing.com crypto', 'finance magnates', 'crypto',
        'reddit r/bitcoin', 'reddit r/cryptocurrency', 'reddit r/ethereum', 'reddit r/crypto',
        'reddit r/defi', 'coin bureau', 'bitboy', 'altcoin daily', 'benjamin cowen',
        'digital asset news', 'bankless', 'unchained podcast', 'coingecko podcast',
        'chainlink', 'vitalik', 'l2beat', 'aave', 'uniswap', 'open', 'paradigm',
        'solana', 'polkadot', 'cardano', 'tether', 'circle',
    ]
    source_lower = article['source'].lower()
    for cs in crypto_sources:
        if cs in source_lower:
            return True

    # Crypto keywords
    crypto_words = [
        'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'blockchain', 'defi', 'nft',
        'token', 'coin', 'mining', 'wallet', 'exchange', 'binance', 'coinbase',
        'solana', 'cardano', 'polkadot', 'avalanche', 'polygon', 'ripple', 'xrp',
        'dogecoin', 'doge', 'shiba', 'stablecoin', 'usdt', 'usdc', 'usdt',
        'altcoin', 'memecoin', 'web3', 'dao', 'dex', 'swap', 'staking', 'yield',
        'airdrop', 'ico', 'ido', 'halving', 'hash', 'satoshi', 'vitalik',
        'uniswap', 'aave', 'compound', 'maker', 'lido', 'curve', 'opensea',
        'metamask', 'ledger', 'trezor', 'layer 2', 'rollup', 'zk', 'consensus',
        'smart contract', 'dapp', 'oracle', 'chainlink', 'polkadot', 'cosmos',
        'arbitrum', 'optimism', 'base', 'linea', 'zksync',
    ]
    for w in crypto_words:
        if w in text:
            return True

    # Finance/macro keywords (relevant to crypto market)
    macro_words = [
        'federal reserve', 'fed', 'interest rate', 'inflation', 'recession',
        'gdp', 'employment', 'tariff', 'sanction', 'trade war', 'banking crisis',
        'stock market', 'nasdaq', 's&p', 'dow jones', 'wall street',
        'gold', 'oil', 'commodity', 'treasury', 'bond', 'forex',
        'dollar', 'euro', 'currency', 'monetary', 'fiscal',
        'etf', 'regulation', 'sec', 'cftc', 'compliance',
        'war', 'conflict', 'geopolitics', 'nuclear', 'sanctions',
    ]
    for w in macro_words:
        if w in text:
            return True

    return False

def get_fallback_image(article):
    """Generate fallback image based on content."""
    text = f"{article['title']} {article['description']}".lower()
    if 'bitcoin' in text or 'btc' in text:
        return PLACEHOLDER_IMAGES['bitcoin']
    if 'ethereum' in text or 'eth' in text:
        return PLACEHOLDER_IMAGES['ethereum']
    if any(w in text for w in ['market', 'stock', 'trading', 'price']):
        return PLACEHOLDER_IMAGES['market']
    return PLACEHOLDER_IMAGES['crypto']

# ===== NEWS REFRESH =====
def refresh_news():
    global news_cache, is_loading
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
        t.join(timeout=15)

    for r in results:
        all_articles.extend(r)

    # Filter: only crypto/macro related articles
    filtered = [a for a in all_articles if is_crypto_related(a)]

    # Add fallback images
    for a in filtered:
        if not a.get('image'):
            a['image'] = get_fallback_image(a)

    seen = set()
    deduped = []
    for a in filtered:
        key = re.sub(r'[^a-z0-9]', '', a['title'].lower())[:40]
        if key not in seen and len(key) > 5:
            seen.add(key)
            deduped.append(a)

    deduped.sort(key=lambda x: x['timestamp'] if x['timestamp'] > 0 else 0, reverse=True)

    with news_lock:
        news_cache = deduped
        is_loading = False
        save_json_cache(NEWS_CACHE_FILE, deduped)

    print(f'[news] refreshed {len(deduped)} articles from {len(RSS_FEEDS)} sources')
    sys.stdout.flush()

def news_refresh_loop():
    while True:
        refresh_news()
        time.sleep(120)

# ===== HTTP HANDLER =====
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
        if path == '/api/ai-cache':
            self._serve_ai_cache()
            return
        self.send_error(404)

    def do_POST(self):
        if self.path == '/api/ai':
            self._proxy_ai()
        else:
            self.send_error(404)

    def _serve_news(self):
        query = self.path.split('?')[1] if '?' in self.path else ''
        params = dict(p.split('=') for p in query.split('&') if '=' in p) if query else {}
        limit = min(int(params.get('limit', 999)), 2000)

        with news_lock:
            articles = news_cache[:limit]
            loading = is_loading
            raw = json.dumps({
                'articles': articles,
                'total': len(news_cache),
                'returned': len(articles),
                'sources': len(RSS_FEEDS),
                'loading': loading
            }).encode()

        try:
            compressed = gzip.compress(raw)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(compressed)))
            self._cors()
            self.end_headers()
            self.wfile.write(compressed)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_ai_cache(self):
        with ai_cache_lock:
            raw = json.dumps({'cache': ai_cache, 'total': len(ai_cache)}).encode()
        try:
            compressed = gzip.compress(raw)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(compressed)))
            self._cors()
            self.end_headers()
            self.wfile.write(compressed)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _proxy_ai(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            body_json = json.loads(body)
            api_key = os.environ.get('OPENAI_API_KEY', '')

            # Generate cache key from article title (unique per article)
            messages = body_json.get('messages', [])
            user_msg = next((m['content'] for m in messages if m.get('role') == 'user'), '')
            # Extract article title from prompt for unique caching
            title_match = re.search(r'Title:\s*(.+)', user_msg)
            cache_key = title_match.group(1).strip()[:200] if title_match else user_msg[:200]

            # Check cache (skip if ?nocache=1 in URL)
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
                            ai_cache[cache_key] = {'response': data.decode('utf-8', errors='replace'), 'ts': time.time()}
                            save_json_cache(AI_CACHE_FILE, ai_cache)
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
        except (BrokenPipeError, ConnectionResetError):
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
        except (BrokenPipeError, ConnectionResetError):
            pass

if __name__ == '__main__':
    print(f'GITNEWS running on http://localhost:{PORT}')
    sys.stdout.flush()

    # Load cached data from disk
    load_all_caches()

    # Start background news refresh
    t = threading.Thread(target=news_refresh_loop, daemon=True)
    t.start()

    http.server.HTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
