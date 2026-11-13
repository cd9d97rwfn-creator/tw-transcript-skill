"""Single-user private upload service. Run exactly one worker / replica."""
from __future__ import annotations
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
import uuid
from flask import Flask, abort, jsonify, render_template, request, send_file
from .cloud import process

EXTENSIONS = {'.mp3', '.mp4', '.m4a', '.wav', '.mov', '.aac', '.flac', '.ogg', '.webm', '.m4v', '.aiff', '.aif'}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(DATA_DIR=os.environ.get('DATA_DIR', 'output/cloud'),
        MAX_CONTENT_LENGTH=int(os.environ.get('MAX_UPLOAD_MB', '500')) * 1024 * 1024,
        APP_PASSWORD=os.environ.get('APP_PASSWORD', ''), START_WORKER=True,
        GITHUB_REPO_URL=os.environ.get('GITHUB_REPO_URL', 'https://github.com/cd9d97rwfn-creator/tw-transcript-skill'))
    if test_config:
        app.config.update(test_config)
    if len(app.config['APP_PASSWORD']) < 20:
        raise RuntimeError('APP_PASSWORD must contain at least 20 characters.')
    github_url = app.config['GITHUB_REPO_URL'].strip()
    if github_url and not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?', github_url):
        raise ValueError('GITHUB_REPO_URL must be an HTTPS GitHub repository URL.')
    root = Path(app.config['DATA_DIR']).resolve()
    root.mkdir(parents=True, exist_ok=True)
    csrf = secrets.token_urlsafe(32)

    def db():
        connection = sqlite3.connect(root/'jobs.sqlite', timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    with db() as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, name TEXT, status TEXT, message TEXT, created REAL)')
        # In-flight calls may have been billed before a crash: require explicit retry.
        connection.execute("UPDATE jobs SET status='failed', message='服務重新啟動，工作中斷。可重試；已儲存的分段不會重送，未儲存的請求可能再次計費。' WHERE status='running'")

    @app.before_request
    def authorize():
        if request.path == '/health':
            return
        auth = request.authorization
        if not auth or not hmac.compare_digest((auth.password or '').encode(), app.config['APP_PASSWORD'].encode()):
            return ('需要登入', 401, {'WWW-Authenticate': 'Basic realm="Transcript", charset="UTF-8"'})
        if request.method == 'POST' and not hmac.compare_digest(request.headers.get('X-CSRF-Token', ''), csrf):
            abort(403)

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'unsafe-inline'; script-src 'nonce-" + csrf + "'; frame-ancestors 'none'"
        return response

    @app.get('/health')
    def health():
        return jsonify(status='ok')

    @app.get('/')
    def index():
        return render_template('index.html', csrf=csrf, limit=app.config['MAX_CONTENT_LENGTH']//1024//1024, github_url=github_url)

    @app.get('/api/jobs')
    def jobs():
        with db() as connection:
            rows = connection.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 100').fetchall()
        return jsonify([dict(row) for row in rows])

    @app.post('/api/jobs')
    def upload():
        if not os.environ.get('OPENAI_API_KEY') and not app.testing:
            return jsonify(error='尚未設定轉錄 API 金鑰。'), 503
        media = request.files.get('file')
        if not media or not media.filename:
            return jsonify(error='請選擇音檔或影片。'), 400
        suffix = Path(media.filename).suffix.lower()
        if suffix not in EXTENSIONS:
            return jsonify(error='不支援此檔案格式。'), 400
        identifier = uuid.uuid4().hex
        folder = root / identifier
        folder.mkdir()
        path = folder / ('input' + suffix)
        media.save(path)
        if path.stat().st_size == 0:
            path.unlink()
            folder.rmdir()
            return jsonify(error='檔案是空的。'), 400
        with db() as connection:
            connection.execute('INSERT INTO jobs VALUES (?, ?, ?, ?, ?)',
                (identifier, Path(media.filename).name[:200], 'queued', '等待轉錄', time.time()))
        return jsonify(id=identifier), 202

    def get_job(identifier):
        if not re.fullmatch('[a-f0-9]{32}', identifier):
            abort(404)
        with db() as connection:
            row = connection.execute('SELECT * FROM jobs WHERE id=?', (identifier,)).fetchone()
        if not row:
            abort(404)
        return row

    @app.get('/api/jobs/<identifier>/download')
    def download(identifier):
        row = get_job(identifier)
        if row['status'] != 'done':
            abort(409)
        formats = {
            'zip': ('result.zip', '完整校稿紀錄.zip', 'application/zip'),
            'txt': ('export/專有名詞校稿版.txt', '專有名詞校稿版.txt', 'text/plain; charset=utf-8'),
            'md': ('export/專有名詞校稿版.md', '專有名詞校稿版.md', 'text/markdown; charset=utf-8'),
            'json': ('export/raw_segments.json', '原始分段.json', 'application/json'),
        }
        selected = request.args.get('format', 'zip')
        if selected not in formats:
            return jsonify(error='支援 TXT、Markdown、JSON 與 ZIP；目前不提供逐句時間戳字幕。'), 400
        relative, name, mime = formats[selected]
        path = root / identifier / relative
        if not path.is_file():
            return jsonify(error='此格式檔案不存在，請下載完整 ZIP 或重新處理。'), 404
        return send_file(path, as_attachment=True, download_name=name, mimetype=mime)

    @app.post('/api/jobs/<identifier>/retry')
    def retry(identifier):
        get_job(identifier)
        with db() as connection:
            result = connection.execute("UPDATE jobs SET status='queued', message='等待重試' WHERE id=? AND status='failed'", (identifier,))
            if not result.rowcount:
                abort(409)
        return jsonify(status='queued')

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error='超過上傳大小限制，請先壓縮或切分檔案。'), 413

    def update(identifier, status, message):
        with db() as connection:
            connection.execute('UPDATE jobs SET status=?, message=? WHERE id=?', (status, message, identifier))

    def worker():
        while True:
            with db() as connection:
                row = connection.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
                if row:
                    connection.execute("UPDATE jobs SET status='running', message='準備音訊' WHERE id=?", (row['id'],))
            if not row:
                time.sleep(2)
                continue
            identifier = row['id']
            try:
                # A completed archive can survive interruption before database commit.
                if not (root/identifier/'result.zip').exists():
                    process(root/identifier, lambda message: update(identifier, 'running', message))
                update(identifier, 'done', '完成；請下載並核對逐字稿')
            except Exception as error:
                # Do not log exception strings containing provider data or secrets.
                message = str(error) if isinstance(error, ValueError) else '處理失敗（'+type(error).__name__+'），請稍後重試。'
                update(identifier, 'failed', message)
    if app.config['START_WORKER']:
        threading.Thread(target=worker, daemon=True).start()
    return app
