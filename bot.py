import os
import telebot
import logging
import datetime # এটি আগে মিসিং ছিল যার জন্য ইরোর আসত
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, jsonify
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# --- কনফিগারেশন ---
TOKEN = "8655043839:AAFTUxq56taWUPU9uXRKuL7iyKLXRvk-WqM" 
BOT_USERNAME = "dramastorkingsbot" 
# ডাটাবেজ নাম 'DramaStoreDB' যুক্ত করা হয়েছে যাতে ডাটা মিসিং না হয়
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/DramaStoreDB?retryWrites=true&w=majority&appName=Cluster0"
BASE_URL = "https://indirect-meris-yeasinvai-95120fc6.koyeb.app" 

app = Flask(__name__)
app.secret_key = "ULTRA_FINAL_FULL_MEGA_CODE_VERSION_PRO"
app.config["MONGO_URI"] = MONGO_URI
# সেশন লাইফটাইম বাড়ানো হয়েছে
app.permanent_session_lifetime = datetime.timedelta(days=30)

mongo = PyMongo(app)
bot = telebot.TeleBot(TOKEN, threaded=False)

# ইউজার স্টেট ট্র্যাকিং (মুভি এড করার জন্য)
user_states = {}

# --- বিস্তারিত প্রিমিয়াম সিএসএস (Design Section) ---
# আপনার দেওয়া CSS এক বিন্দুও পরিবর্তন করা হয়নি
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
    
    /* Loader Animation */
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

    /* Notice Bar */
    .notice-bar { 
        background: var(--primary); 
        padding: 12px; 
        text-align: center; 
        font-weight: bold; 
        font-size: 14px; 
        position: sticky; top: 0; z-index: 1000;
        box-shadow: 0 2px 10px rgba(0,0,0,0.5);
    }

    /* Navbar */
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

    .container { padding: 20px; max-width: 1200px; margin: auto; }

    /* Top Views Slider */
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
        -ms-overflow-style: none;
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

    /* Movie Grid Layout */
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

    /* Pagination Styling */
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

    /* Forms & Detail Cards */
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

    /* Episode Buttons */
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
    
    /* Responsive */
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
            # ডিফল্ট lock_duration মিনিট হিসেবে ৩০ রাখা হলো
            default = {"site_name": "PremiumMovie", "notice": "স্বাগতম!", "monetag_id": "10351894", "ad_limit": 2, "lock_duration": 30}
            mongo.db.settings.insert_one({"type": "config", **default})
            return default
        # যদি lock_duration না থাকে তবে আপডেট করা
        if "lock_duration" not in s:
            mongo.db.settings.update_one({"type": "config"}, {"$set": {"lock_duration": 30}})
            s["lock_duration"] = 30
        return s
    except Exception as e:
        return {"site_name": "PremiumMovie", "notice": "Error!", "monetag_id": "10351894", "ad_limit": 2, "lock_duration": 30}

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

@app.route('/')
def index():
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
                {{% for fid in movie.episodes %}}
                <div class="ep-button" onclick="processAd('{{{{ fid }}}}_idx_{{{{ loop.index0 }}}}', '{{{{ fid }}}}')">
                    <div>
                        🎬 Episode {{{{ "%02d" % (loop.index0 + 1) }}}}
                        <span class="ep-status" id="status_{{{{ fid }}}}_idx_{{{{ loop.index0 }}}}">লোড হচ্ছে...</span>
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
                "lock_duration": int(request.form.get('lock_duration'))
            }}, upsert=True)
            flash("বিজ্ঞাপন ও টাইমার সেটিংস আপডেট হয়েছে!")
        return redirect('/admin')

    content = """
    <div class="back-btn-container"><a href="/" class="back-btn"><i class="fas fa-arrow-left"></i> ব্যাক টু সাইট</a></div>
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
            মনিটেগ জোন আইডি (Zone ID): <input name="monetag_id" value="{{ settings.monetag_id }}">
            এপিসোড প্রতি বিজ্ঞাপনের সংখ্যা: <input type="number" name="ad_limit" value="{{ settings.ad_limit }}">
            লিঙ্ক কত মিনিট আনলক থাকবে: <input type="number" name="lock_duration" value="{{ settings.lock_duration }}">
            <button class="btn" style="background:green;" type="submit">সেভ অ্যাড সেটিংস</button>
        </form>
    </div>
    """
    return render_full_page(content)

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
            <input name="number" placeholder="মোবাইল নাম্বার" required>
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

