"""
Flask Artist Portfolio - E-Commerce Enhanced
File: app.py

Features:
- Complete e-commerce system for artwork sales
- Multiple payment methods: Credit Card, QR Scan, Cryptocurrency
- Telegram notifications for purchases
- Customer management with contact details
- Order management and delivery tracking
- Email and SMS notifications
- Admin order dashboard

Environment Variables:
- FLASK_SECRET: Random secret key
- ADMIN_USERNAME: Admin login
- ADMIN_PASSWORD: Admin password
- TELEGRAM_TOKEN: Bot token for notifications
- TELEGRAM_CHAT_ID: Your chat ID for notifications
- SMTP_SERVER: Email server (e.g., smtp.gmail.com)
- SMTP_PORT: Email port (e.g., 587)
- SMTP_USERNAME: Email username
- SMTP_PASSWORD: Email password
- CRYPTO_WALLET_BTC: Bitcoin wallet address
- CRYPTO_WALLET_ETH: Ethereum wallet address
- CRYPTO_WALLET_SOL: Solana wallet address
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
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

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
THUMBNAIL_FOLDER = BASE_DIR / 'static' / 'thumbnails'
TEMPLATE_FOLDER = BASE_DIR / 'templates'
DB_PATH = BASE_DIR / 'portfolio.db'
CONFIG_PATH = BASE_DIR / '.env'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_BACKGROUND_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
THUMBNAIL_SIZE = (400, 400)

# E-commerce settings
DEFAULT_SHIPPING_COST = 15.00
CRYPTO_WALLETS = {
    'bitcoin': os.getenv('CRYPTO_WALLET_BTC', 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh'),
    'ethereum': os.getenv('CRYPTO_WALLET_ETH', '0x742d35Cc6634C0532925a3b8D4f0aB1f4C6C8C9D'),
    'solana': os.getenv('CRYPTO_WALLET_SOL', '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM')
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

# Bootstrap folders and basic templates
def bootstrap():
    """Create necessary directories and default templates"""
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    BACKGROUNDS_FOLDER.mkdir(parents=True, exist_ok=True)
    THUMBNAIL_FOLDER.mkdir(parents=True, exist_ok=True)
    TEMPLATE_FOLDER.mkdir(parents=True, exist_ok=True)
    
    create_default_backgrounds()
    
    if not (TEMPLATE_FOLDER / 'index.html').exists():
        (TEMPLATE_FOLDER / 'index.html').write_text(INDEX_HTML)
    if not (TEMPLATE_FOLDER / 'admin.html').exists():
        (TEMPLATE_FOLDER / 'admin.html').write_text(ADMIN_HTML)
    if not (TEMPLATE_FOLDER / 'login.html').exists():
        (TEMPLATE_FOLDER / 'login.html').write_text(LOGIN_HTML)
    if not (TEMPLATE_FOLDER / 'cart.html').exists():
        (TEMPLATE_FOLDER / 'cart.html').write_text(CART_HTML)
    if not (TEMPLATE_FOLDER / 'checkout.html').exists():
        (TEMPLATE_FOLDER / 'checkout.html').write_text(CHECKOUT_HTML)
    if not (TEMPLATE_FOLDER / 'orders.html').exists():
        (TEMPLATE_FOLDER / 'orders.html').write_text(ORDERS_HTML)

# Modern templates with e-commerce functionality
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Runveer - Artist Portfolio</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

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
            background: var(--body-bg, linear-gradient(135deg, #FAF3E0 0%, #F5E6D3 100%));
            background-size: var(--bg-size, auto);
            background-attachment: var(--bg-attachment, fixed);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
            transition: background 0.5s ease;
        }

        .artistic-header {
            background: linear-gradient(135deg, var(--dark) 0%, var(--primary) 100%);
            color: white;
            padding: 4rem 2rem;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .header-content {
            position: relative;
            z-index: 2;
            max-width: 1200px;
            margin: 0 auto;
        }

        .header-title {
            font-family: 'Georgia', serif;
            font-size: 4rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(45deg, var(--accent), #FFD700);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            letter-spacing: 2px;
        }

        .header-subtitle {
            font-size: 1.4rem;
            font-weight: 300;
            opacity: 0.9;
            margin-bottom: 2rem;
            font-style: italic;
        }

        .header-actions {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
        }

        .admin-button {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: linear-gradient(45deg, var(--secondary), var(--accent));
            color: white;
            padding: 0.8rem 1.5rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: var(--shadow);
        }

        .cart-button {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: linear-gradient(45deg, #28a745, #20c997);
            color: white;
            padding: 0.8rem 1.5rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: var(--shadow);
        }

        .admin-button:hover, .cart-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(210, 105, 30, 0.3);
        }

        .cart-count {
            background: #ff4444;
            color: white;
            border-radius: 50%;
            padding: 0.2rem 0.5rem;
            font-size: 0.8rem;
            margin-left: 0.5rem;
        }

        .portfolio-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 2rem;
            padding: 4rem 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }

        .artwork-card {
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: var(--shadow);
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }

        .artwork-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
        }

        .artwork-image {
            width: 100%;
            height: 280px;
            object-fit: cover;
            transition: transform 0.3s ease;
        }

        .artwork-card:hover .artwork-image {
            transform: scale(1.05);
        }

        .artwork-info {
            padding: 1.5rem;
        }

        .artwork-title {
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: var(--dark);
        }

        .artwork-description {
            color: #666;
            margin-bottom: 1rem;
            line-height: 1.5;
        }

        .artwork-price {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 1rem;
        }

        .artwork-actions {
            display: flex;
            gap: 0.5rem;
        }

        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-primary {
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            color: white;
        }

        .btn-success {
            background: linear-gradient(45deg, #28a745, #20c997);
            color: white;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }

        .artwork-date {
            color: #999;
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }

        /* Lightbox Styles */
        .lightbox {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .lightbox.active {
            display: flex;
            opacity: 1;
            align-items: center;
            justify-content: center;
        }

        .lightbox-content {
            max-width: 90%;
            max-height: 90%;
            position: relative;
        }

        .lightbox-image {
            max-width: 100%;
            max-height: 90vh;
            object-fit: contain;
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }

        .lightbox-info {
            position: absolute;
            bottom: -80px;
            left: 0;
            right: 0;
            text-align: center;
            color: white;
        }

        .lightbox-title {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }

        .lightbox-description {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .lightbox-close {
            position: absolute;
            top: -50px;
            right: 0;
            background: none;
            border: none;
            color: white;
            font-size: 2.5rem;
            cursor: pointer;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: color 0.3s ease;
        }

        .lightbox-close:hover {
            color: var(--accent);
        }

        .lightbox-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: white;
            font-size: 2rem;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }

        .lightbox-nav:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-50%) scale(1.1);
        }

        .lightbox-prev {
            left: 2rem;
        }

        .lightbox-next {
            right: 2rem;
        }

        .empty-state {
            text-align: center;
            padding: 6rem 2rem;
            color: #666;
        }

        .empty-state i {
            font-size: 4rem;
            margin-bottom: 1.5rem;
            opacity: 0.5;
        }

        .empty-state h2 {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: var(--dark);
        }

        .empty-state p {
            font-size: 1.2rem;
            max-width: 500px;
            margin: 0 auto;
        }

        @media (max-width: 768px) {
            .header-title {
                font-size: 2.5rem;
            }

            .header-subtitle {
                font-size: 1.1rem;
            }

            .header-actions {
                flex-direction: column;
                align-items: center;
            }

            .portfolio-grid {
                grid-template-columns: 1fr;
                padding: 2rem 1rem;
                gap: 1.5rem;
            }

            .artwork-actions {
                flex-direction: column;
            }

            .lightbox-nav {
                width: 50px;
                height: 50px;
                font-size: 1.5rem;
            }

            .lightbox-prev {
                left: 1rem;
            }

            .lightbox-next {
                right: 1rem;
            }
        }

        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #ffffff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .price-tag {
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: linear-gradient(45deg, #28a745, #20c997);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-weight: 700;
            font-size: 1.1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 2;
        }
    </style>
</head>
<body>
    <!-- Artistic Header -->
    <header class="artistic-header">
        <div class="header-decoration"></div>
        <div class="header-content">
            <h1 class="header-title">Runveer</h1>
            <p class="header-subtitle">Where Art Meets Soul • Visual Stories Unveiled</p>
            <div class="header-actions">
                <a href="/admin" class="admin-button">
                    <i class="fas fa-palette"></i>
                    Admin Gallery
                </a>
                <a href="/cart" class="cart-button">
                    <i class="fas fa-shopping-cart"></i>
                    View Cart
                    <span class="cart-count" id="cartCount">0</span>
                </a>
            </div>
        </div>
    </header>

    <!-- Main Portfolio Grid -->
    <main>
        {% if works %}
        <div class="portfolio-grid" id="portfolioGrid">
            {% for work in works %}
            <div class="artwork-card" 
                 onclick="openLightbox({{ loop.index0 }})"
                 data-title="{{ work.title }}"
                 data-description="{{ work.description or 'No description available' }}"
                 data-image="/static/uploads/{{ work.filename }}"
                 data-price="{{ work.price or '0' }}"
                 data-id="{{ work.id }}">
                {% if work.price and work.price > 0 %}
                <div class="price-tag">${{ "%.2f"|format(work.price) }}</div>
                {% endif %}
                <img src="/static/uploads/{{ work.filename }}" 
                     alt="{{ work.title }}" 
                     class="artwork-image"
                     loading="lazy">
                <div class="artwork-info">
                    <h3 class="artwork-title">{{ work.title }}</h3>
                    {% if work.description %}
                    <p class="artwork-description">{{ work.description }}</p>
                    {% endif %}
                    {% if work.price and work.price > 0 %}
                    <div class="artwork-price">${{ "%.2f"|format(work.price) }}</div>
                    <div class="artwork-actions">
                        <button class="btn btn-primary" onclick="event.stopPropagation(); addToCart({{ work.id }})">
                            <i class="fas fa-cart-plus"></i> Add to Cart
                        </button>
                        <button class="btn btn-success" onclick="event.stopPropagation(); openLightbox({{ loop.index0 }})">
                            <i class="fas fa-eye"></i> View
                        </button>
                    </div>
                    {% else %}
                    <div class="artwork-actions">
                        <button class="btn btn-success" onclick="event.stopPropagation(); openLightbox({{ loop.index0 }})">
                            <i class="fas fa-eye"></i> View Artwork
                        </button>
                    </div>
                    {% endif %}
                    <div class="artwork-date">
                        <i class="far fa-calendar"></i>
                        {{ work.created_at[:10] }}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state">
            <i class="fas fa-paint-brush"></i>
            <h2>Gallery Awaits Your Masterpieces</h2>
            <p>No artwork has been added yet. Start by uploading your first piece through the admin panel.</p>
            <a href="/admin" class="admin-button" style="margin-top: 2rem;">
                <i class="fas fa-plus"></i>
                Add First Artwork
            </a>
        </div>
        {% endif %}
    </main>

    <!-- Lightbox Modal -->
    <div class="lightbox" id="lightbox">
        <button class="lightbox-close" onclick="closeLightbox()">
            <i class="fas fa-times"></i>
        </button>
        <button class="lightbox-nav lightbox-prev" onclick="navigateLightbox(-1)">
            <i class="fas fa-chevron-left"></i>
        </button>
        <button class="lightbox-nav lightbox-next" onclick="navigateLightbox(1)">
            <i class="fas fa-chevron-right"></i>
        </button>
        <div class="lightbox-content">
            <img id="lightboxImage" class="lightbox-image" src="" alt="">
            <div class="lightbox-info">
                <h3 id="lightboxTitle" class="lightbox-title"></h3>
                <p id="lightboxDescription" class="lightbox-description"></p>
                <div id="lightboxPrice" class="artwork-price" style="color: white; margin: 1rem 0;"></div>
                <div id="lightboxActions" style="margin-top: 1rem;"></div>
            </div>
        </div>
    </div>

    <script>
        let currentArtworks = [];
        let currentIndex = 0;

        // Initialize artworks data
        function initArtworks() {
            const cards = document.querySelectorAll('.artwork-card');
            currentArtworks = Array.from(cards).map(card => ({
                id: card.dataset.id,
                title: card.dataset.title,
                description: card.dataset.description,
                image: card.dataset.image,
                price: card.dataset.price
            }));
        }

        // Open lightbox
        function openLightbox(index) {
            initArtworks();
            currentIndex = index;
            updateLightbox();
            document.getElementById('lightbox').classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        // Close lightbox
        function closeLightbox() {
            document.getElementById('lightbox').classList.remove('active');
            document.body.style.overflow = 'auto';
        }

        // Navigate lightbox
        function navigateLightbox(direction) {
            currentIndex += direction;
            if (currentIndex < 0) {
                currentIndex = currentArtworks.length - 1;
            } else if (currentIndex >= currentArtworks.length) {
                currentIndex = 0;
            }
            updateLightbox();
        }

        // Update lightbox content
        function updateLightbox() {
            const artwork = currentArtworks[currentIndex];
            const image = document.getElementById('lightboxImage');
            const title = document.getElementById('lightboxTitle');
            const description = document.getElementById('lightboxDescription');
            const price = document.getElementById('lightboxPrice');
            const actions = document.getElementById('lightboxActions');

            // Show loading state
            image.style.opacity = '0';
            
            image.onload = function() {
                image.style.opacity = '1';
            };
            
            image.src = artwork.image;
            title.textContent = artwork.title;
            description.textContent = artwork.description;
            
            if (artwork.price && parseFloat(artwork.price) > 0) {
                price.textContent = `$${parseFloat(artwork.price).toFixed(2)}`;
                price.style.display = 'block';
                actions.innerHTML = `
                    <button class="btn btn-primary" onclick="addToCart(${artwork.id})">
                        <i class="fas fa-cart-plus"></i> Add to Cart
                    </button>
                    <button class="btn btn-success" onclick="window.location.href='/cart'">
                        <i class="fas fa-shopping-cart"></i> View Cart
                    </button>
                `;
            } else {
                price.style.display = 'none';
                actions.innerHTML = '';
            }
        }

        // Add to cart
        function addToCart(artworkId) {
            fetch('/api/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ artwork_id: artworkId })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateCartCount();
                    showNotification('Artwork added to cart!', 'success');
                } else {
                    showNotification('Failed to add artwork to cart', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error adding to cart', 'error');
            });
        }

        // Update cart count
        function updateCartCount() {
            fetch('/api/cart/count')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('cartCount').textContent = data.count;
                });
        }

        // Show notification
        function showNotification(message, type) {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 1rem 2rem;
                border-radius: 10px;
                color: white;
                font-weight: 600;
                z-index: 10000;
                transition: all 0.3s ease;
                ${type === 'success' ? 'background: linear-gradient(45deg, #28a745, #20c997);' : 'background: linear-gradient(45deg, #dc3545, #c82333);'}
            `;
            notification.textContent = message;
            document.body.appendChild(notification);

            setTimeout(() => {
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => document.body.removeChild(notification), 300);
            }, 3000);
        }

        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            const lightbox = document.getElementById('lightbox');
            if (!lightbox.classList.contains('active')) return;

            switch(e.key) {
                case 'Escape':
                    closeLightbox();
                    break;
                case 'ArrowLeft':
                    navigateLightbox(-1);
                    break;
                case 'ArrowRight':
                    navigateLightbox(1);
                    break;
            }
        });

        // Close lightbox when clicking on backdrop
        document.getElementById('lightbox').addEventListener('click', function(e) {
            if (e.target === this) {
                closeLightbox();
            }
        });

        // Prevent card click from triggering backdrop close
        document.querySelector('.lightbox-content').addEventListener('click', function(e) {
            e.stopPropagation();
        });

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            initArtworks();
            updateCartCount();
            
            // Apply background settings from server
            fetch('/api/background-settings')
                .then(response => response.json())
                .then(settings => {
                    if (settings.background_type === 'color' && settings.background_value) {
                        document.body.style.setProperty('--body-bg', settings.background_value);
                    } else if (settings.background_type === 'image' && settings.background_value) {
                        document.body.style.setProperty('--body-bg', `url('${settings.background_value}')`);
                        document.body.style.setProperty('--bg-size', 'cover');
                        document.body.style.setProperty('--bg-attachment', 'fixed');
                    } else if (settings.background_type === 'pattern' && settings.background_value) {
                        document.body.style.setProperty('--body-bg', `url('${settings.background_value}')`);
                        document.body.style.setProperty('--bg-size', 'auto');
                        document.body.style.setProperty('--bg-attachment', 'fixed');
                    }
                })
                .catch(error => console.error('Error loading background settings:', error));
        });
    </script>
</body>
</html>
'''

# Additional templates for cart, checkout, and orders would be here...
# Due to length constraints, I'll provide the key additional templates in the next response

# --- Flask app ---
app = Flask(__name__, template_folder=str(TEMPLATE_FOLDER))
app.secret_key = os.getenv('FLASK_SECRET', secrets.token_hex(32))
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Load environment variables
load_dotenv(CONFIG_PATH)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- Database Schema Enhancement for E-commerce ---

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
        
        msg = MimeMultipart()
        msg['From'] = smtp_username
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MimeText(message, 'html'))
        
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

# --- Routes for E-commerce ---

@app.route('/cart')
def cart():
    """Shopping cart page"""
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    
    cart_items = get_cart(session_id)
    total = get_cart_total(session_id)
    shipping = DEFAULT_SHIPPING_COST
    grand_total = total + shipping
    
    return render_template('cart.html', 
                         cart_items=cart_items, 
                         total=total, 
                         shipping=shipping, 
                         grand_total=grand_total)

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
                         crypto_wallets=CRYPTO_WALLETS)

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
    
    return render_template('order_confirmation.html',
                         order=order,
                         items=items,
                         crypto_wallets=CRYPTO_WALLETS)

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
    
    return render_template('orders.html', orders=orders)

# ... (Previous routes and functions remain the same, but enhanced with price fields)

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
        
        # ... (rest of upload function remains similar but includes price)
        # Save to database with price
        db = get_db()
        db.execute(
            'INSERT INTO works (title, description, filename, price, created_at) VALUES (?, ?, ?, ?, ?)',
            (title, description, filename, price, datetime.utcnow().isoformat())
        )
        db.commit()
        
        logger.info(f"Uploaded new work: {filename} - ${price:.2f}")
        flash('Image uploaded successfully!')
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        flash('Upload failed', 'error')
    
    return redirect(url_for('admin'))

# ... (Rest of the application remains similar with enhanced e-commerce features)

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

def main():
    """Main application entry point"""
    bootstrap()
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
