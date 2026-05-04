import os
import telebot
import logging
import datetime
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# --- কনফিগারেশন ---
TOKEN = "8655043839:AAE_qIxO1QAORFsSJzpIMybe5a-wWVeDfL4" 
BOT_USERNAME = "dramastorkingsbot" 
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/DramaStoreDB?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "https://indirect-meris-yeasinvai-95120fc6.koyeb.app" 

app = Flask(__name__)
app.secret_key = "ULTRA_FINAL_FULL_MEGA_CODE_VERSION_PRO"
app.config["MONGO_URI"] = MONGO_URI
app.permanent_session_lifetime = datetime.timedelta(days=30)

mongo = PyMongo(app)
bot = telebot.TeleBot(TOKEN, threaded=False)

# ইউজার স্টেট ট্র্যাকিং
user_states = {}

# --- বিস্তারিত প্রিমিয়াম সিএসএস (Design Section) ---
FULL_CSS = """
<style>
    :root { 
        --primary: #e50914; 
        --bg: #050505; 
        --card-bg: #121212; 
        --text: #ffffff; 
        --gray: #b3b3b3; 
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
    .slider { 
        display: flex; 
        overflow-x: auto; 
        gap: 20px; 
        padding: 10px 0 20px; 
        scrollbar-width: none;
    }
    .slider::-webkit-scrollbar { display: none; }
    .slider-item { 
        min-width: 300px; 
        height: 170px; 
        border-radius: 12px; 
        position: relative; 
        overflow: hidden; 
        background: #1a1a1a; 
        cursor: pointer;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .slider-item img { width: 100%; height: 100%; object-fit: cover; opacity: 0.6; transition: var(--transition); }
    .slider-item:hover img { transform: scale(1.05); opacity: 0.8; }
    .slider-info { 
        position: absolute; bottom: 15px; left: 15px; 
        font-weight: bold; font-size: 18px;
        text-shadow: 2px 2px 10px #000;
    }

    .movie-grid { 
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); 
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
    .movie-card:hover { transform: translateY(-8px); border-color: var(--primary); box-shadow: 0 10px 20px rgba(0,0,0,0.5); }
    .movie-card img { width: 100%; height: 240px; object-fit: cover; }
    
    .badge-top-left { position: absolute; top: 10px; left: 10px; background: var(--primary); padding: 4px 10px; font-size: 11px; border-radius: 5px; font-weight: bold; z-index: 10; }
    .badge-bottom-right { position: absolute; bottom: 55px; right: 10px; background: rgba(0,0,0,0.8); padding: 4px 10px; font-size: 11px; border-radius: 5px; display: flex; align-items: center; gap: 5px; }
    
    .movie-info-box { padding: 12px; text-align: center; }
    .movie-info-box h4 { font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #fff; }

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
    input { 
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
    
    /* Admin Manage List */
    .manage-item {
        display: flex; justify-content: space-between; align-items: center;
        background: #1a1a1a; padding: 10px 15px; border-radius: 8px; margin-bottom: 10px;
        border: 1px solid #333;
    }
    .del-btn { background: #ff4d4d; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; }

    @media (max-width: 600px) {
        .movie-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .slider-item { min-width: 250px; }
        .movie-card img { height: 200px; }
    }
</style>
<script>
    function showLoader() { 
        document.getElementById('loader').style.display = 'flex'; 
    }
    window.addEventListener('pageshow', function(event) {
        document.getElementById('loader').style.display = 'none';
    });
</script>
"""

# --- ডাটাবেজ এবং সেটিংস হেল্পার ---
def get_site_settings():
    try:
        s = mongo.db.settings.find_one({"type": "config"})
        if not s:
            default = {"site_name": "PremiumMovie", "notice": "স্বাগতম!", "monetag_id": "10351894", "ad_limit": 2, "lock_duration": 30, "file_channel": ""}
            mongo.db.settings.insert_one({"type": "config", **default})
            return default
        return s
    except Exception as e:
        return {"site_name": "PremiumMovie", "notice": "Error!", "monetag_id": "10351894", "ad_limit": 2, "lock_duration": 30, "file_channel": ""}

