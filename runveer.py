"""
Flask Artist Portfolio - Optimized for Render Deployment
File: app.py

Features:
- Single-file Flask app for easy deployment
- SQLite database with automatic admin creation
- Admin panel for image management
- Optional Telegram integration
- Modern lightbox image viewer
- Artistic "Runveer" header design
- Production-ready configuration

Environment Variables for Render:
- FLASK_SECRET: Random secret key
- ADMIN_USERNAME: Admin login username (optional)
- ADMIN_PASSWORD: Admin login password (optional)
- TELEGRAM_TOKEN: Bot token (optional)
- TELEGRAM_CHAT_ID: Telegram chat ID (optional)
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

# Modern templates with artistic header and lightbox
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
            background: linear-gradient(135deg, #FAF3E0 0%, #F5E6D3 100%);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
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

        .header-decoration {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 80%, rgba(244, 164, 96, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(139, 69, 19, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(210, 105, 30, 0.05) 0%, transparent 50%);
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

        .admin-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 40px rgba(210, 105, 30, 0.3);
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

        .artwork-date {
            color: #999;
            font-size: 0.9rem;
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

            .portfolio-grid {
                grid-template-columns: 1fr;
                padding: 2rem 1rem;
                gap: 1.5rem;
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
    </style>
</head>
<body>
    <!-- Artistic Header -->
    <header class="artistic-header">
        <div class="header-decoration"></div>
        <div class="header-content">
            <h1 class="header-title">Runveer</h1>
            <p class="header-subtitle">Where Art Meets Soul • Visual Stories Unveiled</p>
            <a href="/admin" class="admin-button">
                <i class="fas fa-palette"></i>
                Admin Gallery
            </a>
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
                 data-image="/static/uploads/{{ work.filename }}">
                <img src="/static/uploads/{{ work.filename }}" 
                     alt="{{ work.title }}" 
                     class="artwork-image"
                     loading="lazy">
                <div class="artwork-info">
                    <h3 class="artwork-title">{{ work.title }}</h3>
                    {% if work.description %}
                    <p class="artwork-description">{{ work.description }}</p>
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
                title: card.dataset.title,
                description: card.dataset.description,
                image: card.dataset.image
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

            // Show loading state
            image.style.opacity = '0';
            
            image.onload = function() {
                image.style.opacity = '1';
            };
            
            image.src = artwork.image;
            title.textContent = artwork.title;
            description.textContent = artwork.description;
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
        });
    </script>
</body>
</html>
'''

ADMIN_HTML = '''
<!doctype html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Admin - Runveer Portfolio</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .admin-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .admin-header {
            background: linear-gradient(135deg, #8B4513 0%, #D2691E 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }
        .admin-header h1 {
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
        }
        .admin-nav {
            background: #2C1810;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .admin-nav a {
            color: white;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            transition: background 0.3s;
        }
        .admin-nav a:hover {
            background: rgba(255,255,255,0.1);
        }
        .admin-content {
            padding: 2rem;
        }
        .alert {
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }
        .alert.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .upload-form {
            background: #f8f9fa;
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
        }
        .form-group {
            margin-bottom: 1rem;
        }
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #333;
        }
        .form-control {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }
        .form-control:focus {
            outline: none;
            border-color: #8B4513;
        }
        .btn {
            background: linear-gradient(135deg, #8B4513 0%, #D2691E 100%);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(139, 69, 19, 0.3);
        }
        .btn.delete {
            background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        }
        .artworks-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }
        .artwork-item {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .artwork-item:hover {
            transform: translateY(-5px);
        }
        .artwork-image {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        .artwork-details {
            padding: 1rem;
        }
        .artwork-title {
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #333;
        }
        .artwork-date {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }
        .artwork-actions {
            display: flex;
            gap: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="admin-container">
        <div class="admin-header">
            <h1><i class="fas fa-palette"></i> Runveer Admin</h1>
            <p>Manage Your Artistic Portfolio</p>
        </div>
        
        <div class="admin-nav">
            <div>
                <a href="/"><i class="fas fa-home"></i> View Portfolio</a>
            </div>
            <div>
                <a href="/logout"><i class="fas fa-sign-out-alt"></i> Logout</a>
            </div>
        </div>

        <div class="admin-content">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert {{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="upload-form">
                <h2><i class="fas fa-upload"></i> Upload New Artwork</h2>
                <form method="post" action="/admin/upload" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="title">Artwork Title</label>
                        <input type="text" class="form-control" id="title" name="title" placeholder="Enter artwork title" required>
                    </div>
                    <div class="form-group">
                        <label for="description">Description</label>
                        <textarea class="form-control" id="description" name="description" placeholder="Describe your artwork" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label for="file">Choose Image</label>
                        <input type="file" class="form-control" id="file" name="file" accept="image/*" required>
                    </div>
                    <button type="submit" class="btn"><i class="fas fa-cloud-upload-alt"></i> Upload Artwork</button>
                </form>
            </div>

            <div class="artworks-section">
                <h2><i class="fas fa-images"></i> Manage Artworks ({{ works|length }})</h2>
                {% if works %}
                <div class="artworks-grid">
                    {% for work in works %}
                    <div class="artwork-item">
                        <img src="/static/uploads/{{ work.filename }}" alt="{{ work.title }}" class="artwork-image">
                        <div class="artwork-details">
                            <div class="artwork-title">{{ work.title }}</div>
                            <div class="artwork-date">Added: {{ work.created_at[:16] }}</div>
                            <div class="artwork-actions">
                                <form method="post" action="/admin/delete" onsubmit="return confirm('Are you sure you want to delete this artwork?')" style="width: 100%;">
                                    <input type="hidden" name="id" value="{{ work.id }}">
                                    <button type="submit" class="btn delete" style="width: 100%;">
                                        <i class="fas fa-trash"></i> Delete
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div style="text-align: center; padding: 3rem; color: #666;">
                    <i class="fas fa-image" style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                    <h3>No Artworks Yet</h3>
                    <p>Start by uploading your first masterpiece above!</p>
                </div>
                {% endif %}
            </div>
        </div>
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
    <title>Login - Runveer Portfolio</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #8B4513 0%, #D2691E 50%, #F4A460 100%);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            padding: 3rem;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 400px;
            text-align: center;
        }
        .logo {
            font-size: 3rem;
            color: #8B4513;
            margin-bottom: 1rem;
        }
        h1 {
            color: #2C1810;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }
        .subtitle {
            color: #666;
            margin-bottom: 2rem;
        }
        .form-group {
            margin-bottom: 1.5rem;
            text-align: left;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            color: #333;
            font-weight: 600;
        }
        .form-control {
            width: 100%;
            padding: 1rem;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }
        .form-control:focus {
            outline: none;
            border-color: #8B4513;
        }
        .btn {
            background: linear-gradient(135deg, #8B4513 0%, #D2691E 100%);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            width: 100%;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(139, 69, 19, 0.3);
        }
        .alert {
            background: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            border: 1px solid #f5c6cb;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">
            <i class="fas fa-palette"></i>
        </div>
        <h1>Runveer</h1>
        <p class="subtitle">Artist Portfolio Admin</p>
        
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
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" class="form-control" id="username" name="username" placeholder="Enter your username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" class="form-control" id="password" name="password" placeholder="Enter your password" required>
            </div>
            <button type="submit" class="btn">
                <i class="fas fa-sign-in-alt"></i> Login
            </button>
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
    logger.info("Starting Flask app")
    
    # Get port from environment variable (for Render)
    port = int(os.environ.get('PORT', 5000))
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Cleanup
        if telegram_updater:
            telegram_updater.stop()

if __name__ == '__main__':
    main()
