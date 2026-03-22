#!/usr/bin/env python3
"""
Schiffs-Scraper - Web App for Ship Image Download, Classification & Training
With VPN integration, ML classification, and data augmentation
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import sqlite3
import subprocess
import threading
import time
import random
import json
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'schiffs-scraper.db')
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

# Global state for running jobs
active_jobs = {}

# ============ DATABASE ============

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), 'r') as f:
        schema = f.read()
    conn = get_db()
    conn.executescript(schema)
    conn.commit()
    conn.close()

# ============ VPN FUNCTIONS ============

def get_vpn_status():
    """Check NordVPN connection status"""
    try:
        result = subprocess.run(['nordvpn', 'status'], capture_output=True, text=True, timeout=10)
        output = result.stdout

        connected = 'Connected' in output or 'Verbunden' in output
        country = None
        ip = None

        for line in output.split('\n'):
            if 'Country:' in line or 'Land:' in line:
                country = line.split(':')[-1].strip()
            if 'Server IP:' in line or 'IP:' in line:
                ip = line.split(':')[-1].strip()

        return {
            'connected': connected,
            'country': country,
            'ip': ip,
            'raw': output
        }
    except Exception as e:
        return {'connected': False, 'error': str(e)}

def connect_vpn(country='Germany'):
    """Connect to VPN"""
    try:
        subprocess.run(['nordvpn', 'connect', country], capture_output=True, timeout=30)
        time.sleep(3)
        status = get_vpn_status()

        conn = get_db()
        conn.execute(
            'INSERT INTO vpn_log (action, country, ip_address, success) VALUES (?, ?, ?, ?)',
            ('connect', country, status.get('ip'), status.get('connected', False))
        )
        conn.commit()
        conn.close()

        return status
    except Exception as e:
        return {'connected': False, 'error': str(e)}

def disconnect_vpn():
    """Disconnect from VPN"""
    try:
        subprocess.run(['nordvpn', 'disconnect'], capture_output=True, timeout=10)
        conn = get_db()
        conn.execute('INSERT INTO vpn_log (action, success) VALUES (?, ?)', ('disconnect', True))
        conn.commit()
        conn.close()
        return {'connected': False}
    except Exception as e:
        return {'error': str(e)}

def rotate_vpn():
    """Rotate VPN IP (disconnect + reconnect)"""
    disconnect_vpn()
    time.sleep(2)
    return connect_vpn()

# ============ SCRAPING FUNCTIONS ============

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

session = requests.Session()
session.headers.update(HEADERS)

def analyze_website(url):
    """Analyze a website and find categories/structure"""
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        categories = []
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

        patterns = [
            'a[href*="category"]',
            'a[href*="type"]',
            'a[href*="gallery"]',
            '.category a',
            '.nav-item a',
            'li.menu-item a',
        ]

        seen_urls = set()
        for pattern in patterns:
            for link in soup.select(pattern):
                href = link.get('href', '')
                if href and href not in seen_urls:
                    full_url = urljoin(base_url, href)
                    if urlparse(full_url).netloc == urlparse(base_url).netloc:
                        categories.append({
                            'name': link.get_text(strip=True) or href,
                            'url': full_url
                        })
                        seen_urls.add(href)

        title = soup.title.string if soup.title else url

        return {
            'success': True,
            'title': title,
            'categories': categories[:50],
            'url': url
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def find_images(url, limit=100):
    """Find ship images on a page"""
    try:
        response = session.get(url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')

        images = []
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

        if 'vesselfinder.com' in url:
            return find_vesselfinder_images(soup, base_url, limit)

        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if src:
                full_url = urljoin(base_url, src)
                alt = img.get('alt', '')
                if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    images.append({
                        'url': full_url,
                        'alt': alt,
                        'source_page': url
                    })
                    if len(images) >= limit:
                        break

        return images
    except Exception as e:
        print(f"find_images error: {e}")
        return []

def find_vesselfinder_images(soup, base_url, limit):
    """VesselFinder-specific image finder"""
    images = []

    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if '/ship-photos/' in href and href.count('/') == 2:
            photo_url = urljoin(base_url, href)

            ship_name = ''
            parent = link.find_parent()
            if parent:
                name_link = parent.find('a', href=lambda h: h and '/vessels/details/' in h)
                if name_link:
                    ship_name = name_link.get_text(strip=True)

            photo_id = href.split('/')[-1]
            image_url = f"https://photos.vesselfinder.com/2/{photo_id}.jpg"

            images.append({
                'url': image_url,
                'alt': ship_name,
                'source_page': photo_url,
                'photo_id': photo_id
            })

            if len(images) >= limit:
                break

    return images

def download_image(url, save_path):
    """Download a single image"""
    try:
        response = session.get(url, timeout=30, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Download error for {url}: {e}")
        return False

def run_scraping_job(job_id):
    """Background task for scraping"""
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()

    if not job:
        return

    conn.execute('UPDATE jobs SET status = ?, started_at = ? WHERE id = ?',
                ('running', datetime.now().isoformat(), job_id))
    conn.commit()

    try:
        items = conn.execute(
            'SELECT * FROM items WHERE job_id = ? AND status = ? LIMIT ?',
            (job_id, 'pending', job['limit_count'] or 1000)
        ).fetchall()

        for i, item in enumerate(items):
            current_job = conn.execute('SELECT status FROM jobs WHERE id = ?', (job_id,)).fetchone()
            if current_job['status'] != 'running':
                break

            delay = random.uniform(job['delay_min'], job['delay_max'])
            time.sleep(delay)

            if item['image_url']:
                filename = f"{job_id}_{item['id']}_{os.path.basename(urlparse(item['image_url']).path)}"
                save_path = os.path.join(DOWNLOAD_DIR, str(job_id), filename)

                success = download_image(item['image_url'], save_path)

                if success:
                    conn.execute(
                        'UPDATE items SET status = ?, local_path = ?, downloaded_at = ? WHERE id = ?',
                        ('downloaded', save_path, datetime.now().isoformat(), item['id'])
                    )
                else:
                    conn.execute('UPDATE items SET status = ? WHERE id = ?', ('failed', item['id']))

                conn.execute('UPDATE jobs SET downloaded = downloaded + 1 WHERE id = ?', (job_id,))
                conn.commit()

        conn.execute('UPDATE jobs SET status = ?, completed_at = ? WHERE id = ?',
                    ('completed', datetime.now().isoformat(), job_id))
        conn.commit()

    except Exception as e:
        conn.execute('UPDATE jobs SET status = ?, error_message = ? WHERE id = ?',
                    ('failed', str(e), job_id))
        conn.commit()

    conn.close()
    active_jobs.pop(job_id, None)

# ============ FRONTEND ============

@app.route('/')
def index():
    return render_template('index.html')

# ============ API: VPN ============

@app.route('/api/vpn/status')
def api_vpn_status():
    return jsonify(get_vpn_status())

@app.route('/api/vpn/connect', methods=['POST'])
def api_vpn_connect():
    data = request.get_json() or {}
    country = data.get('country', 'Germany')
    return jsonify(connect_vpn(country))

@app.route('/api/vpn/disconnect', methods=['POST'])
def api_vpn_disconnect():
    return jsonify(disconnect_vpn())

@app.route('/api/vpn/rotate', methods=['POST'])
def api_vpn_rotate():
    return jsonify(rotate_vpn())

# ============ API: ANALYZE ============

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL required'}), 400
    result = analyze_website(url)
    return jsonify(result)

# ============ API: JOBS ============

@app.route('/api/jobs', methods=['GET'])
def api_get_jobs():
    conn = get_db()
    jobs = conn.execute('SELECT * FROM jobs ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(j) for j in jobs])

@app.route('/api/jobs', methods=['POST'])
def api_create_job():
    data = request.get_json()
    url = data.get('url')
    name = data.get('name', url)
    limit_count = data.get('limit', 100)
    delay_min = data.get('delay_min', 1.0)
    delay_max = data.get('delay_max', 5.0)
    vpn_required = data.get('vpn_required', True)

    if not url:
        return jsonify({'error': 'URL required'}), 400

    conn = get_db()
    cursor = conn.execute(
        '''INSERT INTO jobs (url, name, limit_count, delay_min, delay_max, vpn_required)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (url, name, limit_count, delay_min, delay_max, vpn_required)
    )
    job_id = cursor.lastrowid

    images = find_images(url, limit=limit_count)
    for img in images:
        conn.execute(
            'INSERT INTO items (job_id, source_url, image_url, ship_name) VALUES (?, ?, ?, ?)',
            (job_id, img['source_page'], img['url'], img.get('alt', ''))
        )

    conn.execute('UPDATE jobs SET total_items = ? WHERE id = ?', (len(images), job_id))
    conn.commit()

    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    conn.close()

    return jsonify(dict(job)), 201

@app.route('/api/jobs/<int:job_id>')
def api_get_job(job_id):
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    items = conn.execute('SELECT * FROM items WHERE job_id = ?', (job_id,)).fetchall()
    conn.close()

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify({
        'job': dict(job),
        'items': [dict(i) for i in items]
    })

@app.route('/api/jobs/<int:job_id>/start', methods=['POST'])
def api_start_job(job_id):
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    conn.close()

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    if job['vpn_required']:
        vpn_status = get_vpn_status()
        if not vpn_status.get('connected'):
            return jsonify({'error': 'VPN not connected. Please connect first.'}), 400

    thread = threading.Thread(target=run_scraping_job, args=(job_id,))
    thread.daemon = True
    thread.start()
    active_jobs[job_id] = thread

    return jsonify({'status': 'started', 'job_id': job_id})

@app.route('/api/jobs/<int:job_id>/pause', methods=['POST'])
def api_pause_job(job_id):
    conn = get_db()
    conn.execute('UPDATE jobs SET status = ? WHERE id = ?', ('paused', job_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'paused'})

@app.route('/api/jobs/<int:job_id>/delete', methods=['DELETE'])
def api_delete_job(job_id):
    conn = get_db()
    conn.execute('DELETE FROM items WHERE job_id = ?', (job_id,))
    conn.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})

# ============ API: STATS ============

@app.route('/api/stats')
def api_stats():
    conn = get_db()
    stats = {
        'total_jobs': conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],
        'total_items': conn.execute('SELECT COUNT(*) FROM items').fetchone()[0],
        'downloaded': conn.execute('SELECT COUNT(*) FROM items WHERE status = ?', ('downloaded',)).fetchone()[0],
        'pending': conn.execute('SELECT COUNT(*) FROM items WHERE status = ?', ('pending',)).fetchone()[0],
        'failed': conn.execute('SELECT COUNT(*) FROM items WHERE status = ?', ('failed',)).fetchone()[0],
        'classifications': conn.execute('SELECT COUNT(*) FROM classifications').fetchone()[0],
    }

    # Ship type distribution
    types = conn.execute('''
        SELECT ship_type, COUNT(*) as count
        FROM items
        WHERE ship_type IS NOT NULL AND ship_type != ''
        GROUP BY ship_type ORDER BY count DESC
    ''').fetchall()
    stats['type_distribution'] = [{'type': t['ship_type'], 'count': t['count']} for t in types]

    conn.close()
    return jsonify(stats)

# ============ API: PREDEFINED URLS ============

@app.route('/api/urls')
def api_get_urls():
    conn = get_db()
    urls = conn.execute('SELECT * FROM predefined_urls ORDER BY name').fetchall()
    conn.close()
    return jsonify([dict(u) for u in urls])

@app.route('/api/urls', methods=['POST'])
def api_add_url():
    data = request.get_json()
    url = data.get('url', '').strip()
    name = data.get('name', '').strip()

    if not url:
        return jsonify({'error': 'URL required'}), 400

    if not name:
        name = urlparse(url).netloc.replace('www.', '').split('.')[0].title()

    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO predefined_urls (url, name) VALUES (?, ?)',
            (url, name)
        )
        url_id = cursor.lastrowid
        conn.commit()
        new_url = conn.execute('SELECT * FROM predefined_urls WHERE id = ?', (url_id,)).fetchone()
        conn.close()
        return jsonify(dict(new_url)), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'URL already exists'}), 409

@app.route('/api/urls/<int:url_id>', methods=['DELETE'])
def api_delete_url(url_id):
    conn = get_db()
    conn.execute('DELETE FROM predefined_urls WHERE id = ?', (url_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})

# ============ API: SHIPS ============

@app.route('/api/ships')
def api_get_ships():
    """Get all downloaded ships with pagination and filtering"""
    ship_type = request.args.get('type', '')
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    offset = (page - 1) * per_page

    conn = get_db()

    types = conn.execute(
        "SELECT DISTINCT ship_type FROM items WHERE ship_type IS NOT NULL AND ship_type != '' ORDER BY ship_type"
    ).fetchall()

    query = '''
        SELECT i.*, j.name as job_name, j.url as job_url
        FROM items i
        LEFT JOIN jobs j ON i.job_id = j.id
        WHERE i.status = 'downloaded'
    '''
    params = []

    if ship_type:
        query += ' AND i.ship_type = ?'
        params.append(ship_type)

    if search:
        query += ' AND (i.ship_name LIKE ? OR i.imo_number LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    count_query = query.replace('SELECT i.*, j.name as job_name, j.url as job_url', 'SELECT COUNT(*)')
    total = conn.execute(count_query, params).fetchone()[0]

    query += ' ORDER BY i.downloaded_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, offset])

    ships = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify({
        'ships': [dict(s) for s in ships],
        'types': [t['ship_type'] for t in types],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })

@app.route('/api/ships/<int:ship_id>')
def api_get_ship(ship_id):
    """Get single ship details"""
    conn = get_db()
    ship = conn.execute('''
        SELECT i.*, j.name as job_name, j.url as job_url
        FROM items i
        LEFT JOIN jobs j ON i.job_id = j.id
        WHERE i.id = ?
    ''', (ship_id,)).fetchone()
    conn.close()

    if not ship:
        return jsonify({'error': 'Ship not found'}), 404

    result = dict(ship)
    if result.get('metadata'):
        try:
            result['metadata'] = json.loads(result['metadata'])
        except:
            pass

    return jsonify(result)

@app.route('/api/ships/stats')
def api_ships_stats():
    """Statistics about downloaded ships"""
    conn = get_db()

    type_stats = conn.execute('''
        SELECT ship_type, COUNT(*) as count,
               COUNT(DISTINCT job_id) as sources
        FROM items
        WHERE status = 'downloaded' AND ship_type IS NOT NULL AND ship_type != ''
        GROUP BY ship_type ORDER BY count DESC
    ''').fetchall()

    total = conn.execute("SELECT COUNT(*) FROM items WHERE status = 'downloaded'").fetchone()[0]
    classified = conn.execute("SELECT COUNT(*) FROM classifications").fetchone()[0]

    conn.close()

    return jsonify({
        'total_downloaded': total,
        'total_classified': classified,
        'by_type': [{'type': t['ship_type'], 'count': t['count'], 'sources': t['sources']} for t in type_stats]
    })

# ============ API: CLASSIFY (ML) ============

@app.route('/api/classify', methods=['POST'])
def api_classify():
    """Classify an uploaded ship image"""
    from ml_engine import classify_image

    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    image_data = file.read()

    # Save upload for reference
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    save_path = os.path.join(UPLOAD_DIR, filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(save_path, 'wb') as f:
        f.write(image_data)

    results = classify_image(image_data)

    if isinstance(results, dict) and 'error' in results:
        return jsonify(results), 500

    # Save to DB
    if results:
        conn = get_db()
        conn.execute(
            'INSERT INTO classifications (image_path, predicted_type, confidence, all_predictions) VALUES (?, ?, ?, ?)',
            (save_path, results[0]['label'], results[0]['confidence'], json.dumps(results))
        )
        conn.commit()
        conn.close()

    return jsonify({
        'predictions': results,
        'image_path': save_path,
        'filename': filename
    })

@app.route('/api/classify/ship/<int:ship_id>', methods=['POST'])
def api_classify_ship(ship_id):
    """Classify an existing ship from the database"""
    from ml_engine import classify_image

    conn = get_db()
    ship = conn.execute('SELECT * FROM items WHERE id = ?', (ship_id,)).fetchone()

    if not ship:
        conn.close()
        return jsonify({'error': 'Ship not found'}), 404

    if not ship['local_path'] or not os.path.exists(ship['local_path']):
        conn.close()
        return jsonify({'error': 'Image file not found'}), 404

    results = classify_image(ship['local_path'])

    if isinstance(results, dict) and 'error' in results:
        conn.close()
        return jsonify(results), 500

    if results:
        # Update ship type
        conn.execute('UPDATE items SET ship_type = ? WHERE id = ?',
                     (results[0]['label'], ship_id))
        conn.execute(
            'INSERT INTO classifications (item_id, image_path, predicted_type, confidence, all_predictions) VALUES (?, ?, ?, ?, ?)',
            (ship_id, ship['local_path'], results[0]['label'], results[0]['confidence'], json.dumps(results))
        )
        conn.commit()

    conn.close()

    return jsonify({
        'ship_id': ship_id,
        'predictions': results
    })

# ============ API: MODEL INFO ============

@app.route('/api/model/info')
def api_model_info():
    """Get model information"""
    from ml_engine import get_model_info
    return jsonify(get_model_info())

# ============ API: TRAINING ============

@app.route('/api/training/status')
def api_training_status():
    """Get training status"""
    from ml_engine import get_training_status
    return jsonify(get_training_status())

@app.route('/api/training/start', methods=['POST'])
def api_training_start():
    """Start model training"""
    from ml_engine import start_training
    data = request.get_json() or {}

    dataset_dir = data.get('dataset_dir', '')
    epochs = data.get('epochs', 5)
    batch_size = data.get('batch_size', 8)
    learning_rate = data.get('learning_rate', 5e-5)

    if not dataset_dir or not os.path.exists(dataset_dir):
        return jsonify({'error': f'Dataset directory not found: {dataset_dir}'}), 400

    result = start_training(dataset_dir, epochs=epochs, batch_size=batch_size, learning_rate=learning_rate)
    return jsonify(result)

@app.route('/api/training/datasets')
def api_training_datasets():
    """List available datasets for training"""
    from ml_engine import get_available_datasets
    return jsonify(get_available_datasets())

# ============ API: AUGMENTATION ============

@app.route('/api/augment', methods=['POST'])
def api_augment():
    """Start image augmentation"""
    from ml_engine import augment_images
    data = request.get_json() or {}

    source_dir = data.get('source_dir', '')
    num_per_image = data.get('num_per_image', 5)
    transforms = data.get('transforms', None)

    if not source_dir or not os.path.exists(source_dir):
        return jsonify({'error': f'Source directory not found: {source_dir}'}), 400

    result = augment_images(source_dir, num_per_image=num_per_image, transforms_config=transforms)

    # Log to DB
    conn = get_db()
    conn.execute(
        'INSERT INTO augmentation_log (source_dir, num_source_images, transforms_config) VALUES (?, ?, ?)',
        (source_dir, 0, json.dumps(transforms or {}))
    )
    conn.commit()
    conn.close()

    return jsonify(result)

@app.route('/api/augment/status')
def api_augment_status():
    """Get augmentation status"""
    from ml_engine import get_augment_status
    return jsonify(get_augment_status())

# ============ API: CLASSIFICATIONS HISTORY ============

@app.route('/api/classifications')
def api_classifications():
    """Get classification history"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    offset = (page - 1) * per_page

    conn = get_db()
    total = conn.execute('SELECT COUNT(*) FROM classifications').fetchone()[0]
    rows = conn.execute(
        'SELECT * FROM classifications ORDER BY created_at DESC LIMIT ? OFFSET ?',
        (per_page, offset)
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        if item.get('all_predictions'):
            try:
                item['all_predictions'] = json.loads(item['all_predictions'])
            except:
                pass
        results.append(item)

    return jsonify({
        'classifications': results,
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    })

# ============ SERVE FILES ============

@app.route('/downloads/<path:filename>')
def serve_download(filename):
    """Serve downloaded images"""
    return send_from_directory(DOWNLOAD_DIR, filename)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded images"""
    return send_from_directory(UPLOAD_DIR, filename)

# ============ MAIN ============

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("  Ship-Scraper starting on http://localhost:3025")
    print("=" * 50)
    app.run(host='0.0.0.0', port=3025, debug=False, threaded=True)
