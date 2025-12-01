"""
Flask artist portfolio with login + direct Telegram image uploads
Enhanced version with better security, thumbnails, and error handling

Features:
- Single-file Flask app that bootstraps its folders and templates on first run
- SQLite database to store "works" metadata
- Admin login with password hashing
- Admin UI to upload images, edit/delete entries
- Telegram integration for automatic image downloads (optional)
- Thumbnail generation
- Enhanced security and file validation

Security notes:
- Use environment variables for sensitive data
- For production: Use HTTPS, CSRF protection, rate limiting, etc.

Requirements:
- Python 3.8+
- pip install flask python-dotenv python-telegram-bot==13.15 Pillow

Run:
- export TELEGRAM_TOKEN=... TELEGRAM_CHAT_ID=... FLASK_SECRET=...
- python3 flask_portfolio_enhanced.py
"""

import os
import sqlite3
import threading
import time
import logging
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path
from io import BytesIO

from flask import (
    Flask, request, g, redirect, url_for, render_template, send_from_directory, flash,
    session, abort, jsonify
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from dotenv import load_dotenv

# Try to import telegram bot
TELEGRAM_AVAILABLE = False
try:
    from telegram import Bot, Update
    from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
    TELEGRAM_AVAILABLE = True
except ImportError:
    print("Telegram bot features disabled: python-telegram-bot not installed")
    # Create dummy classes for type hints
    class Update:
        pass
    class CallbackContext:
        pass

# Try to import PIL for image processing
PIL_AVAILABLE = False
try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    print("Thumbnail generation disabled: Pillow not installed")

# --- Config ---
BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
THUMBNAIL_FOLDER = BASE_DIR / 'static' / 'thumbnails'
TEMPLATE_FOLDER = BASE_DIR / 'templates'
DB_PATH = BASE_DIR / 'portfolio.db'
CONFIG_PATH = BASE_DIR / '.env'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
THUMBNAIL_SIZE = (400, 400)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bootstrap folders and basic templates
def bootstrap():
    """Create necessary directories and default templates"""
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    THUMBNAIL_FOLDER.mkdir(parents=True, exist_ok=True)
    TEMPLATE_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Create default templates if they don't exist
    if not (TEMPLATE_FOLDER / 'index.html').exists():
        (TEMPLATE_FOLDER / 'index.html').write_text(INDEX_HTML)
    if not (TEMPLATE_FOLDER / 'admin.html').exists():
        (TEMPLATE_FOLDER / 'admin.html').write_text(ADMIN_HTML)
    if not (TEMPLATE_FOLDER / 'login.html').exists():
        (TEMPLATE_FOLDER / 'login.html').write_text(LOGIN_HTML)

# Default templates
INDEX_HTML = '''
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Artist Portfolio</title>
    <style>
      body{font-family:system-ui, sans-serif; background:#f6f6f6; color:#111; margin:0}
      .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:24px;padding:24px;max-width:1400px;margin:0 auto}
      .card{background:#fff;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,.1);overflow:hidden;transition:transform 0.2s, box-shadow 0.2s}
      .card:hover{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,0,0,.15)}
      .card img{width:100%;height:240px;object-fit:cover;display:block}
      .meta{padding:16px}
      .meta h3{margin:0 0 8px 0;font-size:1.2em}
      .meta p{color:#666;margin:0 0 8px 0;line-height:1.4}
      .meta small{color:#999;font-size:0.9em}
      header{display:flex;align-items:center;justify-content:space-between;padding:16px 24px;background:#222;color:#fff}
      header h1{margin:0;font-size:1.5em}
      a.button{background:#4CAF50;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:500;transition:background 0.2s}
      a.button:hover{background:#45a049}
      .empty-state{text-align:center;padding:60px 24px;color:#666}
      .empty-state h2{margin:0 0 16px 0;color:#333}
    </style>
  </head>
  <body>
    <header>
      <h1>Artist Portfolio</h1>
      <div>
        <a class="button" href="/admin">Admin</a>
      </div>
    </header>
    <main>
      {% if works %}
      <div class="grid">
        {% for work in works %}
        <article class="card">
          <img src="/static/uploads/{{ work.filename }}" alt="{{ work.title }}" loading="lazy">
          <div class="meta">
            <h3>{{ work.title }}</h3>
            <p>{{ work.description or '' }}</p>
            <small>Added {{ work.created_at[:10] }}</small>
          </div>
        </article>
        {% endfor %}
      </div>
      {% else %}
      <div class="empty-state">
        <h2>No artwork yet</h2>
        <p>Check back soon for new additions to the portfolio.</p>
      </div>
      {% endif %}
    </main>
  </body>
</html>
'''

ADMIN_HTML = '''
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Admin - Portfolio</title>
    <style>
      body{font-family:system-ui, sans-serif;padding:24px;max-width:1200px;margin:0 auto}
      .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:32px}
      .alert{background:#d4edda;color:#155724;padding:12px;border-radius:6px;margin-bottom:16px;border:1px solid #c3e6cb}
      .alert.error{background:#f8d7da;color:#721c24;border-color:#f5c6cb}
      form{display:flex;flex-direction:column;gap:12px;max-width:600px;margin-bottom:40px}
      input,textarea,select{padding:12px;border:1px solid #ddd;border-radius:6px;font-family:inherit;font-size:inherit}
      button{background:#2196F3;color:#fff;padding:12px 20px;border:none;border-radius:6px;cursor:pointer;font-size:inherit}
      button:hover{background:#0b7dda}
      button.delete{background:#dc3545}
      button.delete:hover{background:#c82333}
      img.thumb{max-width:120px;border-radius:6px;height:80px;object-fit:cover}
      table{width:100%;border-collapse:collapse;margin-top:20px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1)}
      th{background:#f8f9fa;padding:16px;text-align:left;font-weight:600;border-bottom:1px solid #dee2e6}
      td{padding:16px;border-bottom:1px solid #dee2e6}
      tr:last-child td{border-bottom:none}
      .actions{display:flex;gap:8px}
      .section{margin-bottom:40px;padding-bottom:32px;border-bottom:1px solid #eee}
    </style>
  </head>
  <body>
    <div class="header">
      <h1>Portfolio Admin</h1>
      <div>
        <a href="/">View Portfolio</a> | 
        <a href="/logout">Logout</a>
      </div>
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert{% if category == 'error' %} error{% endif %}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="section">
      <h2>Upload New Work</h2>
      <form method="post" action="/admin/upload" enctype="multipart/form-data">
        <input type="text" name="title" placeholder="Title" required>
        <textarea name="description" placeholder="Description" rows="3"></textarea>
        <input type="file" name="file" accept="image/*" required>
        <button type="submit">Upload Image</button>
      </form>
    </div>

    <div class="section">
      <h2>Existing Works ({{ works|length }})</h2>
      {% if works %}
      <table>
        <thead>
          <tr>
            <th>Preview</th>
            <th>Details</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {% for work in works %}
          <tr>
            <td><img src="/static/uploads/{{ work.filename }}" class="thumb" alt="{{ work.title }}"></td>
            <td>
              <strong>{{ work.title }}</strong><br>
              {{ work.description or 'No description' }}<br>
              <small>Added: {{ work.created_at[:16] }}</small>
            </td>
            <td>
              <div class="actions">
                <form method="post" action="/admin/delete" onsubmit="return confirm('Delete this work?')">
                  <input type="hidden" name="id" value="{{ work.id }}">
                  <button type="submit" class="delete">Delete</button>
                </form>
              </div>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
      <p>No works yet. Upload your first image above.</p>
      {% endif %}
    </div>
  </body>
</html>
'''

LOGIN_HTML = '''
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Admin Login</title>
    <style>
      body{font-family:system-ui, sans-serif;padding:24px;max-width:400px;margin:60px auto}
      .login-card{background:#fff;padding:32px;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.1)}
      h1{text-align:center;margin:0 0 32px 0;color:#333}
      form{display:flex;flex-direction:column;gap:16px}
      input{padding:14px;border:1px solid #ddd;border-radius:8px;font-size:16px}
      button{background:#2196F3;color:#fff;padding:14px;border:none;border-radius:8px;cursor:pointer;font-size:16px;font-weight:500}
      button:hover{background:#0b7dda}
      .alert{background:#f8d7da;color:#721c24;padding:12px;border-radius:6px;margin-bottom:16px}
    </style>
  </head>
  <body>
    <div class="login-card">
      <h1>Admin Login</h1>
      
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class="alert">
            {% for message in messages %}
              {{ message }}
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}

      <form method="post" action="/login">
        <input name="username" placeholder="Username" required autofocus>
        <input name="password" type="password" placeholder="Password" required>
        <button type="submit">Login</button>
      </form>
    </div>
  </body>
</html>
'''

# --- Flask app ---
app = Flask(__name__, template_folder=str(TEMPLATE_FOLDER))
app.secret_key = os.getenv('FLASK_SECRET', secrets.token_hex(32))
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Load environment variables
load_dotenv(CONFIG_PATH)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- File validation helpers ---

def allowed_file_ext(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(file_stream):
    """Validate image file using PIL if available"""
    if not PIL_AVAILABLE:
        return True  # Skip validation if PIL not available
    
    try:
        file_stream.seek(0)
        image = Image.open(file_stream)
        image.verify()
        file_stream.seek(0)
        return True
    except Exception as e:
        logger.warning(f"Image validation failed: {e}")
        return False

def allowed_file(file):
    """Comprehensive file validation"""
    if not file or not file.filename:
        return False
    
    # Check extension
    if not allowed_file_ext(file.filename):
        return False
    
    # Check content type
    if not file.content_type or not file.content_type.startswith('image/'):
        return False
    
    return True

# --- DB helpers ---

def get_db():
    """Get database connection with request context"""
    db = getattr(g, '_database', None)
    if db is None:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        db = g._database = conn
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection at end of request"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database tables"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    # Works table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS works (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        filename TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL
    )
    ''')
    
    # Users table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def ensure_admin():
    """Create default admin user if none exists"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    count = cur.fetchone()[0]
    
    if count == 0:
        default_username = os.getenv('ADMIN_USERNAME', 'admin')
        default_password = os.getenv('ADMIN_PASSWORD', 'admin')
        
        pw_hash = generate_password_hash(default_password)
        cur.execute('INSERT INTO users (username, password_hash) VALUES (?,?)', 
                   (default_username, pw_hash))
        conn.commit()
        logger.info(f"Created default admin user: {default_username}")
    
    conn.close()

# --- Image processing helpers ---

def create_thumbnail(original_path, filename):
    """Create thumbnail version of image"""
    if not PIL_AVAILABLE:
        return None
    
    try:
        thumb_filename = f"thumb_{filename}"
        thumb_path = THUMBNAIL_FOLDER / thumb_filename
        
        with Image.open(original_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Create thumbnail
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            img.save(thumb_path, optimize=True, quality=85)
        
        return thumb_filename
    except Exception as e:
        logger.error(f"Thumbnail creation failed for {filename}: {e}")
        return None

def optimize_image(image_path):
    """Optimize image file size"""
    if not PIL_AVAILABLE:
        return
    
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Save with optimization
            img.save(image_path, optimize=True, quality=85)
    except Exception as e:
        logger.warning(f"Image optimization failed: {e}")

# --- Auth helpers ---

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
def index():
    """Main portfolio page"""
    db = get_db()
    cur = db.execute('SELECT * FROM works ORDER BY created_at DESC')
    works = cur.fetchall()
    return render_template('index.html', works=works)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        db = get_db()
        cur = db.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cur.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    """Admin dashboard"""
    db = get_db()
    cur = db.execute('SELECT * FROM works ORDER BY created_at DESC')
    works = cur.fetchall()
    return render_template('admin.html', works=works)

@app.route('/admin/upload', methods=['POST'])
@login_required
def upload():
    """Handle file uploads"""
    try:
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('admin'))
        
        file = request.files['file']
        title = request.form.get('title', '').strip() or 'Untitled'
        description = request.form.get('description', '').strip()
        
        # Validate file
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('admin'))
        
        if not allowed_file(file):
            flash('Invalid file type. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS), 'error')
            return redirect(url_for('admin'))
        
        # Validate image content
        if not validate_image(file.stream):
            flash('Invalid image file', 'error')
            return redirect(url_for('admin'))
        
        # Generate secure filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        original_ext = secure_filename(file.filename).rsplit('.', 1)[-1].lower()
        random_str = secrets.token_hex(4)
        filename = f"{timestamp}_{random_str}.{original_ext}"
        dest_path = UPLOAD_FOLDER / filename
        
        # Save file
        file.save(str(dest_path))
        
        # Optimize image
        optimize_image(dest_path)
        
        # Create thumbnail
        create_thumbnail(dest_path, filename)
        
        # Save to database
        db = get_db()
        db.execute(
            'INSERT INTO works (title, description, filename, created_at) VALUES (?, ?, ?, ?)',
            (title, description, filename, datetime.utcnow().isoformat())
        )
        db.commit()
        
        logger.info(f"Uploaded new work: {filename}")
        flash('Image uploaded successfully!')
        
    except RequestEntityTooLarge:
        flash('File too large (max 16MB)', 'error')
    except Exception as e:
        logger.error(f"Upload error: {e}")
        flash('Upload failed', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/delete', methods=['POST'])
@login_required
def delete_work():
    """Delete a work and its associated files"""
    try:
        work_id = request.form.get('id')
        if not work_id:
            flash('No work specified', 'error')
            return redirect(url_for('admin'))
        
        db = get_db()
        
        # Get work details
        cur = db.execute('SELECT filename FROM works WHERE id = ?', (work_id,))
        work = cur.fetchone()
        
        if not work:
            flash('Work not found', 'error')
            return redirect(url_for('admin'))
        
        filename = work['filename']
        
        # Delete files
        files_to_delete = [
            UPLOAD_FOLDER / filename,
            THUMBNAIL_FOLDER / f"thumb_{filename}"
        ]
        
        for file_path in files_to_delete:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete file {file_path}: {e}")
        
        # Delete from database
        db.execute('DELETE FROM works WHERE id = ?', (work_id,))
        db.commit()
        
        logger.info(f"Deleted work: {filename}")
        flash('Work deleted successfully')
        
    except Exception as e:
        logger.error(f"Delete error: {e}")
        flash('Delete failed', 'error')
    
    return redirect(url_for('admin'))

@app.errorhandler(413)
def too_large(e):
    """Handle file too large errors"""
    flash('File too large (max 16MB)', 'error')
    return redirect(url_for('admin'))

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return "Page not found", 404

# --- Telegram integration ---

def handle_telegram_photo(update, context):
    """Handle incoming Telegram photos"""
    if not TELEGRAM_AVAILABLE:
        return
        
    try:
        chat_id = str(update.effective_chat.id)
        if str(TELEGRAM_CHAT_ID) != chat_id:
            logger.info(f"Ignoring message from unauthorized chat: {chat_id}")
            return
        
        photos = update.message.photo
        if not photos:
            return
        
        # Get highest resolution photo
        file_id = photos[-1].file_id
        bot = context.bot
        file = bot.get_file(file_id)
        
        # Download image
        bio = BytesIO()
        file.download(out=bio)
        bio.seek(0)
        
        # Validate image
        if not validate_image(bio):
            logger.warning("Invalid image received from Telegram")
            return
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        random_str = secrets.token_hex(4)
        filename = f"telegram_{timestamp}_{random_str}.jpg"
        dest_path = UPLOAD_FOLDER / filename
        
        # Save file
        with open(str(dest_path), 'wb') as f:
            f.write(bio.getvalue())
        
        # Optimize and create thumbnail
        optimize_image(dest_path)
        create_thumbnail(dest_path, filename)
        
        # Get caption or use default title
        caption = update.message.caption
        title = caption.strip() if caption else f"Telegram {timestamp}"
        
        # Insert into database
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO works (title, description, filename, created_at) VALUES (?, ?, ?, ?)',
            (title, 'Uploaded from Telegram', filename, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        
        logger.info(f"Saved Telegram image: {filename}")
        
        # Send confirmation
        update.message.reply_text(f"✅ Image added to portfolio: {title}")
        
    except Exception as e:
        logger.error(f"Error handling Telegram message: {e}")
        try:
            update.message.reply_text("❌ Failed to process image")
        except:
            pass

def start_telegram_bot(token, allowed_chat_id):
    """Start Telegram bot in background thread"""
    if not TELEGRAM_AVAILABLE:
        logger.warning("python-telegram-bot not installed; Telegram integration disabled")
        return None
    
    try:
        updater = Updater(token=token, use_context=True)
        dispatcher = updater.dispatcher
        
        # Add photo handler
        dispatcher.add_handler(MessageHandler(Filters.photo, handle_telegram_photo))
        
        # Start polling
        updater.start_polling()
        logger.info("Telegram bot started (polling mode)")
        
        # Store updater for graceful shutdown
        return updater
        
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")
        return None

# --- App startup ---

def main():
    """Main application entry point"""
    # Bootstrap directories and templates
    bootstrap()
    
    # Initialize database
    init_db()
    ensure_admin()
    
    # Start Telegram bot if configured
    telegram_updater = None
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            telegram_updater = start_telegram_bot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
        except Exception as e:
            logger.error(f"Telegram bot startup failed: {e}")
    else:
        logger.warning("Telegram token or chat ID not set; Telegram integration disabled")
    
    # Start Flask app
    logger.info("Starting Flask app on http://127.0.0.1:5000")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Cleanup
        if telegram_updater:
            telegram_updater.stop()

if __name__ == '__main__':
    main()
