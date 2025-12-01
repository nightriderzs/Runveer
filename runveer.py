"""
Flask Artist Portfolio - Complete E-commerce with Custom Themes
File: app.py

Features:
- Complete e-commerce system for artwork sales
- Custom CSS theme selector (predefined + custom upload)
- Background pattern/image/color customization
- Multiple payment methods
- Telegram notifications
- Admin panel for complete management

Environment Variables:
- FLASK_SECRET: Random secret key
- ADMIN_USERNAME: Admin login
- ADMIN_PASSWORD: Admin password
- TELEGRAM_TOKEN: Bot token
- TELEGRAM_CHAT_ID: Your chat ID
- SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD for emails
- CRYPTO_WALLET_BTC, CRYPTO_WALLET_ETH, CRYPTO_WALLET_SOL
"""

import os
import sqlite3
import threading
import time
import logging
import secrets
import json
import socket
import smtplib
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
BACKGROUNDS_FOLDER = BASE_DIR / 'static' / 'backgrounds'
THEMES_FOLDER = BASE_DIR / 'static' / 'themes'
THUMBNAIL_FOLDER = BASE_DIR / 'static' / 'thumbnails'
TEMPLATE_FOLDER = BASE_DIR / 'templates'
DB_PATH = BASE_DIR / 'portfolio.db'
CONFIG_PATH = BASE_DIR / '.env'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_BACKGROUND_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
ALLOWED_CSS_EXTENSIONS = {'css'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
THUMBNAIL_SIZE = (400, 400)

# E-commerce settings
DEFAULT_SHIPPING_COST = 15.00
CRYPTO_WALLETS = {
    'bitcoin': os.getenv('CRYPTO_WALLET_BTC', 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh'),
    'ethereum': os.getenv('CRYPTO_WALLET_ETH', '0x742d35Cc6634C0532925a3b8D4f0aB1f4C6C8C9D'),
    'solana': os.getenv('CRYPTO_WALLET_SOL', '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM')
}

# Predefined themes
PREDEFINED_THEMES = {
    'default': {
        'name': 'Default Theme',
        'description': 'Clean and professional',
        'file': 'default.css'
    },
    'dark': {
        'name': 'Dark Theme',
        'description': 'Elegant dark mode',
        'file': 'dark.css'
    },
    'minimal': {
        'name': 'Minimal Theme',
        'description': 'Simple and clean',
        'file': 'minimal.css'
    },
    'artistic': {
        'name': 'Artistic Theme',
        'description': 'Creative and vibrant',
        'file': 'artistic.css'
    }
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_default_backgrounds():
    """Create default background patterns and images"""
    BACKGROUNDS_FOLDER.mkdir(parents=True, exist_ok=True)
    
    geometric_svg = '''<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#8B4513" stop-opacity="0.1"/>
                <stop offset="100%" stop-color="#D2691E" stop-opacity="0.1"/>
            </linearGradient>
        </defs>
        <rect width="100" height="100" fill="url(#grad1)"/>
        <circle cx="25" cy="25" r="8" fill="#8B4513" opacity="0.3"/>
        <circle cx="75" cy="75" r="8" fill="#D2691E" opacity="0.3"/>
        <rect x="40" y="40" width="20" height="20" fill="#F4A460" opacity="0.2"/>
    </svg>'''
    
    (BACKGROUNDS_FOLDER / 'geometric-pattern.svg').write_text(geometric_svg)

def create_default_themes():
    """Create default CSS themes"""
    THEMES_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Default Theme
    default_css = '''
:root {
    --primary: #8B4513;
    --secondary: #D2691E;
    --accent: #F4A460;
    --dark: #2C1810;
    --light: #FAF3E0;
    --text: #333333;
    --shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, var(--light) 0%, #F5E6D3 100%);
    color: var(--text);
}

.artistic-header {
    background: linear-gradient(135deg, var(--dark) 0%, var(--primary) 100%);
}

.artwork-card {
    background: white;
}
'''
    (THEMES_FOLDER / 'default.css').write_text(default_css)
    
    # Dark Theme
    dark_css = '''
:root {
    --primary: #A0522D;
    --secondary: #CD853F;
    --accent: #DEB887;
    --dark: #1A0F08;
    --light: #2D1B0F;
    --text: #E8DECD;
    --shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, var(--dark) 0%, #3A2516 100%);
    color: var(--text);
}

.artistic-header {
    background: linear-gradient(135deg, #1A0F08 0%, var(--primary) 100%);
}

.artwork-card {
    background: #2D1B0F;
    color: var(--text);
}
'''
    (THEMES_FOLDER / 'dark.css').write_text(dark_css)
    
    # Minimal Theme
    minimal_css = '''
:root {
    --primary: #666666;
    --secondary: #888888;
    --accent: #AAAAAA;
    --dark: #333333;
    --light: #FFFFFF;
    --text: #333333;
    --shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--light);
    color: var(--text);
}

.artistic-header {
    background: var(--dark);
}

.artwork-card {
    background: var(--light);
    border: 1px solid #e0e0e0;
}
'''
    (THEMES_FOLDER / 'minimal.css').write_text(minimal_css)
    
    # Artistic Theme
    artistic_css = '''
:root {
    --primary: #E27D60;
    --secondary: #85DCB0;
    --accent: #E8A87C;
    --dark: #41B3A3;
    --light: #FDF6E3;
    --text: #2C3E50;
    --shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

body {
    font-family: 'Playfair Display', serif;
    background: linear-gradient(135deg, #FDF6E3 0%, #F5E6D3 100%);
    color: var(--text);
}

.artistic-header {
    background: linear-gradient(135deg, var(--dark) 0%, var(--primary) 100%);
}

.artwork-card {
    background: white;
    border-radius: 15px;
}
'''
    (THEMES_FOLDER / 'artistic.css').write_text(artistic_css)

# Bootstrap folders and basic templates
def bootstrap():
    """Create necessary directories and default templates"""
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    BACKGROUNDS_FOLDER.mkdir(parents=True, exist_ok=True)
    THEMES_FOLDER.mkdir(parents=True, exist_ok=True)
    THUMBNAIL_FOLDER.mkdir(parents=True, exist_ok=True)
    TEMPLATE_FOLDER.mkdir(parents=True, exist_ok=True)
    
    create_default_backgrounds()
    create_default_themes()
    
    # Create default templates
    templates = {
        'index.html': INDEX_HTML,
        'admin.html': ADMIN_HTML,
        'login.html': LOGIN_HTML,
        'cart.html': CART_HTML,
        'checkout.html': CHECKOUT_HTML,
        'order_confirmation.html': ORDER_CONFIRMATION_HTML,
        'orders.html': ORDERS_HTML,
        'admin_themes.html': ADMIN_THEMES_HTML
    }
    
    for filename, content in templates.items():
        if not (TEMPLATE_FOLDER / filename).exists():
            (TEMPLATE_FOLDER / filename).write_text(content)

# Template definitions (truncated for brevity, but included in full version)
INDEX_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Runveer - Artist Portfolio</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link rel="stylesheet" href="{{ theme_url }}">
    <style>
        /* Base styles */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background-size: var(--bg-size, auto);
            background-attachment: var(--bg-attachment, fixed);
            line-height: 1.6; min-height: 100vh;
            transition: all 0.5s ease;
        }
        /* ... rest of CSS ... */
    </style>
</head>
<body>
    <!-- Header and main content -->
</body>
</html>'''

# Other template constants would be defined here...
ADMIN_HTML = '''...'''
LOGIN_HTML = '''...'''
CART_HTML = '''...'''
CHECKOUT_HTML = '''...'''
ORDER_CONFIRMATION_HTML = '''...'''
ORDERS_HTML = '''...'''
ADMIN_THEMES_HTML = '''...'''

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

def allowed_file_ext(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def validate_image(file_stream):
    """Validate image file using PIL if available"""
    if not PIL_AVAILABLE:
        return True
    
    try:
        file_stream.seek(0)
        image = Image.open(file_stream)
        image.verify()
        file_stream.seek(0)
        return True
    except Exception as e:
        logger.warning(f"Image validation failed: {e}")
        return False

def allowed_file(file, allowed_extensions):
    """Comprehensive file validation"""
    if not file or not file.filename:
        return False
    
    if not allowed_file_ext(file.filename, allowed_extensions):
        return False
    
    if allowed_extensions == ALLOWED_EXTENSIONS and (not file.content_type or not file.content_type.startswith('image/')):
        return False
    
    return True

# --- Theme and Background Management ---

def get_theme_settings():
    """Get current theme settings"""
    settings_file = BASE_DIR / 'theme_settings.json'
    default_settings = {
        'theme_type': 'predefined',
        'theme_value': 'default',
        'custom_theme_file': ''
    }
    
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except:
            return default_settings
    return default_settings

def save_theme_settings(settings):
    """Save theme settings to file"""
    settings_file = BASE_DIR / 'theme_settings.json'
    with open(settings_file, 'w') as f:
        json.dump(settings, f)

def get_background_settings():
    """Get current background settings"""
    settings_file = BASE_DIR / 'background_settings.json'
    default_settings = {
        'background_type': 'color',
        'background_value': 'linear-gradient(135deg, #FAF3E0 0%, #F5E6D3 100%)'
    }
    
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except:
            return default_settings
    return default_settings

def save_background_settings(settings):
    """Save background settings to file"""
    settings_file = BASE_DIR / 'background_settings.json'
    with open(settings_file, 'w') as f:
        json.dump(settings, f)

def get_theme_url():
    """Get the current theme URL"""
    theme_settings = get_theme_settings()
    
    if theme_settings['theme_type'] == 'custom' and theme_settings['custom_theme_file']:
        return f"/static/themes/{theme_settings['custom_theme_file']}"
    else:
        theme_name = theme_settings['theme_value']
        return f"/static/themes/{PREDEFINED_THEMES[theme_name]['file']}"

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
    """Initialize database tables with e-commerce support"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    # Works table with pricing
    cur.execute('''
    CREATE TABLE IF NOT EXISTS works (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        filename TEXT NOT NULL UNIQUE,
        price DECIMAL(10,2) DEFAULT 0.00,
        is_available BOOLEAN DEFAULT 1,
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
    
    # Customers table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        phone TEXT,
        full_name TEXT,
        address TEXT,
        city TEXT,
        country TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Orders table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        customer_id INTEGER,
        total_amount DECIMAL(10,2) NOT NULL,
        shipping_cost DECIMAL(10,2) DEFAULT 0.00,
        status TEXT DEFAULT 'pending',
        payment_method TEXT,
        payment_status TEXT DEFAULT 'pending',
        crypto_transaction_hash TEXT,
        shipping_address TEXT,
        customer_notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )
    ''')
    
    # Order items table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        artwork_id INTEGER,
        quantity INTEGER DEFAULT 1,
        unit_price DECIMAL(10,2) NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (artwork_id) REFERENCES works (id)
    )
    ''')
    
    # Cart table (session-based)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS cart_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        artwork_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (artwork_id) REFERENCES works (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized with e-commerce support")

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
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
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

# --- E-commerce Helper Functions ---

def generate_order_number():
    """Generate unique order number"""
    return f"RV{datetime.utcnow().strftime('%Y%m%d')}{secrets.token_hex(4).upper()}"

def get_cart(session_id):
    """Get cart items for session"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('''
        SELECT ci.*, w.title, w.filename, w.price 
        FROM cart_items ci 
        JOIN works w ON ci.artwork_id = w.id 
        WHERE ci.session_id = ? AND w.is_available = 1
    ''', (session_id,))
    items = cur.fetchall()
    conn.close()
    return items

def get_cart_total(session_id):
    """Calculate cart total"""
    items = get_cart(session_id)
    total = sum(item['price'] * item['quantity'] for item in items)
    return total

def send_telegram_notification(message):
    """Send notification to Telegram"""
    if not TELEGRAM_AVAILABLE or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram notification disabled")
        return False
    
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False

def send_email_notification(to_email, subject, message):
    """Send email notification to customer"""
    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        if not all([smtp_server, smtp_username, smtp_password]):
            logger.warning("Email configuration missing")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def create_order_confirmation_email(order, customer, items):
    """Create order confirmation email content"""
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
            <h1 style="color: #8B4513; text-align: center;">Runveer Art Gallery</h1>
            <h2 style="color: #D2691E;">Order Confirmation</h2>
            
            <p>Dear {customer['full_name']},</p>
            <p>Thank you for your purchase! Your order has been received and is being processed.</p>
            
            <div style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3>Order Details:</h3>
                <p><strong>Order Number:</strong> {order['order_number']}</p>
                <p><strong>Order Date:</strong> {order['created_at']}</p>
                <p><strong>Total Amount:</strong> ${order['total_amount']:.2f}</p>
                <p><strong>Payment Method:</strong> {order['payment_method'].title()}</p>
            </div>
            
            <div style="margin: 20px 0;">
                <h3>Items Purchased:</h3>
                {"".join(f"<p>- {item['title']} (${item['unit_price']:.2f})</p>" for item in items)}
            </div>
            
            <div style="background: #e8f5e8; padding: 15px; border-radius: 5px;">
                <h3>Delivery Information:</h3>
                <p>Your artwork will be carefully packaged and shipped to you within 3-5 business days.</p>
                <p>You will receive a tracking number once your order has been shipped.</p>
            </div>
            
            <p>If you have any questions, please reply to this email or contact us at the provided phone number.</p>
            
            <hr style="margin: 30px 0;">
            <p style="text-align: center; color: #666;">
                Runveer Art Gallery<br>
                Creating timeless pieces for your space
            </p>
        </div>
    </body>
    </html>
    """

# --- Routes ---

@app.route('/')
def index():
    """Main portfolio page"""
    db = get_db()
    cur = db.execute('SELECT * FROM works ORDER BY created_at DESC')
    works = cur.fetchall()
    
    theme_url = get_theme_url()
    return render_template('index.html', works=works, theme_url=theme_url)

@app.route('/api/background-settings')
def background_settings():
    """API endpoint to get background settings"""
    return jsonify(get_background_settings())

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

@app.route('/admin/themes', methods=['GET', 'POST'])
@login_required
def admin_themes():
    """Theme management page"""
    if request.method == 'POST':
        try:
            theme_type = request.form.get('theme_type')
            theme_value = request.form.get('theme_value')
            custom_theme_file = ''
            
            if theme_type == 'custom' and 'custom_theme_file' in request.files:
                file = request.files['custom_theme_file']
                if file and file.filename:
                    if allowed_file(file, ALLOWED_CSS_EXTENSIONS):
                        filename = secure_filename(file.filename)
                        file.save(THEMES_FOLDER / filename)
                        custom_theme_file = filename
                    else:
                        flash('Invalid CSS file', 'error')
                        return redirect(url_for('admin_themes'))
            
            settings = {
                'theme_type': theme_type,
                'theme_value': theme_value,
                'custom_theme_file': custom_theme_file
            }
            
            save_theme_settings(settings)
            flash('Theme updated successfully!', 'success')
            
        except Exception as e:
            logger.error(f"Theme update error: {e}")
            flash('Failed to update theme', 'error')
    
    theme_settings = get_theme_settings()
    return render_template('admin_themes.html', 
                         theme_settings=theme_settings,
                         predefined_themes=PREDEFINED_THEMES)

@app.route('/admin/update-background', methods=['POST'])
@login_required
def update_background():
    """Update background settings"""
    try:
        background_type = request.form.get('background_type')
        background_value = request.form.get('background_value')
        
        if background_type == 'image' and 'background_file' in request.files:
            file = request.files['background_file']
            if file and file.filename:
                if allowed_file(file, ALLOWED_BACKGROUND_EXTENSIONS):
                    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                    original_ext = secure_filename(file.filename).rsplit('.', 1)[-1].lower()
                    filename = f"bg_{timestamp}.{original_ext}"
                    dest_path = BACKGROUNDS_FOLDER / filename
                    
                    file.save(str(dest_path))
                    background_value = f"/static/backgrounds/{filename}"
                else:
                    flash('Invalid background image file', 'error')
                    return redirect(url_for('admin') + '#background')
        
        settings = {
            'background_type': background_type,
            'background_value': background_value
        }
        
        save_background_settings(settings)
        flash('Background updated successfully!', 'success')
        
    except Exception as e:
        logger.error(f"Background update error: {e}")
        flash('Failed to update background', 'error')
    
    return redirect(url_for('admin') + '#background')

@app.route('/admin/upload', methods=['POST'])
@login_required
def upload():
    """Handle file uploads with pricing"""
    try:
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('admin'))
        
        file = request.files['file']
        title = request.form.get('title', '').strip() or 'Untitled'
        description = request.form.get('description', '').strip()
        price = request.form.get('price', '0')
        
        # Validate price
        try:
            price = float(price) if price else 0.0
        except ValueError:
            price = 0.0
        
        # Validate file
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('admin'))
        
        if not allowed_file(file, ALLOWED_EXTENSIONS):
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
            'INSERT INTO works (title, description, filename, price, created_at) VALUES (?, ?, ?, ?, ?)',
            (title, description, filename, price, datetime.utcnow().isoformat())
        )
        db.commit()
        
        logger.info(f"Uploaded new work: {filename} - ${price:.2f}")
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

