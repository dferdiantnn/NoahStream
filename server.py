import http.server
import socketserver
import urllib.request
import urllib.parse
import re
import json
import os

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/youtube-live':
            self.handle_youtube_live(parsed.query)
        else:
            super().do_GET()

    def handle_youtube_live(self, query_string):
        params = urllib.parse.parse_qs(query_string)
        q = params.get('q', ['xauusd'])[0]
        limit = int(params.get('limit', ['4'])[0])

        results = self.scrape_youtube_live(q, limit)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(results).encode('utf-8'))

    def scrape_youtube_live(self, query, limit):
        # sp=CAMSAkAB: Filter Type=Video, Feature=Live, Sort=Popularity
        search_url = f'https://www.youtube.com/results?search_query={urllib.parse.quote(query)}&sp=CAMSAkAB'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        req = urllib.request.Request(search_url, headers=headers)
        videos = []
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                html = response.read().decode('utf-8')
                match = re.search(r'var ytInitialData\s*=\s*({.+?});</script>', html)
                if match:
                    data = json.loads(match.group(1))
                    sections = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
                    for section in sections:
                        items = section.get('itemSectionRenderer', {}).get('contents', [])
                        for item in items:
                            v = item.get('videoRenderer', {})
                            if not v:
                                continue
                            v_id = v.get('videoId')
                            badges = [b.get('metadataBadgeRenderer', {}).get('label', '') for b in v.get('badges', [])]
                            # Check if truly LIVE badge
                            is_live = 'LIVE' in badges or any('LIVE' in str(b) for b in badges)
                            if not is_live and 'badges' in v:
                                is_live = any('LIVE' in str(b) for b in v['badges'])

                            title = v.get('title', {}).get('runs', [{}])[0].get('text', '')
                            viewers_runs = v.get('viewCountText', {}).get('runs', [])
                            viewers_str = ''.join([r.get('text', '') for r in viewers_runs]) if viewers_runs else v.get('viewCountText', {}).get('simpleText', '')
                            
                            # Parse numeric viewers
                            num_match = re.search(r'([\d.,]+)', viewers_str)
                            viewers_num = 0
                            if num_match:
                                raw_n = num_match.group(1).replace('.', '').replace(',', '')
                                try:
                                    viewers_num = int(raw_n)
                                except:
                                    viewers_num = 1200
                            else:
                                viewers_num = 1000

                            if v_id and is_live:
                                videos.append({
                                    'id': v_id,
                                    'title': title,
                                    'viewers': viewers_num,
                                    'viewersText': viewers_str
                                })
                                if len(videos) >= limit:
                                    break
                        if len(videos) >= limit:
                            break
        except Exception as e:
            print('Scraping error:', e)

        return videos

if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', PORT), CustomHandler) as httpd:
        print(f'Noah Stream Backend running on http://localhost:{PORT}')
        httpd.serve_forever()