# --- মাস্টার টেমপ্লেট মেকার ---
def render_full_page(body_html, **kwargs):
    settings = get_site_settings()
    current_path = request.path
    
    full_html = f"""
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8">
        <title>{{{{ settings.site_name }}}}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        {FULL_CSS}
    </head>
    <body>
        <div id="loader"><div class="spinner"></div><p style="margin-top:20px; color:var(--primary); font-weight:bold;">লোডিং হচ্ছে...</p></div>
        
        <div class="notice-bar">{{{{ settings.notice }}}}</div>
        
        <div class="navbar">
            <a href="/" class="{'active' if current_path == '/' else ''}"><i class="fas fa-home"></i> হোম</a>
            <a href="/profile" class="{'active' if current_path == '/profile' else ''}"><i class="fas fa-user"></i> প্রোফাইল</a>
            {{% if session.get('role') == 'admin' %}}
            <a href="/admin" class="{'active' if current_path == '/admin' else ''}"><i class="fas fa-user-shield"></i> এডমিন</a>
            {{% endif %}}
        </div>

        <div class="search-container">
            <form action="/search" method="GET" class="search-form">
                <input type="text" name="q" placeholder="মুভি বা ড্রামা সার্চ করুন..." value="{{{{ request.args.get('q', '') }}}}" required>
                <button type="submit" class="btn"><i class="fas fa-search"></i></button>
            </form>
        </div>

        <div class="container">
            {{% with messages = get_flashed_messages() %}}
                {{% for m in messages %}}
                    <div style="background:var(--primary); padding:15px; text-align:center; border-radius:10px; margin-bottom:20px; font-weight:bold;">{{{{ m }}}}</div>
                {{% endfor %}}
            {{% endwith %}}
            
            {body_html}
        </div>
    </body>
    </html>
    """
    return render_template_string(full_html, settings=settings, session=session, **kwargs)

# --- সাইট লজিক রাউটস ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST': return "OK", 200 # Koyeb Health Check Support
    if 'user_id' not in session: return redirect(url_for('login'))
    
    page = int(request.args.get('page', 1))
    per_page = 20 if page == 1 else 50
    skip = 0 if page == 1 else 20 + (page - 2) * 50
    
    sliders = list(mongo.db.movies.find().sort("views", -1).limit(20))
    movies = list(mongo.db.movies.find().sort("_id", -1).skip(skip).limit(per_page))

    content = """
    <div class="section-title">টপ ট্রেন্ডিং (ভিওড) <i class="fas fa-fire" style="color:orange;"></i></div>
    <div class="slider">
        {% for s in sliders %}
        <div class="slider-item" onclick="showLoader(); location.href='/movie/{{s._id}}'">
            <img src="{{s.poster}}">
            <div class="slider-info">{{s.title}}</div>
        </div>
        {% endfor %}
    </div>

    <div class="section-title">সদ্য আপলোড করা <i class="fas fa-clock"></i></div>
    <div class="movie-grid">
        {% for m in movies %}
        <div class="movie-card" onclick="showLoader(); location.href='/movie/{{m._id}}'">
            <div class="badge-top-left">{{m.category}}</div>
            <img src="{{m.poster}}">
            <div class="badge-bottom-right"><i class="fas fa-eye"></i> {{m.views}}</div>
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
        <span class="page-info">পৃষ্ঠা নম্বর: {{page}}</span>
        <a href="/?page={{page+1}}" onclick="showLoader()">Next Page <i class="fas fa-chevron-right"></i></a>
    </div>
    """
    return render_full_page(content, sliders=sliders, movies=movies, page=page)