# --- E-commerce Routes ---

@app.route('/cart')
def cart():
    """Shopping cart page"""
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    
    cart_items = get_cart(session_id)
    total = get_cart_total(session_id)
    shipping = DEFAULT_SHIPPING_COST
    grand_total = total + shipping
    
    theme_url = get_theme_url()
    return render_template('cart.html', 
                         cart_items=cart_items, 
                         total=total, 
                         shipping=shipping, 
                         grand_total=grand_total,
                         theme_url=theme_url)

@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    """API endpoint to add item to cart"""
    try:
        data = request.get_json()
        artwork_id = data.get('artwork_id')
        session_id = session.get('session_id', str(uuid.uuid4()))
        session['session_id'] = session_id
        
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        
        # Check if item already in cart
        cur.execute('SELECT id FROM cart_items WHERE session_id = ? AND artwork_id = ?', 
                   (session_id, artwork_id))
        existing = cur.fetchone()
        
        if existing:
            cur.execute('UPDATE cart_items SET quantity = quantity + 1 WHERE id = ?', 
                       (existing['id'],))
        else:
            cur.execute('INSERT INTO cart_items (session_id, artwork_id) VALUES (?, ?)', 
                       (session_id, artwork_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Item added to cart'})
    
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        return jsonify({'success': False, 'message': 'Failed to add item'})

@app.route('/api/cart/update', methods=['POST'])
def update_cart():
    """API endpoint to update cart item quantity"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        quantity = data.get('quantity', 1)
        session_id = session.get('session_id')
        
        if quantity <= 0:
            # Remove item
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute('DELETE FROM cart_items WHERE id = ? AND session_id = ?', 
                       (item_id, session_id))
            conn.commit()
            conn.close()
        else:
            # Update quantity
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute('UPDATE cart_items SET quantity = ? WHERE id = ? AND session_id = ?', 
                       (quantity, item_id, session_id))
            conn.commit()
            conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Error updating cart: {e}")
        return jsonify({'success': False})

@app.route('/api/cart/count')
def cart_count():
    """API endpoint to get cart item count"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'count': 0})
    
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('SELECT SUM(quantity) as total FROM cart_items WHERE session_id = ?', (session_id,))
    result = cur.fetchone()
    count = result['total'] or 0
    conn.close()
    
    return jsonify({'count': count})

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Checkout page"""
    session_id = session.get('session_id')
    if not session_id:
        return redirect('/cart')
    
    cart_items = get_cart(session_id)
    if not cart_items:
        return redirect('/cart')
    
    total = get_cart_total(session_id)
    shipping = DEFAULT_SHIPPING_COST
    grand_total = total + shipping
    
    theme_url = get_theme_url()
    
    if request.method == 'POST':
        # Process checkout
        try:
            # Get customer data
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')
            city = request.form.get('city')
            country = request.form.get('country')
            payment_method = request.form.get('payment_method')
            customer_notes = request.form.get('customer_notes')
            crypto_transaction_hash = request.form.get('crypto_transaction_hash')
            
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            
            # Create or get customer
            cur.execute('SELECT id FROM customers WHERE email = ?', (email,))
            customer = cur.fetchone()
            
            if customer:
                customer_id = customer['id']
                cur.execute('''UPDATE customers SET 
                            phone = ?, full_name = ?, address = ?, city = ?, country = ?
                            WHERE id = ?''', 
                          (phone, full_name, address, city, country, customer_id))
            else:
                cur.execute('''INSERT INTO customers 
                            (email, phone, full_name, address, city, country) 
                            VALUES (?, ?, ?, ?, ?, ?)''',
                          (email, phone, full_name, address, city, country))
                customer_id = cur.lastrowid
            
            # Create order
            order_number = generate_order_number()
            cur.execute('''INSERT INTO orders 
                        (order_number, customer_id, total_amount, shipping_cost, 
                         payment_method, payment_status, crypto_transaction_hash,
                         shipping_address, customer_notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (order_number, customer_id, grand_total, shipping,
                       payment_method, 'pending', crypto_transaction_hash,
                       f"{address}, {city}, {country}", customer_notes))
            order_id = cur.lastrowid
            
            # Create order items
            for item in cart_items:
                cur.execute('''INSERT INTO order_items 
                            (order_id, artwork_id, quantity, unit_price)
                            VALUES (?, ?, ?, ?)''',
                          (order_id, item['artwork_id'], item['quantity'], item['price']))
            
            # Clear cart
            cur.execute('DELETE FROM cart_items WHERE session_id = ?', (session_id,))
            
            conn.commit()
            
            # Get order details for notification
            cur.execute('''SELECT o.*, c.email, c.phone, c.full_name 
                         FROM orders o JOIN customers c ON o.customer_id = c.id 
                         WHERE o.id = ?''', (order_id,))
            order = cur.fetchone()
            
            cur.execute('''SELECT oi.*, w.title FROM order_items oi 
                         JOIN works w ON oi.artwork_id = w.id 
                         WHERE oi.order_id = ?''', (order_id,))
            items = cur.fetchall()
            
            conn.close()
            
            # Send notifications
            telegram_message = f"""
🎨 NEW ARTWORK PURCHASE 🎨

Order: {order['order_number']}
Customer: {order['full_name']}
Email: {order['email']}
Phone: {order['phone']}
Total: ${order['total_amount']:.2f}
Payment: {order['payment_method']}

Items:
{"".join(f"• {item['title']} (${item['unit_price']:.2f})" for item in items)}

Shipping to: {order['shipping_address']}
            """
            
            send_telegram_notification(telegram_message)
            
            # Send email confirmation
            email_content = create_order_confirmation_email(order, order, items)
            send_email_notification(order['email'], 
                                  f"Order Confirmation - {order['order_number']}", 
                                  email_content)
            
            flash('Order placed successfully! You will receive a confirmation email shortly.', 'success')
            return redirect(f'/order-confirmation/{order_number}')
            
        except Exception as e:
            logger.error(f"Checkout error: {e}")
            flash('Error processing order. Please try again.', 'error')
            return redirect('/checkout')
    
    return render_template('checkout.html',
                         cart_items=cart_items,
                         total=total,
                         shipping=shipping,
                         grand_total=grand_total,
                         crypto_wallets=CRYPTO_WALLETS,
                         theme_url=theme_url)

@app.route('/order-confirmation/<order_number>')
def order_confirmation(order_number):
    """Order confirmation page"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('''SELECT o.*, c.full_name, c.email, c.phone 
                 FROM orders o JOIN customers c ON o.customer_id = c.id 
                 WHERE o.order_number = ?''', (order_number,))
    order = cur.fetchone()
    
    if not order:
        abort(404)
    
    cur.execute('''SELECT oi.*, w.title, w.filename 
                 FROM order_items oi JOIN works w ON oi.artwork_id = w.id 
                 WHERE oi.order_id = ?''', (order['id'],))
    items = cur.fetchall()
    
    conn.close()
    
    theme_url = get_theme_url()
    return render_template('order_confirmation.html',
                         order=order,
                         items=items,
                         crypto_wallets=CRYPTO_WALLETS,
                         theme_url=theme_url)

@app.route('/admin/orders')
@login_required
def admin_orders():
    """Admin orders management"""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('''SELECT o.*, c.full_name, c.email, c.phone 
                 FROM orders o JOIN customers c ON o.customer_id = c.id 
                 ORDER BY o.created_at DESC''')
    orders = cur.fetchall()
    conn.close()
    
    theme_url = get_theme_url()
    return render_template('orders.html', orders=orders, theme_url=theme_url)

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

def find_available_port(start_port=5000, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return start_port

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
    
    # Get port from environment variable or find available port
    port = int(os.environ.get('PORT', 5000))
    
    if port == 5000:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 5000))
        except OSError:
            logger.warning("Port 5000 is busy, finding available port...")
            port = find_available_port(5001, 10)
            logger.info(f"Using alternative port: {port}")
    
    # Start Flask app
    logger.info(f"Starting Flask app on port {port}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if telegram_updater:
            telegram_updater.stop()

if __name__ == '__main__':
    main()
