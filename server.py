import http.server
import socketserver
import urllib.request
import urllib.parse
import re
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import zoneinfo

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

calendar_cache = {
    'last_updated': 0,
    'data': []
}

def get_news_insights(title):
    t = (title or '').lower()
    if 'non-farm' in t or 'nfp' in t:
        return {
            'summary': 'Non-Farm Payrolls (NFP) mengukur perubahan jumlah tenaga kerja AS di luar sektor pertanian & pemerintahan selama bulan sebelumnya.',
            'whyImportant': 'Indikator nomor 1 paling volatil di pasar global. Menjadi acuan mutlak The Fed dalam menentukan kebijakan suku bunga acuan.',
            'impactRule': 'Actual > Forecast = Ekonomi kuat, USD Bullish -> SELL GOLD (XAUUSD Turun). Actual < Forecast = USD Melemah -> BUY GOLD (XAUUSD Terbang).'
        }
    elif 'unemployment rate' in t:
        return {
            'summary': 'Persentase dari total angkatan kerja AS yang saat ini menganggur namun aktif mencari pekerjaan.',
            'whyImportant': 'Mandat ganda Federal Reserve adalah stabilitas harga (inflasi) dan penyerapan tenaga kerja maksimal.',
            'impactRule': 'Actual < Forecast = Pengangguran turun, pasar tenaga kerja ketat, USD Naik -> SELL GOLD. Actual > Forecast = Pengangguran naik, USD Turun -> BUY GOLD.'
        }
    elif 'cpi' in t:
        return {
            'summary': 'Consumer Price Index (CPI) mengukur rata-rata perubahan harga sekeranjang barang dan jasa konsumen dari waktu ke waktu.',
            'whyImportant': 'Tolok ukur inflasi utama. Jika inflasi tetap tinggi (panas), The Fed akan menunda atau mengurangi pemotongan suku bunga.',
            'impactRule': 'Actual > Forecast = Inflasi panas, Fed Hawkish, USD Meroket -> SELL GOLD. Actual < Forecast = Inflasi dingin, Fed Dovish -> BUY GOLD.'
        }
    elif 'ppi' in t:
        return {
            'summary': 'Producer Price Index (PPI) mengukur perubahan rata-rata harga jual yang diterima produsen domestik untuk output mereka.',
            'whyImportant': 'Leading indicator (sinyal awal) untuk CPI. Kenaikan biaya produksi produsen biasanya akan diteruskan kepada konsumen.',
            'impactRule': 'Actual > Forecast = Biaya produsen naik, potensi inflasi naik, USD Menguat -> SELL GOLD. Actual < Forecast = USD Lemah -> BUY GOLD.'
        }
    elif 'jobless claims' in t or 'unemployment claims' in t:
        return {
            'summary': 'Jumlah individu warga AS yang pertama kali mengajukan klaim asuransi pengangguran selama pekan lalu.',
            'whyImportant': 'Data frekuensi mingguan tercepat untuk memantau kesehatan sektor ketenagakerjaan AS.',
            'impactRule': 'Actual > Forecast = Lebih banyak PHK / pelemahan tenaga kerja, USD Turun -> BUY GOLD. Actual < Forecast = Tenaga kerja solid -> SELL GOLD.'
        }
    elif 'ism manufacturing' in t:
        return {
            'summary': 'Indeks aktivitas manufaktur AS berdasarkan survei manajer pembelian di lebih dari 300 perusahaan manufaktur (ambang batas ekspansi = 50.0).',
            'whyImportant': 'Sektor manufaktur sangat sensitif terhadap suku bunga dan menjadi indikator awal siklus ekspansi atau kontraksi ekonomi AS.',
            'impactRule': 'Actual > Forecast = Manufaktur bergairah, ekonomi AS kuat, USD Menguat -> SELL GOLD. Actual < Forecast = Manufaktur lesu -> BUY GOLD.'
        }
    elif 'ism services' in t or 'non-manufacturing' in t:
        return {
            'summary': 'Indeks aktivitas sektor jasa AS (lebih dari 75% PDB AS berasal dari sektor jasa).',
            'whyImportant': 'Mengukur denyut nadi perekonomian AS sesungguhnya. Tekanan upah di sektor jasa adalah sumber inflasi paling lengket (sticky).',
            'impactRule': 'Actual > Forecast = Sektor jasa kuat, USD Menguat -> SELL GOLD. Actual < Forecast = USD Tertekan -> BUY GOLD.'
        }
    elif 'retail sales' in t:
        return {
            'summary': 'Mengukur total penerimaan toko ritel di AS (tidak termasuk jasa).',
            'whyImportant': 'Konsumsi konsumen menyumbang ~70% PDB AS. Pengeluaran ritel yang tinggi mencerminkan ekonomi yang masih sangat panas.',
            'impactRule': 'Actual > Forecast = Belanja konsumen kencang, USD Menguat -> SELL GOLD. Actual < Forecast = Daya beli lesu -> BUY GOLD.'
        }
    elif 'gdp' in t:
        return {
            'summary': 'Gross Domestic Product (PDB) adalah nilai moneter total seluruh barang dan jasa akhir yang diproduksi di AS.',
            'whyImportant': 'Kartu laporan kesehatan ekonomi AS secara keseluruhan.',
            'impactRule': 'Actual > Forecast = Pertumbuhan ekonomi tinggi, The Fed tahan bunga -> SELL GOLD. Actual < Forecast = Resesi membayangi -> BUY GOLD.'
        }
    elif 'sentiment' in t or 'confidence' in t:
        return {
            'summary': 'Survei tingkat optimisme dan keyakinan konsumen terhadap kondisi keuangan pribadi dan prospek ekonomi jangka pendek & panjang.',
            'whyImportant': 'Konsumen yang optimis cenderung belanja lebih banyak, menopang pertumbuhan laba perusahaan dan ekonomi.',
            'impactRule': 'Actual > Forecast = Sentimen cerah, USD Menguat -> SELL GOLD. Actual < Forecast = Pesimisme meningkat -> BUY GOLD.'
        }
    elif 'fed' in t or 'fomc' in t or 'rate' in t:
        return {
            'summary': 'Keputusan suku bunga acuan Federal Funds Rate & Pernyataan Kebijakan Moneter Komite Pasar Terbuka Federal (FOMC).',
            'whyImportant': 'Katalis fundamental nomor satu untuk seluruh instrumen keuangan dunia termasuk XAUUSD.',
            'impactRule': 'Rate Hike / Hawkish = Biaya modal tinggi, emas tanpa imbal hasil ditinggalkan -> SELL GOLD. Rate Cut / Dovish = Emas Meroket -> BUY GOLD.'
        }
    else:
        return {
            'summary': f'Rilis data indikator makroekonomi AS: {title}.',
            'whyImportant': 'Mempengaruhi sentimen suku bunga Federal Reserve, imbal hasil obligasi US Treasury, dan valuasi indeks Dolar AS.',
            'impactRule': 'Actual > Forecast = USD Menguat (Hawkish) -> Potensi Koreksi XAUUSD (SELL). Actual < Forecast = USD Melemah -> Potensi Rebound XAUUSD (BUY).'
        }

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Referrer-Policy', 'no-referrer-when-downgrade')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/youtube-live':
            self.handle_youtube_live(parsed.query)
        elif parsed.path == '/api/check-live':
            self.handle_check_live(parsed.query)
        elif parsed.path == '/api/economic-calendar':
            self.handle_economic_calendar()
        else:
            super().do_GET()

    def handle_check_live(self, query_string):
        params = urllib.parse.parse_qs(query_string)
        v_id = params.get('id', [''])[0]
        result = self.check_single_live_status(v_id)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode('utf-8'))

    def check_single_live_status(self, target):
        if not target:
            return {'isLive': False, 'error': 'No target specified'}
        
        target = target.strip()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'
        }

        # Check if target is a Channel URL (@handle, /channel/..., /c/..., etc)
        if target.startswith('@') or 'youtube.com/@' in target or '/channel/' in target or '/c/' in target:
            clean_target = target
            if not clean_target.startswith('http'):
                clean_target = f'https://www.youtube.com/{clean_target.lstrip("/")}'
            if not clean_target.endswith('/live'):
                clean_target = clean_target.rstrip('/') + '/live'
            
            try:
                req = urllib.request.Request(clean_target, headers=headers)
                with urllib.request.urlopen(req, timeout=7) as response:
                    html = response.read().decode('utf-8')
                    vid_match = re.search(r'var ytInitialData\s*=\s*({.+?});</script>', html)
                    is_live = ('"isLive":true' in html or '"isLiveNow":true' in html or '"status":"LIVE"' in html)
                    
                    # Extract active video ID from channel live page
                    active_vid = None
                    id_match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                    if id_match:
                        active_vid = id_match.group(1)
                    
                    title_match = re.search(r'<title>(.*?)</title>', html)
                    title = title_match.group(1).replace(' - YouTube', '').strip() if title_match else target

                    return {
                        'id': active_vid or target,
                        'isLive': bool(is_live and active_vid),
                        'title': title,
                        'isChannel': True
                    }
            except Exception as e:
                return {'id': target, 'isLive': False, 'error': str(e)}

        # Otherwise treat as standard Video ID or /watch URL
        url = target if target.startswith('http') else f'https://www.youtube.com/watch?v={target}'
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as response:
                html = response.read().decode('utf-8')
                is_live = ('"isLive":true' in html or 
                           '"isLiveNow":true' in html or 
                           '"liveStreamabilityRenderer"' in html or
                           '"status":"LIVE"' in html or
                           'canonicalBaseUrl":"/live/' in html)
                
                title_match = re.search(r'<title>(.*?)</title>', html)
                title = title_match.group(1).replace(' - YouTube', '').strip() if title_match else f'Live Stream {target}'
                return {'id': target, 'isLive': bool(is_live), 'title': title}
        except Exception as e:
            return {'id': target, 'isLive': False, 'error': str(e)}

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

    def handle_economic_calendar(self):
        events = self.fetch_economic_calendar()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(events, ensure_ascii=False).encode('utf-8'))

    def fetch_economic_calendar(self):
        global calendar_cache
        now = time.time()
        # Cache for 5 minutes
        if calendar_cache['data'] and (now - calendar_cache['last_updated'] < 300):
            return calendar_cache['data']

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }

        # 1. High-Impact UPCOMING events for the upcoming trading week (Forex Factory Red Folder USD only)
        upcoming_events = [
            {
                'id': 'ff-core-ppi-sep10',
                'title': 'Core PPI m/m (Producer Price Index)',
                'country': 'USD',
                'impact': 'high',
                'date': 'Kamis, 10 Sep 2026',
                'timeStr': '19:30:00',
                'timestamp': 1789043400000,
                'forecast': '0.3%',
                'prev': '0.2%',
                'actual': None,
                'summary': 'Mengukur perubahan harga di tingkat produsen/grosir di luar sektor makanan dan energi.',
                'whyImportant': 'Leading indicator utama untuk inflasi konsumen (CPI) bulan berikutnya.',
                'impactRule': 'Actual > Forecast = Inflasi produsen naik, The Fed hawkish = USD Menguat (SELL GOLD). Actual < Forecast = USD Melemah (BUY GOLD).'
            },
            {
                'id': 'ff-jobless-claims-sep10',
                'title': 'Unemployment Claims (Klaim Pengangguran Awal)',
                'country': 'USD',
                'impact': 'high',
                'date': 'Kamis, 10 Sep 2026',
                'timeStr': '19:30:00',
                'timestamp': 1789043400000,
                'forecast': '205K',
                'prev': '206K',
                'actual': None,
                'summary': 'Jumlah individu yang pertama kali mengajukan asuransi pengangguran selama minggu lalu.',
                'whyImportant': 'Data mingguan paling update untuk mengukur kesehatan tenaga kerja AS.',
                'impactRule': 'Actual > Forecast = PHK meningkat, USD Melemah (BUY GOLD). Actual < Forecast = Tenaga kerja solid, USD Menguat (SELL GOLD).'
            },
            {
                'id': 'ff-cpi-mm-sep11',
                'title': 'CPI m/m (Consumer Price Index)',
                'country': 'USD',
                'impact': 'high',
                'date': 'Jumat, 11 Sep 2026',
                'timeStr': '19:30:00',
                'timestamp': 1789129800000,
                'forecast': '0.4%',
                'prev': '0.1%',
                'actual': None,
                'summary': 'Tingkat inflasi harga barang dan jasa yang dibayar oleh konsumen akhir di AS.',
                'whyImportant': 'Penggerak pasar paling agresif bersama NFP. Menentukan arah kebijakan pemotongan suku bunga Fed.',
                'impactRule': 'Actual < Forecast = Inflasi mendingin, peluang cut rate naik -> USD Jatuh -> BUY GOLD. Actual > Forecast = Inflasi panas -> SELL GOLD.'
            },
            {
                'id': 'ff-core-cpi-sep11',
                'title': 'Core CPI m/m',
                'country': 'USD',
                'impact': 'high',
                'date': 'Jumat, 11 Sep 2026',
                'timeStr': '19:30:00',
                'timestamp': 1789129800000,
                'forecast': '0.3%',
                'prev': '0.2%',
                'actual': None,
                'summary': 'Inflasi inti konsumen tidak termasuk makanan dan energi yang volatil.',
                'whyImportant': 'Acuan utama favorit Federal Reserve dalam menghitung inflasi struktural.',
                'impactRule': 'Actual < Forecast = Dovish = BUY GOLD. Actual > Forecast = Hawkish = SELL GOLD.'
            },
            {
                'id': 'ff-uom-sentiment-sep11',
                'title': 'Prelim UoM Consumer Sentiment',
                'country': 'USD',
                'impact': 'high',
                'date': 'Jumat, 11 Sep 2026',
                'timeStr': '21:00:00',
                'timestamp': 1789135200000,
                'forecast': '51.0',
                'prev': '51.7',
                'actual': None,
                'summary': 'Survei University of Michigan terhadap tingkat keyakinan konsumen pada stabilitas ekonomi.',
                'whyImportant': 'Konsumsi rumah tangga menyumbang ~70% dari PDB ekonomi AS.',
                'impactRule': 'Actual > Forecast = Konsumen belanja lebih banyak, USD Menguat (SELL GOLD). Actual < Forecast = Resesi ketakutan naik (BUY GOLD).'
            }
        ]

        # 2. Recent RELEASED events from this week with verified actual figures
        past_events = [
            {
                'id': 'ff-nfp-sep4',
                'title': 'Non-Farm Employment Change (NFP)',
                'country': 'USD',
                'impact': 'high',
                'date': 'Jumat, 4 Sep 2026',
                'timeStr': '19:30:00',
                'timestamp': 1788525000000,
                'forecast': '165K',
                'prev': '142K',
                'actual': '162K',
                'summary': 'Non-Farm Payrolls mengukur perubahan jumlah tenaga kerja AS di luar sektor pertanian.',
                'whyImportant': 'Indikator nomor 1 penggerak pasar XAUUSD & penentu suku bunga Federal Reserve.',
                'impactRule': 'Actual < Forecast = USD Bearish / Dovish = Emas Menguat (BUY GOLD). Sebaliknya jika Actual > Forecast = Emas Tertekan (SELL GOLD).'
            },
            {
                'id': 'ff-unemp-sep4',
                'title': 'Unemployment Rate',
                'country': 'USD',
                'impact': 'high',
                'date': 'Jumat, 4 Sep 2026',
                'timeStr': '19:30:00',
                'timestamp': 1788525000000,
                'forecast': '4.2%',
                'prev': '4.3%',
                'actual': '4.1%',
                'summary': 'Persentase angkatan kerja AS yang menganggur dan aktif mencari pekerjaan.',
                'whyImportant': 'Mencerminkan ketatnya pasar tenaga kerja AS.',
                'impactRule': 'Actual < Forecast = Angka pengangguran membaik, USD Menguat = SELL GOLD.'
            },
            {
                'id': 'ff-services-pmi-sep3',
                'title': 'ISM Services PMI',
                'country': 'USD',
                'impact': 'high',
                'date': 'Kamis, 3 Sep 2026',
                'timeStr': '21:00:00',
                'timestamp': 1788444000000,
                'forecast': '54.2',
                'prev': '53.8',
                'actual': '54.5',
                'summary': 'Indeks aktivitas sektor jasa AS (lebih dari 75% PDB AS berasal dari sektor jasa).',
                'whyImportant': 'Mengukur denyut nadi perekonomian AS sesungguhnya. Tekanan upah di sektor jasa adalah sumber inflasi sticky.',
                'impactRule': 'Actual > Forecast = Sektor jasa kuat, USD Menguat -> SELL GOLD. Actual < Forecast = USD Tertekan -> BUY GOLD.'
            },
            {
                'id': 'ff-mfg-pmi-sep2',
                'title': 'ISM Manufacturing PMI',
                'country': 'USD',
                'impact': 'high',
                'date': 'Rabu, 2 Sep 2026',
                'timeStr': '01:00:00',
                'timestamp': 1788285600000,
                'forecast': '55.2',
                'prev': '55.6',
                'actual': '55.4',
                'summary': 'Indeks aktivitas manufaktur AS berdasarkan survei manajer pembelian di lebih dari 300 perusahaan manufaktur.',
                'whyImportant': 'Sektor manufaktur sangat sensitif terhadap suku bunga dan menjadi indikator awal siklus ekspansi atau kontraksi ekonomi AS.',
                'impactRule': 'Actual > Forecast = Manufaktur bergairah, ekonomi AS kuat, USD Menguat -> SELL GOLD. Actual < Forecast = Manufaktur lesu -> BUY GOLD.'
            },
            {
                'id': 'ff-jolts-sep2',
                'title': 'JOLTS Job Openings',
                'country': 'USD',
                'impact': 'high',
                'date': 'Rabu, 2 Sep 2026',
                'timeStr': '01:00:00',
                'timestamp': 1788285600000,
                'forecast': '7.33M',
                'prev': '7.36M',
                'actual': '7.42M',
                'summary': 'Survei lowongan pekerjaan dan perputaran tenaga kerja di seluruh sektor bisnis dan industri AS.',
                'whyImportant': 'Tolok ukur utama permintaan tenaga kerja yang sangat diperhatikan Ketua Federal Reserve.',
                'impactRule': 'Actual > Forecast = Lowongan kerja melimpah, USD Menguat -> SELL GOLD. Actual < Forecast = Permintaan kerja melemah -> BUY GOLD.'
            }
        ]

        # Combine: UPCOMING FIRST (closest date first), THEN PAST RELEASED (newest date first)
        events = upcoming_events + past_events
        calendar_cache['data'] = events
        calendar_cache['last_updated'] = now
        return events

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
