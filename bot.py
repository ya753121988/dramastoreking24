import os
import telebot
import logging
import datetime
import threading
import time
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# --- Configuration ---
TOKEN = "8655043839:AAE_qIxO1QAORFsSJzpIMybe5a-wWVeDfL4" 
BOT_USERNAME = "dramastorkingsbot" 
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/DramaStoreDB?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "https://indirect-meris-yeasinvai-95120fc6.koyeb.app" 

# --- New added Security and API Info ---
API_ID = "29904834" 
API_HASH = "8b4fd9ef578af114502feeafa2d31938" 
OWNER_ID = 7120801813 # Your telegram ID here (Only you can add movies)

app = Flask(__name__)
app.secret_key = "ULTRA_FINAL_FULL_MEGA_CODE_VERSION_PRO"
app.config["MONGO_URI"] = MONGO_URI
app.permanent_session_lifetime = datetime.timedelta(days=30)

mongo = PyMongo(app)
bot = telebot.TeleBot(TOKEN, threaded=False)

# User state tracking
user_states = {}

# --- Delete function ---
def delete_msg(chat_id, message_id, delay):
    time.sleep(delay * 60)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

# --- 100% Guaranteed Notification Function ---
def send_manual_notification(movie_id):
    try:
        movie = mongo.db.movies.find_one({"_id": ObjectId(movie_id)})
        settings = mongo.db.settings.find_one({"type": "config"})
        if not movie or not settings:
            return False
        
        notif_ch = settings.get('notification_channel', '').strip()
        if not notif_ch:
            return False

        # Channel ID logic (Check if it's ID or Username)
        try:
            target_chat = int(notif_ch) if (notif_ch.startswith('-') or notif_ch.isdigit()) else notif_ch
        except:
            target_chat = notif_ch

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("👁 Watch Movie", url=f"{BASE_URL}/movie/{movie_id}"))
        
        msg = (
            f"drama name : {movie.get('title')} {movie.get('quality', 'HD')} {movie.get('category')} all part uplode done @{BOT_USERNAME}\n\n"
            f"drama link : {BASE_URL}/movie/{movie_id}\n\n"
            f"-------------------------------------------\n"
            f"join our community 🤝\n"
            f"-------------------------------------------\n"
            f"✅ main channel: {settings.get('notif_main', '')}\n"
            f"✅ official chat: {settings.get('notif_chat', '')}\n"
            f"✅ fb page: {settings.get('notif_fb', '')}\n\n"
            f"⭐ don't forget to share with friends! ⭐\n\n"
            f"{settings.get('notif_footer', '')}"
        )
        
        # 100% Delivery: Try sending photo using File ID (for speed), if fails send URL
        p_id = movie.get('poster_file_id') or movie.get('poster')
        try:
            bot.send_photo(target_chat, p_id, caption=msg, reply_markup=markup)
        except:
            bot.send_message(target_chat, msg, reply_markup=markup)
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False