# --- টেলিগ্রাম বট (ফাইল ডেলিভারি সেকশন - ফিক্সড) ---

@bot.message_handler(commands=['start'])
def handle_bot_start(m):
    # m.text এর মধ্যে '/start file_id' অংশটি থাকে
    command_parts = m.text.split()
    
    if len(command_parts) > 1:
        # ইউজার লিঙ্ক থেকে এসেছে এবং সাথে ফাইল আইডি আছে
        file_id = command_parts[1]
        bot.send_chat_action(m.chat.id, 'upload_document')
        
        try:
            # প্রথমে ভিডিও হিসেবে পাঠানোর চেষ্টা করবে
            bot.send_video(m.chat.id, file_id, caption="🎬 আপনার কাঙ্ক্ষিত ভিডিওটি এখানে।\n\nড্রামা স্টোর কিং এর সাথে থাকার জন্য ধন্যবাদ।")
        except Exception:
            try:
                # ভিডিও না হলে ডকুমেন্ট হিসেবে পাঠানোর চেষ্টা করবে
                bot.send_document(m.chat.id, file_id, caption="🎬 আপনার কাঙ্ক্ষিত ফাইলটি এখানে।\n\nড্রামা স্টোর কিং এর সাথে থাকার জন্য ধন্যবাদ।")
            except Exception:
                bot.reply_to(m, "❌ দুঃখিত, ফাইলটি বটের সার্ভারে খুঁজে পাওয়া যায়নি।")
    else:
        # সাধারণ স্টার্ট কমান্ড
        bot.reply_to(m, "👋 স্বাগতম! মুভি বা ড্রামা এড করতে /movie কমান্ড ব্যবহার করুন।")

@bot.message_handler(commands=['movie'])
def start_adding_movie(m):
    try:
        parts = m.text.split('/movie ')[1].split(',')
        if len(parts) < 2: raise Exception()
        
        user_states[m.chat.id] = {
            "title": parts[0].strip(), 
            "category": parts[1].strip(), 
            "episodes": [], 
            "views": 0, 
            "status": "AWAITING_POSTER"
        }
        bot.reply_to(m, f"🎬 ড্রামা: *{parts[0].strip()}*\n📂 ক্যাটাগরি: *{parts[1].strip()}*\n\nএখন পোস্টার পাঠান।", parse_mode="Markdown")
    except:
        bot.reply_to(m, "⚠️ নিয়ম: `/movie নাম, ক্যাটাগরি`", parse_mode="Markdown")

@bot.message_handler(content_types=['photo', 'text', 'video', 'document'])
def handle_bot_inputs(m):
    cid = m.chat.id
    if cid not in user_states: return

    state = user_states[cid]
    if state["status"] == "AWAITING_POSTER":
        if m.content_type == 'photo':
            file_id = m.photo[-1].file_id
            user_states[cid]["poster"] = bot.get_file_url(file_id)
        elif m.content_type == 'text':
            user_states[cid]["poster"] = m.text
        else:
            bot.reply_to(m, "❌ ফটো বা লিঙ্ক দিন!")
            return
        
        user_states[cid]["status"] = "AWAITING_EPISODES"
        bot.reply_to(m, "✅ পোস্টার যুক্ত হয়েছে! এখন ফাইলগুলো পাঠান এবং শেষে /Done দিন।")

    elif state["status"] == "AWAITING_EPISODES":
        if m.content_type == 'text' and m.text == '/Done':
            if not user_states[cid]["episodes"]:
                bot.reply_to(m, "❌ কোনো ফাইল দেননি!")
                return
            final_data = user_states[cid].copy()
            del final_data["status"]
            mongo.db.movies.insert_one(final_data)
            del user_states[cid]
            bot.reply_to(m, "🚀 ড্রামাটি পাবলিশ হয়েছে!")
        elif m.content_type in ['video', 'document']:
            fid = m.video.file_id if m.content_type == 'video' else m.document.file_id
            user_states[cid]['episodes'].append(fid)
            bot.reply_to(m, f"✅ এপিসোড {len(user_states[cid]['episodes'])} যুক্ত হয়েছে।")

@app.route('/' + TOKEN, methods=['POST'])
def webhook_receiver():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

@app.route('/set_webhook')
def setup_webhook():
    success = bot.set_webhook(url=BASE_URL + '/' + TOKEN)
    return "<h1>Webhook Connection Successfull!</h1>" if success else "<h1>Webhook Failed!</h1>"

handler = app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