@app.route('/search')
def search():
    if 'user_id' not in session: return redirect(url_for('login'))
    query = request.args.get('q', '')
    results = list(mongo.db.movies.find({"title": {"$regex": query, "$options": "i"}}).sort("_id", -1))
    
    content = f"""
    <div class="section-title">সার্চ রেজাল্ট: "{query}"</div>
    <div class="movie-grid">
        {{% for m in results %}}
        <div class="movie-card" onclick="showLoader(); location.href='/movie/{{{{m._id}}}}'">
            <div class="badge-top-left">{{{{m.category}}}}</div>
            <img src="{{{{m.poster}}}}">
            <div class="badge-bottom-right"><i class="fas fa-eye"></i> {{{{m.views}}}}</div>
            <div class="movie-info-box">
                <h4>{{{{m.title}}}}</h4>
            </div>
        </div>
        {{% else %}}
        <p style="text-align:center; grid-column: 1/-1; padding: 50px; color: var(--gray);">দুঃখিত, আপনার সার্চ করা মুভিটি পাওয়া যায়নি।</p>
        {{% endfor %}}
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
    
    content = f"""
    <div class="back-btn-container">
        <a href="/" onclick="showLoader();" class="back-btn"><i class="fas fa-arrow-left"></i> ব্যাক টু হোম</a>
    </div>
    
    <div style="text-align:center;">
        <img src="{{{{ movie.poster }}}}" style="width:100%; max-width:400px; border-radius:20px; border:3px solid #222; box-shadow: 0 15px 40px rgba(0,0,0,0.7);">
        <h2 style="margin:25px 0 10px; font-size:28px;">{{{{ movie.title }}}}</h2>
        <div style="margin-bottom:30px;">
            <span style="background:#222; padding:5px 15px; border-radius:20px; font-size:14px; margin:0 5px;">{{{{ movie.category }}}}</span>
            <span style="background:#222; padding:5px 15px; border-radius:20px; font-size:14px; margin:0 5px;"><i class="fas fa-eye"></i> {{{{ movie.views }}}} Views</span>
        </div>
        
        <div class="card" style="max-width:100%; text-align:left; border-top:4px solid var(--primary);">
            <h4 style="margin-bottom:20px; border-bottom:1px solid #333; padding-bottom:10px;">ডাউনলোড এবং ওয়াচ লিঙ্ক:</h4>
            <div class="episode-list">
                {{% for msg_id in movie.episodes %}}
                <div class="ep-button" onclick="processAd('{{{{ msg_id }}}}_idx_{{{{ loop.index0 }}}}', '{{{{ msg_id }}}}')">
                    <div>
                        🎬 Episode {{{{ "%02d" % (loop.index0 + 1) }}}}
                        <span class="ep-status" id="status_{{{{ msg_id }}}}_idx_{{{{ loop.index0 }}}}">লোড হচ্ছে...</span>
                    </div>
                    <i class="fas fa-download"></i>
                </div>
                {{% endfor %}}
            </div>
        </div>
    </div>

    <!-- Monetag Integration -->
    <script src='//libtl.com/sdk.js' data-zone='{{{{ settings.monetag_id }}}}' data-sdk='show_{{{{ settings.monetag_id }}}}'></script>
    
    <script>
        const AD_LIMIT = {{{{ settings.ad_limit }}}};
        const LOCK_MINUTES = {{{{ settings.lock_duration }}}};

        function updateStatus(uniqueId) {{
            let data = JSON.parse(localStorage.getItem('ad_data_' + uniqueId) || '{{"count":0, "unlocked_at":0}}');
            let statusEl = document.getElementById('status_' + uniqueId);
            let now = new Date().getTime();
            
            if (data.unlocked_at > 0) {{
                let elapsed = (now - data.unlocked_at) / (1000 * 60);
                if (elapsed >= LOCK_MINUTES) {{
                    data.count = 0;
                    data.unlocked_at = 0;
                    localStorage.setItem('ad_data_' + uniqueId, JSON.stringify(data));
                }}
            }}

            if (data.unlocked_at > 0) {{
                let remain = Math.ceil(LOCK_MINUTES - (now - data.unlocked_at) / (1000 * 60));
                statusEl.innerHTML = "🔓 আনলকড (বাকি " + remain + " মিনিট)";
                statusEl.style.color = "#00ff00";
            }} else {{
                statusEl.innerHTML = "🔒 বিজ্ঞাপন দেখা হয়েছে: " + data.count + "/" + AD_LIMIT;
                statusEl.style.color = "#b3b3b3";
            }}
        }}

        document.querySelectorAll('[id^="status_"]').forEach(el => {{
            updateStatus(el.id.replace('status_', ''));
        }});

        function processAd(uniqueId, fileId) {{
            let data = JSON.parse(localStorage.getItem('ad_data_' + uniqueId) || '{{"count":0, "unlocked_at":0}}');
            let now = new Date().getTime();

            if (data.unlocked_at > 0) {{
                showLoader();
                window.location.href = "https://t.me/" + "{BOT_USERNAME}" + "?start=file_" + fileId;
                return;
            }}

            if (data.count < AD_LIMIT) {{
                if (typeof window['show_' + {{{{ settings.monetag_id }}}}] === 'function') {{
                    window['show_' + {{{{ settings.monetag_id }}}}]();
                }}
                data.count++;
                localStorage.setItem('ad_data_' + uniqueId, JSON.stringify(data));
                updateStatus(uniqueId);
            }} else {{
                data.unlocked_at = now;
                localStorage.setItem('ad_data_' + uniqueId, JSON.stringify(data));
                updateStatus(uniqueId);
                showLoader();
                window.location.href = "https://t.me/" + "{BOT_USERNAME}" + "?start=file_" + fileId;
            }}
        }}
    </script>
    """
    return render_full_page(content, movie=movie)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin': 
        flash("আপনার এডমিন অ্যাক্সেস নেই!")
        return redirect('/')
    
    search_q = request.args.get('search_movie', '')
    manage_movies = list(mongo.db.movies.find({"title": {"$regex": search_q, "$options": "i"}}).sort("_id", -1).limit(50))

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'site':
            mongo.db.settings.update_one({"type": "config"}, {"$set": {
                "site_name": request.form.get('site_name'),
                "notice": request.form.get('notice')
            }}, upsert=True)
            flash("সাইট সেটিংস আপডেট হয়েছে!")
        elif action == 'ad':
            mongo.db.settings.update_one({"type": "config"}, {"$set": {
                "monetag_id": request.form.get('monetag_id'),
                "ad_limit": int(request.form.get('ad_limit')),
                "lock_duration": int(request.form.get('lock_duration')),
                "file_channel": request.form.get('file_channel')
            }}, upsert=True)
            flash("বিজ্ঞাপন ও স্টোরেজ সেটিংস আপডেট হয়েছে!")
        elif action == 'delete_movie':
            mid = request.form.get('movie_id')
            mongo.db.movies.delete_one({"_id": ObjectId(mid)})
            flash("মুভিটি ডিলিট করা হয়েছে!")
            return redirect('/admin')
            
        return redirect('/admin')

    content = """
    <div class="card">
        <h3><i class="fas fa-cog"></i> জেনারেল সেটিংস</h3>
        <form method="POST">
            <input type="hidden" name="action" value="site">
            সাইটের নাম: <input name="site_name" value="{{ settings.site_name }}">
            নোটিশ বার টেক্সট: <input name="notice" value="{{ settings.notice }}">
            <button class="btn" type="submit">সেভ জেনারেল সেটিংস</button>
        </form>
    </div>
    <div class="card" style="border-top:4px solid green;">
        <h3><i class="fas fa-ad"></i> মনিটেগ ও লক সেটিংস</h3>
        <form method="POST">
            <input type="hidden" name="action" value="ad">
            মনিটেগ জোন আইডি: <input name="monetag_id" value="{{ settings.monetag_id }}">
            এপিসোড প্রতি বিজ্ঞাপন: <input type="number" name="ad_limit" value="{{ settings.ad_limit }}">
            লক ডিউরেশন (মিনিট): <input type="number" name="lock_duration" value="{{ settings.lock_duration }}">
            ফাইল চ্যানেল আইডি: <input name="file_channel" value="{{ settings.file_channel }}">
            <button class="btn" style="background:green;" type="submit">সেভ অ্যাড সেটিংস</button>
        </form>
    </div>

    <div class="card" style="max-width:800px; border-top:4px solid var(--primary);">
        <h3><i class="fas fa-tasks"></i> মুভি ম্যানেজমেন্ট (ডিলিট/সার্চ)</h3>
        <form method="GET" style="display:flex; gap:10px; margin-bottom:20px;">
            <input name="search_movie" placeholder="মুভি ডিলিট করতে সার্চ করুন..." value="{{ request.args.get('search_movie', '') }}">
            <button type="submit" class="btn" style="width:100px;">সার্চ</button>
        </form>
        
        <div class="manage-list">
            {% for m in manage_movies %}
            <div class="manage-item">
                <span>{{ m.title }} ({{ m.category }})</span>
                <form method="POST" style="margin:0;" onsubmit="return confirm('আপনি কি নিশ্চিত যে মুভিটি ডিলিট করবেন?')">
                    <input type="hidden" name="action" value="delete_movie">
                    <input type="hidden" name="movie_id" value="{{ m._id }}">
                    <button class="del-btn" type="submit">ডিলিট</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </div>
    """
    return render_full_page(content, manage_movies=manage_movies)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname, lname, num, pw = request.form.get('fname'), request.form.get('lname'), request.form.get('number'), request.form.get('password')
        if mongo.db.users.find_one({"number": num}):
            flash("এই নাম্বার দিয়ে অলরেডি অ্যাকাউন্ট আছে!")
        else:
            role = "admin" if mongo.db.users.count_documents({}) == 0 else "user"
            mongo.db.users.insert_one({
                "fname": fname, "lname": lname, "number": num, 
                "password": generate_password_hash(pw), "role": role, 
                "joined": datetime.datetime.now()
            })
            flash("রেজিস্ট্রেশন সফল! এখন লগিন করুন।")
            return redirect('/login')
    
    html = """
    <div class="card">
        <h3>রেজিস্ট্রেশন করুন</h3>
        <form method="POST">
            <input name="fname" placeholder="ফাস্ট নাম" required>
            <input name="lname" placeholder="লাস্ট নাম" required>
            <input name="number" placeholder="মোবাইল নাম্বার" required>
            <input type="password" name="password" placeholder="পাসওয়ার্ড" required>
            <button class="btn" type="submit">নিবন্ধন করুন</button>
        </form>
        <div style="text-align:center; margin-top:20px;"><a href="/login" style="color:var(--gray); text-decoration:none;">ইতিমধ্যে অ্যাকাউন্ট আছে? লগিন করুন</a></div>
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
        flash("নাম্বার অথবা পাসওয়ার্ড ভুল!")
    
    html = """
    <div class="card">
        <h3>লগিন করুন</h3>
        <form method="POST">
            <input name="number" placeholder="মোাবাইল নাম্বার" required>
            <input type="password" name="password" placeholder="পাসওয়ার্ড" required>
            <button class="btn" type="submit">প্রবেশ করুন</button>
        </form>
        <div style="text-align:center; margin-top:20px;"><a href="/register" style="color:var(--gray); text-decoration:none;">অ্যাকাউন্ট নেই? নতুন অ্যাকাউন্ট খুলুন</a></div>
    </div>
    """
    return render_full_page(html)

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect('/login')
    u = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    html = f"""
    <div class="card" style="text-align:center;">
        <div style="width:100px; height:100px; background:var(--primary); border-radius:50%; margin:auto; display:flex; justify-content:center; align-items:center; font-size:40px; margin-bottom:20px;">
            <i class="fas fa-user"></i>
        </div>
        <h2 style="margin-bottom:10px;">{{{{ u.fname }}}} {{{{ u.lname }}}}</h2>
        <p style="color:var(--gray); margin-bottom:10px;"><i class="fas fa-phone"></i> {{{{ u.number }}}}</p>
        <p style="color:var(--primary); font-weight:bold; margin-bottom:20px;">পজিশন: {{{{ u.role|upper }}}}</p>
        <a href="/logout" class="btn" style="background:#333;">লগআউট (Logout)</a>
    </div>
    """
    return render_full_page(html, u=u)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# --- টেলিগ্রাম বট হ্যান্ডলার ---