# --- Detailed Premium CSS (Design Section Updated) ---
FULL_CSS = """
<style>
    :root { 
        --primary: #e50914; 
        --bg: #050505; 
        --card-bg: #121212; 
        --text: #ffffff; 
        --gray: #b3b3b3; 
        --gold: #ffd700;
        --transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
        background: var(--bg); 
        color: var(--text); 
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; 
        line-height: 1.6;
        padding-bottom: 100px;
        overflow-x: hidden;
    }
    
    #loader { 
        display: none; 
        position: fixed; 
        top: 0; left: 0; 
        width: 100%; height: 100%; 
        background: rgba(0,0,0,0.95); 
        z-index: 99999; 
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .spinner {
        width: 60px; height: 60px;
        border: 6px solid #222;
        border-top: 6px solid var(--primary);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

    .notice-bar { 
        background: var(--primary); 
        padding: 12px; 
        text-align: center; 
        font-weight: bold; 
        font-size: 14px; 
        position: sticky; top: 0; z-index: 1000;
        box-shadow: 0 2px 10px rgba(0,0,0,0.5);
    }

    .navbar { 
        display: flex; 
        justify-content: space-around; 
        background: rgba(0,0,0,0.9); 
        padding: 15px 0; 
        border-bottom: 1px solid #222;
        backdrop-filter: blur(10px);
    }
    .navbar a { 
        color: var(--gray); 
        text-decoration: none; 
        font-size: 14px; 
        display: flex; flex-direction: column; align-items: center; gap: 5px;
        transition: var(--transition);
    }
    .navbar a i { font-size: 18px; }
    .navbar a:hover, .navbar a.active { color: var(--primary); }

    .user-stats-bar {
        background: #1a1a1a;
        padding: 10px 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
        border-bottom: 1px solid #333;
        font-size: 14px;
        gap: 5px;
    }

    .feature-menus {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        margin: 15px 0;
    }
    .menu-btn {
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        text-decoration: none;
        font-weight: bold;
        color: white;
        display: flex;
        flex-direction: column; gap: 5px;
        transition: var(--transition);
    }
    .btn-premium { background: linear-gradient(45deg, #FFD700, #FFA500); color: #000; }
    .btn-task { background: linear-gradient(45deg, #00c6ff, #0072ff); }
    .menu-btn:hover { transform: scale(1.03); }

    .search-container {
        padding: 15px 20px;
        max-width: 1200px;
        margin: auto;
    }
    .search-form {
        display: flex;
        gap: 10px;
    }
    .search-form input {
        margin: 0;
        flex-grow: 1;
    }
    .search-form .btn {
        width: auto;
        padding: 0 25px;
    }

    .container { padding: 20px; max-width: 1200px; margin: auto; }

    .section-title { 
        font-size: 22px; 
        font-weight: 800; 
        margin: 30px 0 15px; 
        border-left: 5px solid var(--primary); 
        padding-left: 15px;
        display: flex; justify-content: space-between; align-items: center;
    }

    /* --- Slider Section Update --- */
    .slider { 
        display: flex; 
        overflow-x: auto; 
        gap: 20px; 
        padding: 10px 0 20px; 
        scrollbar-width: none;
        scroll-behavior: smooth;
    }
    .slider::-webkit-scrollbar { display: none; }
    .slider-item { 
        min-width: 280px; 
        border-radius: 12px; 
        position: relative; 
        overflow: hidden; 
        background: #1a1a1a; 
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        flex-shrink: 0;
    }
    .slider-img-box { position: relative; width: 100%; height: 160px; overflow: hidden; }
    .slider-img-box img { width: 100%; height: 100%; object-fit: cover; transition: var(--transition); }
    .slider-item:hover img { transform: scale(1.05); }
    
    .badge-view-red { 
        position: absolute; top: 10px; left: 10px; 
        background: var(--primary); color: white; 
        padding: 3px 10px; font-size: 11px; border-radius: 5px; 
        font-weight: bold; z-index: 10;
    }

    .slider-info { 
        padding: 12px;
        font-weight: bold; font-size: 15px;
        text-align: center; color: white;
        background: #111;
    }

    /* --- Recent Upload Landscape Section --- */
    .movie-grid { 
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); 
        gap: 20px; 
    }
    .movie-card { 
        background: var(--card-bg); 
        border-radius: 12px; 
        overflow: hidden; 
        position: relative; 
        border: 1px solid #222; 
        transition: var(--transition);
        cursor: pointer;
    }
    .movie-card:hover { transform: translateY(-5px); border-color: var(--primary); }
    
    .movie-card .img-container { width: 100%; aspect-ratio: 16/9; overflow: hidden; position: relative; }
    .movie-card img { width: 100%; height: 100%; object-fit: cover; }
    
    .badge-top-left { position: absolute; top: 10px; left: 10px; background: var(--primary); padding: 4px 10px; font-size: 11px; border-radius: 5px; font-weight: bold; z-index: 10; }
    .badge-bottom-right { position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.8); padding: 4px 10px; font-size: 11px; border-radius: 5px; display: flex; align-items: center; gap: 5px; }
    
    .movie-info-box { padding: 12px; text-align: left; background: #121212; }
    .movie-info-box h4 { font-size: 15px; font-weight: 600; color: #fff; line-height: 1.4; white-space: normal; overflow: visible; }

    .pagination { display: flex; justify-content: center; align-items: center; gap: 15px; margin: 50px 0; }
    .pagination a { 
        padding: 12px 25px; 
        background: #1a1a1a; 
        border-radius: 8px; 
        color: #fff; 
        text-decoration: none; 
        border: 1px solid #333;
        transition: var(--transition);
        font-weight: bold;
    }
    .pagination a:hover { background: var(--primary); border-color: var(--primary); }
    .page-info { color: var(--gray); font-size: 14px; }

    .card { background: var(--card-bg); padding: 30px; border-radius: 15px; max-width: 500px; margin: 40px auto; border: 1px solid #222; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .card h3 { text-align: center; margin-bottom: 25px; color: var(--primary); font-size: 24px; }
    input, select { 
        width: 100%; padding: 15px; margin: 15px 0; 
        background: #1a1a1a; border: 1px solid #333; 
        color: #fff; border-radius: 10px; outline: none;
    }
    input:focus { border-color: var(--primary); }
    .btn { 
        width: 100%; padding: 15px; 
        background: var(--primary); color: #fff; 
        border: none; border-radius: 10px; 
        cursor: pointer; font-weight: bold; font-size: 16px; 
        text-decoration: none; display: block; text-align: center;
        transition: var(--transition);
    }
    .btn:hover { background: #b20710; transform: scale(1.02); }
    
    .back-btn-container { margin-bottom: 20px; }
    .back-btn { 
        display: inline-flex; align-items: center; gap: 8px; 
        color: var(--gray); text-decoration: none; font-size: 15px; 
        transition: var(--transition);
    }
    .back-btn:hover { color: #fff; transform: translateX(-5px); }

    .episode-list { margin-top: 30px; }
    .ep-button { 
        background: linear-gradient(45deg, #1a1a1a, #222); 
        border: 1px solid #333; 
        padding: 20px; 
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 15px; border-radius: 12px; 
        border-left: 6px solid var(--primary); 
        color: #fff; text-decoration: none; font-weight: bold;
        transition: var(--transition);
        cursor: pointer;
    }
    .ep-button:hover { background: #282828; transform: scale(1.02); box-shadow: 0 5px 15px rgba(229, 9, 20, 0.2); }
    .ep-status { font-size: 12px; font-weight: normal; color: var(--gray); margin-top: 5px; display: block; }
    
    .task-card {
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .task-info h4 { font-size: 16px; margin-bottom: 5px; }
    .task-info p { color: var(--gold); font-size: 13px; font-weight: bold; }
    .task-btn {
        background: var(--primary);
        color: white;
        padding: 8px 15px;
        border-radius: 8px;
        text-decoration: none;
        font-size: 14px;
        font-weight: bold;
        border: none;
        cursor: pointer;
    }
    .task-btn.link { background: #28a745; }

    #task-timer-modal {
        display: none;
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.9);
        z-index: 10000;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }

    .manage-item {
        display: flex; justify-content: space-between; align-items: center;
        background: #1a1a1a; padding: 10px 15px; border-radius: 8px; margin-bottom: 10px;
        border: 1px solid #333;
    }
    .del-btn { background: #ff4d4d; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; }
    .notif-btn { background: #007bff; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; margin-right: 5px; }

    @media (max-width: 600px) {
        .movie-grid { grid-template-columns: 1fr; gap: 15px; }
        .slider-item { min-width: 250px; }
    }
</style>
<script>
    function showLoader() { 
        document.getElementById('loader').style.display = 'flex'; 
    }
    window.addEventListener('pageshow', function(event) {
        document.getElementById('loader').style.display = 'none';
    });

    // --- Auto slider logic ---
    document.addEventListener("DOMContentLoaded", function() {
        const slider = document.querySelector('.slider');
        if (slider) {
            let step = 280;
            setInterval(() => {
                if (slider.scrollLeft + slider.clientWidth >= slider.scrollWidth) {
                    slider.scrollLeft = 0;
                } else {
                    slider.scrollLeft += step;
                }
            }, 3000); 
        }
    });

    function startPremiumTimer(expiryTimestamp, elementId) {
        function update() {
            const now = new Date().getTime();
            const diff = expiryTimestamp - now;
            const el = document.getElementById(elementId);
            if(!el) return;

            if (diff <= 0) {
                el.innerHTML = "Expired";
                return;
            }

            const years = Math.floor(diff / (1000 * 60 * 60 * 24 * 365));
            const months = Math.floor((diff % (1000 * 60 * 60 * 24 * 365)) / (1000 * 60 * 60 * 24 * 30));
            const weeks = Math.floor((diff % (1000 * 60 * 60 * 24 * 30)) / (1000 * 60 * 60 * 24 * 7));
            const days = Math.floor((diff % (1000 * 60 * 60 * 24 * 7)) / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);

            let timeStr = "";
            if (years > 0) timeStr += years + " Years ";
            if (months > 0) timeStr += months + " Months ";
            if (weeks > 0) timeStr += weeks + " Weeks ";
            if (days > 0) timeStr += days + " Days ";
            timeStr += hours + " Hours " + minutes + " Mins " + seconds + " Secs";

            el.innerHTML = timeStr;
        }
        setInterval(update, 1000);
        update();
    }
</script>
"""