@bot.message_handler(commands=['start'])
def handle_bot_start(m):
    text = m.text
    settings = get_site_settings()
    channel_id = settings.get('file_channel')
    
    if "file_" in text:
        try:
            # লিঙ্ক থেকে Message ID বের করা (যেমন: file_12 থেকে 12)
            msg_id = int(text.split("file_")[1])
            if not channel_id:
                bot.reply_to(m, "❌ স্টোরেজ চ্যানেল সেট করা নেই!")
                return
            
            # সরাসরি চ্যানেল থেকে মেসেজ কপি করে পাঠানো
            bot.copy_message(m.chat.id, channel_id, msg_id, caption="🎬 ড্রামা স্টোর কিং এর সাথে থাকার জন্য ধন্যবাদ।")
        except Exception as e:
            bot.reply_to(m, "❌ ফাইলটি পাওয়া যায়নি অথবা চ্যানেল থেকে ডিলিট করা হয়েছে।")
    else:
        bot.reply_to(m, "👋 স্বাগতম! মুভি এড করতে /movie নাম, ক্যাটাগরি লিখুন।")

@bot.message_handler(commands=['movie'])
def start_adding_movie(m):
    try:
        parts = m.text.split('/movie ')[1].split(',')
        if len(parts) < 2: raise Exception()
        user_states[m.chat.id] = {"title": parts[0].strip(), "category": parts[1].strip(), "episodes": [], "views": 0, "status": "AWAITING_POSTER"}
        bot.reply_to(m, "📸 মুভির পোস্টার ফটো পাঠান।")
    except:
        bot.reply_to(m, "⚠️ সঠিক নিয়ম: `/movie নাম, ক্যাটাগরি`", parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'text', 'video', 'document'])
def handle_bot_inputs(m):
    cid = m.chat.id
    if cid not in user_states: return
    state = user_states[cid]
    settings = get_site_settings()
    channel_id = settings.get('file_channel')

    if state["status"] == "AWAITING_POSTER":
        if m.content_type == 'photo':
            file_info = bot.get_file(m.photo[-1].file_id)
            user_states[cid]["poster"] = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
            user_states[cid]["status"] = "AWAITING_EPISODES"
            bot.reply_to(m, "✅ পোস্টার এড হয়েছে। এখন ভিডিও ফাইল পাঠান এবং সব শেষে /Done কমান্ড দিন।")
        else:
            bot.reply_to(m, "❌ দয়া করে একটি ফটো পাঠান।")

    elif state["status"] == "AWAITING_EPISODES":
        if m.text == '/Done':
            if not state["episodes"]:
                bot.reply_to(m, "❌ কোনো এপিসোড এড করেননি।")
                return
            mongo.db.movies.insert_one(user_states[cid])
            del user_states[cid]
            bot.reply_to(m, "🚀 ড্রামাটি সফলভাবে ওয়েবসাইটে পাবলিশ হয়েছে!")
        elif m.content_type in ['video', 'document']:
            if not channel_id:
                bot.reply_to(m, "❌ এডমিন প্যানেলে স্টোরেজ চ্যানেল আইডি সেট করা নেই।")
                return
            try:
                # চ্যানেলে পাঠানো এবং Message ID টি সেভ করা
                if m.content_type == 'video':
                    sent = bot.send_video(channel_id, m.video.file_id)
                else:
                    sent = bot.send_document(channel_id, m.document.file_id)
                
                # আমরা এখানে Message ID সেভ করছি (যা একটি ছোট সংখ্যা হবে)
                user_states[cid]['episodes'].append(sent.message_id)
                bot.reply_to(m, f"✅ এপিসোড {len(user_states[cid]['episodes'])} যুক্ত হয়েছে (ID: {sent.message_id})। আরও থাকলে পাঠান নতুবা /Done দিন।")
            except Exception as e:
                bot.reply_to(m, f"❌ এরর: {str(e)}\nনিশ্চিত করুন বট চ্যানেলে এডমিন আছে।")

# --- Webhook receiver ---

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