# --- Database and settings helpers ---
def get_site_settings():
    try:
        s = mongo.db.settings.find_one({"type": "config"})
        if not s:
            default = {
                "site_name": "PremiumMovie", "notice": "Welcome!", 
                "monetag_id": "10351894", "ad_limit": 2, 
                "lock_duration": 30, "file_channel": "",
                "auto_delete_time": 5, "protect_content": "No",
                "notification_channel": "",
                "notif_main": "t.me/drama4uofficial",
                "notif_chat": "t.me/drama2hchat",
                "notif_fb": "facebook.com/bddranaworld",
                "notif_footer": "#drama2h @drama2h #movies"
            }
            mongo.db.settings.insert_one({"type": "config", **default})
            return default
        return s
    except Exception as e:
        return {"site_name": "PremiumMovie", "notice": "Error!", "monetag_id": "10351894", "ad_limit": 2, "lock_duration": 30, "file_channel": "", "auto_delete_time": 5, "protect_content": "No", "notification_channel": ""}

# --- Master template maker ---
def render_full_page(body_html, **kwargs):
    settings = get_site_settings()
    kwargs.pop('settings', None)
    kwargs.pop('expiry_ts', None)
    
    user_data = None
    expiry_ts = 0
    if 'user_id' in session:
        try:
            user_data = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
            if user_data and user_data.get('premium_until'):
                expiry_ts = int(user_data['premium_until'].timestamp() * 1000)
        except:
            pass
    
    template_start = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{{ settings.site_name }}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="preconnect" href="//libtl.com">
        <link rel="dns-prefetch" href="//libtl.com">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        """ + FULL_CSS + """
    </head>
    <body>
        <div id="loader"><div class="spinner"></div><p style="margin-top:20px; color:var(--primary); font-weight:bold;">Loading...</p></div>
        
        <div class="notice-bar">{{ settings.notice }}</div>
        
        <div class="navbar">
            <a href="/" class="{% if request.path == '/' %}active{% endif %}"><i class="fas fa-home"></i> Home</a>
            <a href="/profile" class="{% if request.path == '/profile' %}active{% endif %}"><i class="fas fa-user"></i> Profile</a>
            {% if session.get('role') == 'admin' %}
            <a href="/admin" class="{% if request.path == '/admin' %}active{% endif %}"><i class="fas fa-user-shield"></i> Admin</a>
            {% endif %}
        </div>

        {% if user_data %}
        <div class="user-stats-bar">
            <div style="display:flex; justify-content:space-between; width:100%;">
                <span><i class="fas fa-wallet" style="color:gold;"></i> Balance: <b>{{ user_data.get('coins', 0) }}</b> Coins</span>
                {% if user_data.get('premium_until') and user_data.get('premium_until') > now %}
                <span style="color:gold; font-weight:bold;"><i class="fas fa-crown"></i> Premium</span>
                {% else %}
                <span style="color:var(--gray);">Free User</span>
                {% endif %}
            </div>
            {% if user_data.get('premium_until') and user_data.get('premium_until') > now %}
            <div style="font-size:11px; color:#00ff00; width:100%; text-align:center;">
                Remaining: <span id="nav-premium-timer"></span>
                <script>startPremiumTimer({{ expiry_ts }}, 'nav-premium-timer');</script>
            </div>
            {% endif %}
        </div>
        {% endif %}

        <div class="search-container">
            <form action="/search" method="GET" class="search-form">
                <input type="text" name="q" placeholder="Search movies or dramas..." value="{{ request.args.get('q', '') }}" required>
                <button type="submit" class="btn"><i class="fas fa-search"></i></button>
            </form>
        </div>

        <div class="container">
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for m in messages %}
                        <div style="background:var(--primary); padding:15px; text-align:center; border-radius:10px; margin-bottom:20px; font-weight:bold;">{{ m }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            """
            
    template_end = """
        </div>
    </body>
    </html>
    """
    
    full_template = template_start + body_html + template_end
    return render_template_string(full_template, settings=settings, session=session, user_data=user_data, expiry_ts=expiry_ts, now=datetime.datetime.now(), **kwargs)

# --- Site logic routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST': return "OK", 200 
    if 'user_id' not in session: return redirect(url_for('login'))
    
    page = int(request.args.get('page', 1))
    per_page = 20 if page == 1 else 50
    skip = 0 if page == 1 else 20 + (page - 2) * 50
    
    sliders = list(mongo.db.movies.find().sort("views", -1).limit(20))
    movies = list(mongo.db.movies.find().sort("_id", -1).skip(skip).limit(per_page))

    content = """
    <div class="feature-menus">
        <a href="/buy-premium" class="menu-btn btn-premium">
            <i class="fas fa-crown fa-lg"></i>
            <span>Buy Premium</span>
        </a>
        <a href="/tasks" class="menu-btn btn-task">
            <i class="fas fa-tasks fa-lg"></i>
            <span>Earn Coins</span>
        </a>
    </div>

    <div class="section-title">Top Trending (Views) <i class="fas fa-fire" style="color:orange;"></i></div>
    <div class="slider">
        {% for s in sliders %}
        <div class="slider-item" onclick="showLoader(); location.href='/movie/{{s._id}}'">
            <div class="slider-img-box">
                <div class="badge-view-red"><i class="fas fa-eye"></i> {{s.views}} Views</div>
                <img src="{{s.poster}}">
            </div>
            <div class="slider-info">{{s.title}}</div>
        </div>
        {% endfor %}
    </div>

    <div class="section-title">Recently Uploaded <i class="fas fa-clock"></i></div>
    <div class="movie-grid">
        {% for m in movies %}
        <div class="movie-card" onclick="showLoader(); location.href='/movie/{{m._id}}'">
            <div class="img-container">
                <div class="badge-top-left">{{m.category}}</div>
                <div class="badge-bottom-right"><i class="fas fa-eye"></i> {{m.views}}</div>
                <img src="{{m.poster}}">
            </div>
            <div class="movie-info-box">
                <h4>{{m.title}}</h4>
            </div>
        </div>
        {% endfor %}
    </div>

    <div class="pagination">
        {% if page > 1 %}
            <a href="/?page={{page-1}}" onclick="showLoader()"><i class="fas fa-chevron-left"></i> Previous</a>
        {% endif %}
        <span class="page-info">Page Number: {{page}}</span>
        <a href="/?page={{page+1}}" onclick="showLoader()">Next Page <i class="fas fa-chevron-right"></i></a>
    </div>
    """
    return render_full_page(content, sliders=sliders, movies=movies, page=page)

# --- Task and premium logic ---

@app.route('/tasks')
def tasks():
    if 'user_id' not in session: return redirect('/login')
    tasks_list = list(mongo.db.tasks.find())
    
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    daily_stats = user.get('daily_stats', {"date": today, "counts": {}})
    
    if daily_stats.get('date') != today:
        daily_stats = {"date": today, "counts": {}}
        mongo.db.users.update_one({"_id": user['_id']}, {"$set": {"daily_stats": daily_stats}})

    content = """
    <!-- Monetag Optimization (FAST LOAD) -->
    <script async src='//libtl.com/sdk.js' data-zone='{{ settings.monetag_id }}' data-sdk='show_{{ settings.monetag_id }}'></script>

    <div class="section-title">Earn Coins <i class="fas fa-coins" style="color:gold;"></i></div>
    {% for t in tasks_list %}
    <div class="task-card">
        <div class="task-info">
            <h4>{{ t.title }}</h4>
            <p>+{{ t.reward }} Coins | Limit: {{ daily_stats.counts.get(t._id|string, 0) }}/{{ t.get('daily_limit', 1) }}</p>
        </div>
        {% if daily_stats.counts.get(t._id|string, 0)|int >= t.get('daily_limit', 1)|int %}
            <span style="color:var(--gray); font-weight:bold;">Limit Reached</span>
        {% else %}
            <button onclick="handleTask('{{ t._id }}', '{{ t.type }}', {{ t.get('timer', 5) }})" class="task-btn">Start</button>
        {% endif %}
    </div>
    {% endfor %}

    <div id="task-timer-modal">
        <h2 style="color:var(--primary);">Wait...</h2>
        <div id="timer-countdown" style="font-size:50px; font-weight:bold; margin:20px 0;">0</div>
        <p id="timer-subtext">Coins will be added when the task finishes.</p>
        <button id="claim-reward-btn" class="btn" style="display:none; max-width:200px;" onclick="claimReward()">Claim Coins</button>
    </div>

    <script>
        let currentTaskId = "";

        function handleTask(taskId, type, timerSec) {
            currentTaskId = taskId;
            
            // Fast Ad Trigger Logic
            if(type === 'monetag') {
                if (typeof window['show_{{ settings.monetag_id }}'] === 'function') {
                    window['show_{{ settings.monetag_id }}']();
                }
            }

            fetch('/get-task-data/' + taskId)
            .then(res => res.json())
            .then(data => {
                if(type === 'link') {
                    window.open(data.content, '_blank');
                } else if(type === 'monetag' && !window['show_{{ settings.monetag_id }}']) {
                    // Fallback for monetag if not triggered above
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = data.content;
                    const scripts = tempDiv.getElementsByTagName('script');
                    for (let i = 0; i < scripts.length; i++) {
                        const newScript = document.createElement('script');
                        Array.from(scripts[i].attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
                        document.body.appendChild(newScript);
                        
                        const sdkFunc = scripts[i].getAttribute('data-sdk');
                        if (sdkFunc) {
                            setTimeout(() => {
                                if (typeof window[sdkFunc] === 'function') {
                                    window[sdkFunc]();
                                }
                            }, 500);
                        }
                    }
                }
            });

            document.getElementById('task-timer-modal').style.display = 'flex';
            let timeLeft = timerSec;
            document.getElementById('timer-countdown').innerText = timeLeft;
            document.getElementById('claim-reward-btn').style.display = 'none';

            let timer = setInterval(() => {
                timeLeft--;
                document.getElementById('timer-countdown').innerText = timeLeft;
                if(timeLeft <= 0) {
                    clearInterval(timer);
                    document.getElementById('timer-countdown').innerText = "Done!";
                    document.getElementById('claim-reward-btn').style.display = 'block';
                }
            }, 1000);
        }

        function claimReward() {
            showLoader();
            fetch('/claim-task-new/' + currentTaskId, {method: 'POST'})
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    alert('Congratulations! ' + data.reward + ' coins added.');
                    location.reload();
                } else {
                    alert(data.error || 'Something went wrong!');
                    location.reload();
                }
            });
        }
    </script>
    """
    return render_full_page(content, tasks_list=tasks_list, daily_stats=daily_stats)

@app.route('/get-task-data/<tid>')
def get_task_data(tid):
    t = mongo.db.tasks.find_one({"_id": ObjectId(tid)})
    return jsonify({"content": t['content'] if t else ""})

@app.route('/claim-task-new/<tid>', methods=['POST'])
def claim_task_new(tid):
    if 'user_id' not in session: return jsonify({"success": False})
    
    t = mongo.db.tasks.find_one({"_id": ObjectId(tid)})
    if not t: return jsonify({"success": False, "error": "Task not found!"})
    
    uid = ObjectId(session['user_id'])
    user = mongo.db.users.find_one({"_id": uid})
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    daily_stats = user.get('daily_stats', {"date": today, "counts": {}})
    
    current_count = daily_stats.get('counts', {}).get(str(tid), 0)
    if int(current_count) >= int(t.get('daily_limit', 1)):
        return jsonify({"success": False, "error": "Today's limit reached!"})
    
    mongo.db.users.update_one({"_id": uid}, {
        "$inc": {"coins": int(t.get('reward', 10)), f"daily_stats.counts.{tid}": 1},
        "$set": {"daily_stats.date": today}
    })
    
    return jsonify({"success": True, "reward": t.get('reward', 10)})

@app.route('/buy-premium')
def buy_premium():
    if 'user_id' not in session: return redirect('/login')
    offers = list(mongo.db.offers.find())
    content = """
    <div class="section-title">Premium Packages <i class="fas fa-crown" style="color:gold;"></i></div>
    <p style="margin-bottom:20px; color:var(--gray);">Buy premium to watch movies without any ads.</p>
    {% for o in offers %}
    <div class="task-card">
        <div class="task-info">
            <h4>{{ o.days }} Days Premium</h4>
            <p>{{ o.price }} Coins</p>
        </div>
        <a href="/purchase-premium/{{ o._id }}" class="task-btn" style="background:gold; color:black;" onclick="return confirm('Are you sure?')">Buy</a>
    </div>
    {% endfor %}
    """
    return render_full_page(content, offers=offers)

@app.route('/purchase-premium/<oid>')
def purchase_premium(oid):
    if 'user_id' not in session: return redirect('/login')
    offer = mongo.db.offers.find_one({"_id": ObjectId(oid)})
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    
    if user.get('coins', 0) >= offer['price']:
        days = int(offer['days'])
        now = datetime.datetime.now()
        
        current_expiry = user.get('premium_until')
        if current_expiry and current_expiry > now:
            new_expiry = current_expiry + datetime.timedelta(days=days)
        else:
            new_expiry = now + datetime.timedelta(days=days)
            
        mongo.db.users.update_one({"_id": ObjectId(session['user_id'])}, {
            "$inc": {"coins": -offer['price']},
            "$set": {"premium_until": new_expiry}
        })
        flash(f"Successfully purchased {days} days premium!")
    else:
        flash("You don't have enough coins!")
    return redirect('/profile')

@app.route('/search')
def search():
    if 'user_id' not in session: return redirect(url_for('login'))
    query = request.args.get('q', '')
    results = list(mongo.db.movies.find({"title": {"$regex": query, "$options": "i"}}).sort("_id", -1))
    
    content = """
    <div class="section-title">Search Results: "{{ query }}"</div>
    <div class="movie-grid">
        {% for m in results %}
        <div class="movie-card" onclick="showLoader(); location.href='/movie/{{m._id}}'">
            <div class="img-container">
                <div class="badge-top-left">{{m.category}}</div>
                <div class="badge-bottom-right"><i class="fas fa-eye"></i> {{m.views}}</div>
                <img src="{{m.poster}}">
            </div>
            <div class="movie-info-box">
                <h4>{{m.title}}</h4>
            </div>
        </div>
        {% else %}
        <p style="text-align:center; grid-column: 1/-1; padding: 50px; color: var(--gray);">Sorry, the movie you searched for was not found.</p>
        {% endfor %}
    </div>
    """
    return render_full_page(content, results=results, query=query)

@app.route('/movie/<m_id>')
def movie_detail(m_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    movie = mongo.db.movies.find_one_and_update(
        {"_id": ObjectId(m_id)}, 
        {"$inc": {"views": 1}}, 
        return_document=True
    )
    if not movie: return redirect('/')
    
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    is_premium = user.get('premium_until') and user['premium_until'] > datetime.datetime.now()

    content = """
    <div class="back-btn-container">
        <a href="/" onclick="showLoader();" class="back-btn"><i class="fas fa-arrow-left"></i> Back to Home</a>
    </div>
    
    <div style="text-align:center;">
        <img src="{{ movie.poster }}" style="width:100%; max-width:400px; border-radius:20px; border:3px solid #222; box-shadow: 0 15px 40px rgba(0,0,0,0.7);">
        <h2 style="margin:25px 0 10px; font-size:28px;">{{ movie.title }}</h2>
        <div style="margin-bottom:30px;">
            <span style="background:#222; padding:5px 15px; border-radius:20px; font-size:14px; margin:0 5px;">{{ movie.category }}</span>
            <span style="background:#222; padding:5px 15px; border-radius:20px; font-size:14px; margin:0 5px;"><i class="fas fa-eye"></i> {{ movie.views }} Views</span>
        </div>
        
        <div class="card" style="max-width:100%; text-align:left; border-top:4px solid var(--primary);">
            <h4 style="margin-bottom:20px; border-bottom:1px solid #333; padding-bottom:10px;">Download and Watch Links:</h4>
            <div class="episode-list">
                {% for msg_id in movie.episodes %}
                <div class="ep-button" onclick="processAd('{{ msg_id }}_idx_{{ loop.index0 }}', '{{ msg_id }}')">
                    <div>
                        🎬 Episode {{ "%02d" % (loop.index0 + 1) }}
                        <span class="ep-status" id="status_{{ msg_id }}_idx_{{ loop.index0 }}">Loading...</span>
                    </div>
                    <i class="fas fa-download"></i>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <!-- Monetag Optimization: Fast Loading Scripts -->
    <script async src='//libtl.com/sdk.js' data-zone='{{ settings.monetag_id }}' data-sdk='show_{{ settings.monetag_id }}'></script>
    
    <script>
        const AD_LIMIT = {{ settings.ad_limit }};
        const LOCK_MINUTES = {{ settings.lock_duration }};
        const IS_PREMIUM = {{ 'true' if is_premium else 'false' }};
        const BOT_NAME = '""" + BOT_USERNAME + """';

        function updateStatus(uniqueId) {
            if(IS_PREMIUM) {
                document.getElementById('status_' + uniqueId).innerHTML = "🔓 Premium Unlocked (No Ads)";
                document.getElementById('status_' + uniqueId).style.color = "gold";
                return;
            }
            let data = JSON.parse(localStorage.getItem('ad_data_' + uniqueId) || '{"count":0, "unlocked_at":0}');
            let statusEl = document.getElementById('status_' + uniqueId);
            let now = new Date().getTime();
            
            if (data.unlocked_at > 0) {
                let elapsed = (now - data.unlocked_at) / (1000 * 60);
                if (elapsed >= LOCK_MINUTES) {
                    data.count = 0;
                    data.unlocked_at = 0;
                    localStorage.setItem('ad_data_' + uniqueId, JSON.stringify(data));
                }
            }

            if (data.unlocked_at > 0) {
                let remain = Math.ceil(LOCK_MINUTES - (now - data.unlocked_at) / (1000 * 60));
                statusEl.innerHTML = "🔓 Unlocked (" + remain + " mins remaining)";
                statusEl.style.color = "#00ff00";
            } else {
                statusEl.innerHTML = "🔒 Ads viewed: " + data.count + "/" + AD_LIMIT;
                statusEl.style.color = "#b3b3b3";
            }
        }

        document.querySelectorAll('[id^="status_"]').forEach(el => {
            updateStatus(el.id.replace('status_', ''));
        });

        function processAd(uniqueId, fileId) {
            if(IS_PREMIUM) {
                showLoader();
                window.location.href = "https://t.me/" + BOT_NAME + "?start=file_" + fileId;
                return;
            }

            let data = JSON.parse(localStorage.getItem('ad_data_' + uniqueId) || '{"count":0, "unlocked_at":0}');
            let now = new Date().getTime();

            if (data.unlocked_at > 0) {
                showLoader();
                window.location.href = "https://t.me/" + BOT_NAME + "?start=file_" + fileId;
                return;
            }

            if (data.count < AD_LIMIT) {
                if (typeof window['show_' + {{ settings.monetag_id }}] === 'function') {
                    window['show_' + {{ settings.monetag_id }}]();
                }
                data.count++;
                localStorage.setItem('ad_data_' + uniqueId, JSON.stringify(data));
                updateStatus(uniqueId);
            } else {
                data.unlocked_at = now;
                localStorage.setItem('ad_data_' + uniqueId, JSON.stringify(data));
                updateStatus(uniqueId);
                showLoader();
                window.location.href = "https://t.me/" + BOT_NAME + "?start=file_" + fileId;
            }
        }
    </script>
    """
    return render_full_page(content, movie=movie, is_premium=is_premium)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin': 
        flash("You do not have admin access!")
        return redirect('/')
    
    settings = get_site_settings()
    admin_user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    search_q = request.args.get('search_movie', '')
    manage_movies = list(mongo.db.movies.find({"title": {"$regex": search_q, "$options": "i"}}).sort("_id", -1).limit(50))
    current_tasks = list(mongo.db.tasks.find())
    current_offers = list(mongo.db.offers.find())

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'site':
            mongo.db.settings.update_one({"type": "config"}, {"$set": {
                "site_name": request.form.get('site_name'),
                "notice": request.form.get('notice')
            }}, upsert=True)
            flash("Site settings updated!")
        elif action == 'update_admin':
            new_num = request.form.get('admin_number')
            new_pw = request.form.get('admin_password')
            up_data = {"number": new_num}
            if new_pw:
                up_data["password"] = generate_password_hash(new_pw)
            mongo.db.users.update_one({"_id": admin_user['_id']}, {"$set": up_data})
            flash("Admin ID and Password updated successfully!")
        elif action == 'add_task':
            mongo.db.tasks.insert_one({
                "title": request.form.get('title'),
                "type": request.form.get('type'),
                "content": request.form.get('content'),
                "reward": int(request.form.get('reward', 10)),
                "timer": int(request.form.get('timer', 10)),
                "daily_limit": int(request.form.get('daily_limit', 1))
            })
            flash("Task added!")
        elif action == 'add_offer':
            mongo.db.offers.insert_one({
                "days": request.form.get('days'),
                "price": int(request.form.get('price'))
            })
            flash("Offer added!")
        elif action == 'del_task':
            mongo.db.tasks.delete_one({"_id": ObjectId(request.form.get('tid'))})
        elif action == 'del_offer':
            mongo.db.offers.delete_one({"_id": ObjectId(request.form.get('oid'))})
        elif action == 'ad':
            mongo.db.settings.update_one({"type": "config"}, {"$set": {
                "monetag_id": request.form.get('monetag_id'),
                "ad_limit": int(request.form.get('ad_limit')),
                "lock_duration": int(request.form.get('lock_duration')),
                "file_channel": request.form.get('file_channel'),
                "auto_delete_time": int(request.form.get('auto_delete_time', 5)),
                "protect_content": request.form.get('protect_content')
            }}, upsert=True)
            flash("Ad and storage settings updated!")
        # --- NEW NOTIFICATION LINKS SAVE LOGIC ---
        elif action == 'update_notif_links':
            mongo.db.settings.update_one({"type": "config"}, {"$set": {
                "notification_channel": request.form.get('notification_channel'),
                "notif_main": request.form.get('notif_main'),
                "notif_chat": request.form.get('notif_chat'),
                "notif_fb": request.form.get('notif_fb'),
                "notif_footer": request.form.get('notif_footer')
            }}, upsert=True)
            flash("Notification Section updated!")
        elif action == 'delete_movie':
            mid = request.form.get('movie_id')
            mongo.db.movies.delete_one({"_id": ObjectId(mid)})
            flash("Movie has been deleted!")
        elif action == 'push_notification':
            mid = request.form.get('movie_id')
            if send_manual_notification(mid):
                flash("Notification sent successfully!")
            else:
                flash("Failed to send notification! Check Channel ID.")
            
        return redirect('/admin')

    content = """
    <div style="text-align:right; margin-bottom:20px;">
        <a href="/logout" class="btn" style="background:#333; display:inline-block; width:auto; padding:10px 20px;">Logout (Admin)</a>
    </div>

    <div class="card" style="border-top:4px solid #00c6ff;">
        <h3><i class="fas fa-user-lock"></i> Admin Credentials</h3>
        <p style="color:var(--gray); font-size:12px; margin-bottom:10px;">Change login mobile number and password.</p>
        <form method="POST">
            <input type="hidden" name="action" value="update_admin">
            Mobile Number: <input name="admin_number" value="{{ admin_user.number }}" required>
            New Password (Leave blank for no change): <input type="password" name="admin_password" placeholder="New Password">
            <button class="btn" type="submit" style="background:#00c6ff;">Update Credentials</button>
        </form>
    </div>

    <!-- --- NOTIFICATION SECTION (TELEGRAM CHANNEL ID ADDED) --- -->
    <div class="card" style="border-top:4px solid #FFA500;">
        <h3><i class="fas fa-bell"></i> Telegram Notification Settings</h3>
        <p style="color:var(--gray); font-size:12px; margin-bottom:10px;">Configure where and how notifications are sent.</p>
        <form method="POST">
            <input type="hidden" name="action" value="update_notif_links">
            Notification Channel ID (Required): <input name="notification_channel" value="{{ settings.notification_channel or '' }}" placeholder="-100xxxxxxxxx">
            Main Channel Link: <input name="notif_main" value="{{ settings.notif_main or '' }}" placeholder="t.me/drama4uofficial">
            Official Chat Link: <input name="notif_chat" value="{{ settings.notif_chat or '' }}" placeholder="t.me/drama2hchat">
            FB Page Link: <input name="notif_fb" value="{{ settings.notif_fb or '' }}" placeholder="facebook.com/bddranaworld">
            Footer Tags/Text: <input name="notif_footer" value="{{ settings.notif_footer or '' }}" placeholder="#drama2h #movies">
            <button class="btn" type="submit" style="background:#FFA500;">Update Notification Box</button>
        </form>
    </div>

    <div class="card">
        <h3><i class="fas fa-plus"></i> Add New Task</h3>
        <form method="POST">
            <input type="hidden" name="action" value="add_task">
            <input name="title" placeholder="Task Title" required>
            <select name="type">
                <option value="monetag">Monetag Script</option>
                <option value="link">Direct Link</option>
            </select>
            <textarea name="content" placeholder="Enter script or link here" style="width:100%; height:80px; background:#1a1a1a; color:white; padding:10px; border-radius:10px; border:1px solid #333;"></textarea>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
                <input type="number" name="reward" placeholder="Reward (Coin)" value="10">
                <input type="number" name="timer" placeholder="Wait Time (Sec)" value="10">
                <input type="number" name="daily_limit" placeholder="Daily Limit" value="1">
            </div>
            <button class="btn" type="submit">Save Task</button>
        </form>
        <div style="margin-top:20px;">
            {% for t in current_tasks %}
            <div class="manage-item">
                <span>{{ t.title }} ({{ t.reward }} Coin)</span>
                <form method="POST" style="margin:0;">
                    <input type="hidden" name="action" value="del_task">
                    <input type="hidden" name="tid" value="{{ t._id }}">
                    <button class="del-btn" type="submit">X</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="card">
        <h3><i class="fas fa-crown"></i> Add Premium Offer</h3>
        <form method="POST">
            <input type="hidden" name="action" value="add_offer">
            <input name="days" placeholder="How many days (e.g. 30)" required>
            <input name="price" placeholder="How many coins (e.g. 100)" required>
            <button class="btn" type="submit">Save Offer</button>
        </form>
        <div style="margin-top:20px;">
            {% for o in current_offers %}
            <div class="manage-item">
                <span>{{ o.days }} Days - {{ o.price }} Coins</span>
                <form method="POST" style="margin:0;">
                    <input type="hidden" name="action" value="del_offer">
                    <input type="hidden" name="oid" value="{{ o._id }}">
                    <button class="del-btn" type="submit">X</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </div>

    <div class="card">
        <h3><i class="fas fa-cog"></i> General Settings</h3>
        <form method="POST">
            <input type="hidden" name="action" value="site">
            Site Name: <input name="site_name" value="{{ settings.site_name }}">
            Notice Bar Text: <input name="notice" value="{{ settings.notice }}">
            <button class="btn" type="submit">Save General Settings</button>
        </form>
    </div>

    <div class="card" style="border-top:4px solid green;">
        <h3><i class="fas fa-ad"></i> Monetag and Lock Settings</h3>
        <form method="POST">
            <input type="hidden" name="action" value="ad">
            Monetag Zone ID: <input name="monetag_id" value="{{ settings.monetag_id }}">
            Ads per episode: <input type="number" name="ad_limit" value="{{ settings.ad_limit }}">
            Lock duration (minutes): <input type="number" name="lock_duration" value="{{ settings.lock_duration }}">
            File channel ID: <input name="file_channel" value="{{ settings.file_channel }}">
            Auto delete time (minutes): <input type="number" name="auto_delete_time" value="{{ settings.auto_delete_time }}">
            Turn off forward?
            <select name="protect_content">
                <option value="Yes" {% if settings.protect_content == 'Yes' %}selected{% endif %}>Yes (Lock Forward)</option>
                <option value="No" {% if settings.protect_content == 'No' %}selected{% endif %}>No (Allow Forward)</option>
            </select>
            <button class="btn" style="background:green;" type="submit">Save Ad Settings</button>
        </form>
    </div>

    <div class="card" style="max-width:800px; border-top:4px solid var(--primary);">
        <h3><i class="fas fa-tasks"></i> Movie Management</h3>
        <form method="GET" style="display:flex; gap:10px; margin-bottom:20px;">
            <input name="search_movie" placeholder="Search..." value="{{ request.args.get('search_movie', '') }}">
            <button type="submit" class="btn" style="width:100px;">Search</button>
        </form>
        <div class="manage-list">
            {% for m in manage_movies %}
            <div class="manage-item">
                <span>{{ m.title }}</span>
                <div style="display:flex;">
                    <form method="POST" style="margin:0;">
                        <input type="hidden" name="action" value="push_notification">
                        <input type="hidden" name="movie_id" value="{{ m._id }}">
                        <button class="notif-btn" type="submit" title="Push Notification"><i class="fas fa-bell"></i></button>
                    </form>
                    <form method="POST" style="margin:0;">
                        <input type="hidden" name="action" value="delete_movie">
                        <input type="hidden" name="movie_id" value="{{ m._id }}">
                        <button class="del-btn" type="submit">Delete</button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_full_page(content, admin_user=admin_user, manage_movies=manage_movies, settings=settings, current_tasks=current_tasks, current_offers=current_offers)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname, lname, num, pw = request.form.get('fname'), request.form.get('lname'), request.form.get('number'), request.form.get('password')
        if mongo.db.users.find_one({"number": num}):
            flash("Account already exists with this number!")
        else:
            role = "admin" if mongo.db.users.count_documents({}) == 0 else "user"
            mongo.db.users.insert_one({
                "fname": fname, "lname": lname, "number": num, 
                "password": generate_password_hash(pw), "role": role, 
                "joined": datetime.datetime.now(),
                "coins": 0, "completed_tasks": [], "premium_until": None,
                "daily_stats": {"date": datetime.datetime.now().strftime("%Y-%m-%d"), "counts": {}}
            })
            flash("Registration successful! Now login.")
            return redirect('/login')
    
    html = """
    <div class="card">
        <h3>Register Now</h3>
        <form method="POST">
            <input name="fname" placeholder="First Name" required>
            <input name="lname" placeholder="Last Name" required>
            <input name="number" placeholder="Mobile Number" required>
            <input type="password" name="password" placeholder="Password" required>
            <button class="btn" type="submit">Register</button>
        </form>
        <div style="text-align:center; margin-top:20px;"><a href="/login" style="color:var(--gray); text-decoration:none;">Already have an account? Login</a></div>
    </div>
    """
    return render_full_page(html)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        num, pw = request.form.get('number'), request.form.get('password')
        user = mongo.db.users.find_one({"number": num})
        if user and check_password_hash(user['password'], pw):
            session.permanent = True
            session['user_id'], session['role'] = str(user['_id']), user.get('role', 'user')
            return redirect('/')
        flash("Wrong number or password!")
    
    html = """
    <div class="card">
        <h3>Login</h3>
        <form method="POST">
            <input name="number" placeholder="Mobile Number" required>
            <input type="password" name="password" placeholder="Password" required>
            <button class="btn" type="submit">Login</button>
        </form>
        <div style="text-align:center; margin-top:20px;"><a href="/register" style="color:var(--gray); text-decoration:none;">No account? Create account</a></div>
    </div>
    """
    return render_full_page(html)

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect('/login')
    u = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    if not u: return redirect('/logout')
    
    expiry_ts = 0
    if u.get('premium_until'):
        expiry_ts = int(u['premium_until'].timestamp() * 1000)
        
    html = """
    <div class="card" style="text-align:center;">
        <div style="width:100px; height:100px; background:var(--primary); border-radius:50%; margin:auto; display:flex; justify-content:center; align-items:center; font-size:40px; margin-bottom:20px;">
            <i class="fas fa-user"></i>
        </div>
        <h2 style="margin-bottom:10px;">{{ u.fname }} {{ u.lname }}</h2>
        <p style="color:var(--gray); margin-bottom:10px;"><i class="fas fa-phone"></i> {{ u.number }}</p>
        <p style="color:var(--gold); font-weight:bold; margin-bottom:10px;"><i class="fas fa-coins"></i> Balance: {{ u.get('coins', 0) }}</p>
        
        {% if u.premium_until and u.premium_until > now %}
        <div style="background:#1a1a1a; border:1px solid var(--gold); border-radius:10px; padding:15px; margin-bottom:20px;">
            <p style="color:var(--gold); font-weight:bold;"><i class="fas fa-crown"></i> Premium Active</p>
            <p style="font-size:12px; color:#fff;">Expiry time left:</p>
            <p id="profile-premium-timer" style="font-size:14px; font-weight:bold; color:#00ff00;"></p>
            <script>startPremiumTimer({{ expiry_ts }}, 'profile-premium-timer');</script>
        </div>
        {% else %}
        <p style="color:var(--primary); font-weight:bold; margin-bottom:20px;">Position: {{ u.role|upper }}</p>
        {% endif %}
        
        <a href="/logout" class="btn" style="background:#333;">Logout</a>
    </div>
    """
    return render_full_page(html, u=u)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# --- Telegram bot handler ---

@bot.message_handler(commands=['start'])
def handle_bot_start(m):
    text = m.text
    settings = get_site_settings()
    channel_id = settings.get('file_channel')
    
    if "file_" in text:
        try:
            msg_id = int(text.split("file_")[1])
            if not channel_id:
                bot.send_message(m.chat.id, "❌ Storage channel not set!")
                return
            
            movie = mongo.db.movies.find_one({"episodes": msg_id})
            ep_index = 0
            if movie:
                ep_index = movie['episodes'].index(msg_id) + 1
            
            movie_name = movie['title'] if movie else "Unknown Movie"
            caption = f"🎬 {movie_name}\n🎞 Episode: {ep_index:02d}\n\nThanks for staying with Drama Store Kings."
            
            protect = True if settings.get('protect_content') == "Yes" else False
            
            sent_msg = bot.copy_message(m.chat.id, channel_id, msg_id, caption=caption, protect_content=protect)
            
            bot.send_message(m.chat.id, f"✅ File provided above.\n⚠️ It will be auto-deleted in {settings.get('auto_delete_time')} minutes.")
            
            threading.Thread(target=delete_msg, args=(m.chat.id, sent_msg.message_id, int(settings.get('auto_delete_time', 5)))).start()

        except Exception as e:
            bot.send_message(m.chat.id, "❌ File not found.")
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🌐 Visit Website", url=BASE_URL))
        
        info = f"👤 Profile Info:\n📝 Name: {m.from_user.first_name} {m.from_user.last_name or ''}\n🆔 ID: {m.from_user.id}\n🔗 Username: @{m.from_user.username or 'N/A'}\n\nWelcome! Visit the website to watch movies."
        bot.send_message(m.chat.id, info, reply_markup=markup)

@bot.message_handler(commands=['movie'])
def start_adding_movie(m):
    if int(m.from_user.id) != int(OWNER_ID):
        bot.send_message(m.chat.id, f"❌ You are not the owner!")
        return
    try:
        parts = m.text.split('/movie ')[1].split(',')
        if len(parts) < 2: raise Exception()
        
        user_states[m.chat.id] = {
            "title": parts[0].strip(), 
            "category": parts[1].strip(), 
            "quality": parts[2].strip() if len(parts) > 2 else "HD Rip",
            "episodes": [], 
            "views": 0, 
            "status": "AWAITING_POSTER"
        }
        bot.send_message(m.chat.id, "📸 Send movie poster photo OR Send Poster File ID as text.")
    except:
        bot.send_message(m.chat.id, "⚠️ Correct format: `/movie Name, Category, Quality`", parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'text', 'video', 'document'])
def handle_bot_inputs(m):
    cid = m.chat.id
    if cid not in user_states: return
    if int(m.from_user.id) != int(OWNER_ID): return 
    
    state = user_states[cid]
    settings = get_site_settings()
    channel_id = settings.get('file_channel')

    if m.text and m.text.strip().lower() == '/done':
        if state["status"] == "AWAITING_EPISODES":
            if not state["episodes"]:
                bot.send_message(cid, "❌ No episodes found.")
                return
            
            res = mongo.db.movies.insert_one(user_states[cid])
            movie_id = str(res.inserted_id)
            
            # --- Auto Notification Logic ---
            send_manual_notification(movie_id)
                
            del user_states[cid]
            bot.send_message(cid, "🚀 Published to website and channel!")
            return

    if state["status"] == "AWAITING_POSTER":
        f_id = None
        if m.content_type == 'photo':
            f_id = m.photo[-1].file_id
        elif m.content_type == 'text':
            f_id = m.text.strip()

        if f_id:
            try:
                # Get File info from Telegram
                file_info = bot.get_file(f_id)
                # Save both systems: URL for website and ID for Telegram Notification
                user_states[cid]["poster"] = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}" # For Website
                user_states[cid]["poster_file_id"] = f_id # For Telegram Notification Channel
                
                user_states[cid]["status"] = "AWAITING_EPISODES"
                bot.send_message(cid, "✅ Poster added (URL & File ID saved). Send video files and finally send /Done.")
            except:
                bot.send_message(cid, "❌ Invalid Photo or File ID.")
        else:
            bot.send_message(cid, "❌ Send a photo or Poster File ID.")

    elif state["status"] == "AWAITING_EPISODES":
        if m.content_type in ['video', 'document']:
            if not channel_id:
                bot.send_message(cid, "❌ No channel ID.")
                return
            try:
                storage_ch = int(channel_id) if str(channel_id).startswith('-') else channel_id
                if m.content_type == 'video':
                    sent = bot.send_video(storage_ch, m.video.file_id)
                else:
                    sent = bot.send_document(storage_ch, m.document.file_id)
                
                user_states[cid]['episodes'].append(sent.message_id)
                bot.send_message(cid, f"✅ Episode {len(user_states[cid]['episodes'])} added.")
            except Exception as e:
                bot.send_message(cid, f"❌ Error: {str(e)}")

@app.route('/tg-webhook', methods=['POST'])
def tg_webhook_receiver():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_json()
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
