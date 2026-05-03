import os
import random
import base64
import math
import time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# ⚙️ ডাটাবেস এবং কনফিগারেশন
# ==========================================
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

client = MongoClient(MONGO_URL)
db = client['DramaStore_Mega_Project']

# কালেকশন সমূহ
movies_col = db['movies']
users_col = db['users']
link_tasks_col = db['link_tasks']
ad_tasks_col = db['ad_tasks']
packages_col = db['packages']
settings_col = db['settings']
categories_col = db['categories']
unlock_logs = db['unlock_logs']

# ডিফল্ট সেটিংস সেটআপ
def setup_site():
    if not settings_col.find_one({"key": "main_config"}):
        settings_col.insert_one({
            "key": "main_config",
            "site_name": "Premium Drama Store",
            "notice": "🌟 ৫টি অ্যাড দেখে মুভি আনলক করুন এবং প্রিমিয়াম মুভি উপভোগ করুন!",
            "unlock_limit": 5,
            "ep_zone_id": "10351894",
            "task_zone_ids": "10351894, 10351895, 10351896"
        })
    if categories_col.count_documents({}) == 0:
        categories_col.insert_many([{"name": "Chinese Drama"}, {"name": "Korean Drama"}, {"name": "Action Drama"}, {"name": "Romantic"}])

setup_site()

app = Flask(__name__)
app.secret_key = "ULTRA_MEGA_PRO_SECRET_KEY_9999"

# ==========================================
# 🎨 আল্ট্রা প্রিমিয়াম সিএসএস (Glassmorphism UI)
# ==========================================
STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Poppins:wght@300;400;600;700&display=swap');
    :root { 
        --primary: #00d2ff; 
        --secondary: #3a7bd5; 
        --accent: #ff007a; 
        --bg: #0b0e14; 
        --glass: rgba(22, 27, 34, 0.85); 
        --border: rgba(255, 255, 255, 0.1); 
    }
    * { box-sizing: border-box; font-family: 'Poppins', sans-serif; transition: 0.3s; }
    body { background: var(--bg); color: #e6edf3; margin: 0; padding-bottom: 100px; overflow-x: hidden; }
    
    header { 
        background: linear-gradient(135deg, var(--primary), var(--secondary)); 
        padding: 25px; text-align: center; font-family: 'Orbitron'; 
        font-size: 24px; font-weight: 700; position: sticky; top: 0; z-index: 1000; 
        box-shadow: 0 5px 25px rgba(0,0,0,0.6); 
    }
    
    .notice-bar { background: rgba(255, 193, 7, 0.1); color: #ffc107; padding: 12px; font-size: 14px; text-align: center; border-bottom: 1px solid #ffc107; }
    .container { width: 95%; max-width: 1200px; margin: auto; padding: 15px; }
    
    /* Movie Grid */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 20px; margin-top: 20px; }
    @media (min-width: 768px) { .grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); } }
    
    .movie-card { 
        background: var(--glass); border-radius: 20px; overflow: hidden; 
        border: 1px solid var(--border); text-decoration: none; color: inherit; 
        position: relative; backdrop-filter: blur(10px); 
    }
    .movie-card:hover { transform: translateY(-8px); border-color: var(--primary); box-shadow: 0 10px 30px rgba(0, 210, 255, 0.3); }
    .movie-card img { width: 100%; height: 260px; object-fit: cover; }
    .movie-card .info { padding: 15px; text-align: center; font-weight: 600; font-size: 14px; }
    .cat-tag { position: absolute; top: 10px; left: 10px; background: var(--accent); color: white; padding: 4px 10px; border-radius: 8px; font-size: 11px; font-weight: bold; }

    /* Buttons */
    .btn { 
        background: linear-gradient(90deg, var(--primary), var(--secondary)); 
        color: white; padding: 14px; border-radius: 12px; text-decoration: none; 
        display: block; text-align: center; border: none; font-weight: 600; 
        cursor: pointer; margin: 10px 0; width: 100%; font-size: 16px; 
    }
    .btn:active { transform: scale(0.96); }
    .btn-red { background: linear-gradient(90deg, #ff416c, #ff4b2b) !important; }
    .btn-unlock { background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%) !important; }

    /* Glass Panels */
    .glass-panel { background: var(--glass); padding: 25px; border-radius: 20px; border: 1px solid var(--border); margin-bottom: 20px; backdrop-filter: blur(15px); }

    /* Inputs */
    input, select, textarea { 
        width: 100%; padding: 15px; border-radius: 12px; border: 1px solid var(--border); 
        background: #0d1117; color: white; margin-bottom: 20px; font-size: 16px; 
    }
    
    /* Bottom Navigation */
    .bottom-nav { 
        position: fixed; bottom: 0; width: 100%; background: rgba(22, 27, 34, 0.95); 
        display: flex; justify-content: space-around; padding: 15px 0; 
        border-top: 1px solid var(--border); z-index: 1000; 
    }
    .bottom-nav a { color: #8b949e; text-decoration: none; font-size: 12px; text-align: center; flex: 1; }
    .bottom-nav a.active { color: var(--primary); font-weight: 700; }
    .bottom-nav i { font-size: 22px; margin-bottom: 5px; display: block; }

    /* Admin Styles */
    .admin-nav { display: flex; overflow-x: auto; gap: 15px; padding: 10px 0; border-bottom: 1px solid var(--border); margin-bottom: 25px; }
    .admin-nav a { background: #21262d; color: white; padding: 10px 20px; border-radius: 30px; text-decoration: none; font-size: 14px; white-space: nowrap; }
    .admin-nav a.active { background: var(--primary); }
</style>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
"""

# ==========================================
# 🛠️ হেল্পার ফাংশনস
# ==========================================
def get_user():
    if 'uid' in session: return users_col.find_one({"_id": ObjectId(session['uid'])})
    return None

def is_premium(user):
    if not user: return False
    if 'premium_until' not in user: return False
    return user['premium_until'] > datetime.utcnow()

# ==========================================
# 👤 ইউজার অথেনটিকেশন (Login/Register)
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({"mobile": request.form.get('mobile')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['uid'] = str(user['_id']); return redirect('/')
        flash("❌ ভুল মোবাইল নম্বর বা পাসওয়ার্ড!")
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container' style='max-width:450px; margin-top:50px;'><div class='glass-panel'><h2>🔑 Login</h2><form method='post'><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>Login Now</button></form><br><a href='/register' style='color:gray;text-decoration:none;'>নতুন অ্যাকাউন্ট খুলুন</a></div></div></body></html>")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname, mobile, pwd = request.form.get('fname'), request.form.get('mobile'), request.form.get('password')
        if users_col.find_one({"mobile": mobile}): flash("❌ এই নম্বর দিয়ে অ্যাকাউন্ট আছে!")
        else:
            users_col.insert_one({"fname": fname, "mobile": mobile, "password": generate_password_hash(pwd), "coins": 0, "premium_until": datetime.utcnow()})
            return redirect('/login')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container' style='max-width:450px; margin-top:50px;'><div class='glass-panel'><h2>🚀 Register</h2><form method='post'><input name='fname' placeholder='Full Name' required><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>Create Account</button></form><br><a href='/login' style='color:gray;text-decoration:none;'>লগইন করুন</a></div></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

# ==========================================
# 🏠 ইউজার হোমপেজ
# ==========================================
@app.route('/')
def index():
    user = get_user()
    if not user: return redirect('/login')
    conf = settings_col.find_one({"key": "main_config"})
    cat_filter = request.args.get('cat')
    query = {"category": cat_filter} if cat_filter else {}
    movies = list(movies_col.find(query).sort("_id", -1))
    cats = list(categories_col.find())
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>{{{{conf['site_name']}}}}</title>{STYLE}</head><body>
            <header>{{{{conf['site_name']}}}}</header>
            <div class="notice-bar"><marquee>{{{{conf['notice']}}}}</marquee></div>
            <div class="container">
                <div style="overflow-x:auto; display:flex; gap:12px; margin-bottom:20px; scrollbar-width:none;">
                    <a href="/" class="btn" style="width:auto; padding:8px 20px; font-size:13px; background:{{{{'var(--primary)' if not cat_filter else '#21262d'}}}}">All</a>
                    {{% for c in cats %}}
                    <a href="/?cat={{{{c.name}}}}" class="btn" style="width:auto; padding:8px 20px; font-size:13px; background:{{{{'var(--primary)' if cat_filter==c.name else '#21262d'}}}}">{{{{c.name}}}}</a>
                    {{% endfor %}}
                </div>
                <div class="grid">
                    {{% for m in movies %}}
                    <a href="/movie/{{{{m._id}}}}" class="movie-card">
                        <span class="cat-tag">{{{{m.category}}}}</span>
                        <img src="{{{{m.poster}}}}">
                        <div class="info">{{{{m.name}}}}</div>
                    </a>
                    {{% endfor %}}
                </div>
            </div>
            {get_nav('/')}
        </body></html>
    """, conf=conf, movies=movies, cats=cats, cat_filter=cat_filter)

# ==========================================
# 🎬 মুভি ডিটেইল এবং আনলক সিস্টেম
# ==========================================
@app.route('/movie/<id>')
def movie_detail(id):
    user = get_user()
    if not user: return redirect('/login')
    movie = movies_col.find_one({"_id": ObjectId(id)})
    conf = settings_col.find_one({"key": "main_config"})
    
    log = unlock_logs.find_one({"uid": user['_id'], "mid": movie['_id']})
    watched = log['count'] if log else 0
    limit = int(conf.get('unlock_limit', 5))
    is_unlocked = watched >= limit or is_premium(user)
    
    ep_zid = conf.get('ep_zone_id', '10351894')

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>{{{{movie.name}}}}</header>
            <div class="container" style="text-align:center;">
                <img src="{{{{movie.poster}}}}" style="width:100%; max-width:450px; border-radius:25px; box-shadow: 0 15px 40px rgba(0,0,0,0.6);">
                
                <div class="glass-panel" style="margin-top:25px;">
                    {{% if is_unlocked %}}
                        <h3 style="color:var(--primary); margin-bottom:20px;">🎬 Episodes Unlocked</h3>
                        {{% for ep in movie.episodes %}}
                            <div style="margin-bottom:15px;">
                                <a href="{{{{ep}}}}" class="btn">🚀 Play Episode {{{{loop.index}}}}</a>
                            </div>
                        {{% endfor %}}
                    {{% else %}}
                        <h3 style="color:var(--accent);">🔒 Episodes Locked</h3>
                        <p>মুভিটি আনলক করতে আপনাকে <b>{{{{limit}}}}</b> টি অ্যাড দেখতে হবে।</p>
                        <div style="background:#000; padding:15px; border-radius:15px; font-size:20px; font-weight:bold; margin-bottom:15px;">
                            Watched: {{{{watched}}}} / {{{{limit}}}}
                        </div>
                        <div id="ad-inject"></div>
                        <button class="btn btn-unlock" onclick="playUnlockAd()">Watch Ad to Unlock</button>
                    {{% endif %}}
                </div>
                <a href="/" class="btn btn-red">Back to Home</a>
            </div>
            <script>
                function playUnlockAd() {{
                    const zid = "{{{{ep_zid}}}}";
                    const container = document.getElementById('ad-inject');
                    container.innerHTML = "";
                    
                    // Monetag Ad Logic Fix
                    const s = document.createElement('script');
                    s.src = 'https://libtl.com/sdk.js';
                    s.setAttribute('data-zone', zid);
                    s.setAttribute('data-sdk', 'show_'+zid);
                    s.async = true;
                    s.onload = () => {{
                        if (typeof window['show_'+zid] === 'function') {{
                            window['show_'+zid]();
                        }}
                    }};
                    container.appendChild(s);
                    
                    fetch('/track_ad/{{{{movie._id}}}}').then(() => {{
                        setTimeout(() => {{ location.reload(); }}, 8000);
                    }});
                }}
            </script>
        </body></html>
    """, movie=movie, is_unlocked=is_unlocked, watched=watched, limit=limit, conf=conf, ep_zid=ep_zid)

@app.route('/track_ad/<mid>')
def track_ad(mid):
    user = get_user()
    if user:
        unlock_logs.update_one({"uid": user['_id'], "mid": ObjectId(mid)}, {"$inc": {"count": 1}}, upsert=True)
    return "ok"

# ==========================================
# 💰 টাস্ক সিস্টেম (Earn Coins)
# ==========================================
@app.route('/tasks')
def tasks():
    user = get_user()
    if not user: return redirect('/login')
    conf = settings_col.find_one({"key": "main_config"})
    l_tasks = list(link_tasks_col.find())
    a_tasks = list(ad_tasks_col.find())
    
    # টাস্ক জোন আইডি প্রসেস
    task_zones = [z.strip() for z in conf.get('task_zone_ids', '').split(',')]

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>💰 Earn Coins</header>
            <div class="container">
                <div class="glass-panel" style="text-align:center;">
                    <span style="font-size:16px; color:gray;">My Balance</span><br>
                    <span style="font-size:35px; color:var(--primary); font-weight:bold;">{{{{user.coins}}}} 🪙</span>
                </div>
                
                <h3>🔗 Link Tasks</h3>
                {{% for t in l_tasks %}}
                <div class="glass-panel" style="display:flex; justify-content:space-between; align-items:center; padding:15px;">
                    <div><b>{{{{t.name}}}}</b><br><small style="color:var(--primary);">Reward: +{{{{t.coins}}}} Coins</small></div>
                    <a href="{{{{t.link}}}}" target="_blank" onclick="fetch('/claim/link/{{{{t._id}}}}')" class="btn" style="width:80px; margin:0; padding:10px;">Go</a>
                </div>
                {{% endfor %}}

                <h3>📺 Video Ad Tasks</h3>
                <p style="font-size:13px; color:gray; margin-bottom:15px;">প্রতিটি ভিডিও অ্যাড দেখলে আপনি ৫ কয়েন করে পাবেন।</p>
                {{% for t in a_tasks %}}
                <div class="glass-panel">
                    <b>{{{{t.name}}}}</b> (+{{{{t.coins}}}} Coins)
                    <div id="task-ad-{{{{t._id}}}}"></div>
                    <button class="btn btn-unlock" onclick="watchRandomAd('{{{{t._id}}}}')">Watch Ad</button>
                </div>
                {{% endfor %}}
            </div>
            <script>
                const zones = {task_zones};
                function watchRandomAd(tid) {{
                    const zid = zones[Math.floor(Math.random() * zones.length)];
                    const container = document.getElementById('task-ad-'+tid);
                    container.innerHTML = "";
                    
                    // Monetag Ad Logic Fix
                    const s = document.createElement('script');
                    s.src = 'https://libtl.com/sdk.js';
                    s.setAttribute('data-zone', zid);
                    s.setAttribute('data-sdk', 'show_'+zid);
                    s.async = true;
                    s.onload = () => {{
                        if (typeof window['show_'+zid] === 'function') {{
                            window['show_'+zid]();
                        }}
                    }};
                    container.appendChild(s);
                    
                    fetch('/claim/ad/'+tid);
                    alert("অ্যাড লোড হচ্ছে... অনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন।");
                }}
            </script>
            {get_nav('/tasks')}
        </body></html>
    """, user=user, l_tasks=l_tasks, a_tasks=a_tasks, task_zones=task_zones)

@app.route('/claim/<type>/<tid>')
def claim_reward(type, tid):
    user = get_user()
    if not user: return "err"
    col = link_tasks_col if type == 'link' else ad_tasks_col
    t = col.find_one({"_id": ObjectId(tid)})
    if t:
        users_col.update_one({"_id": user['_id']}, {"$inc": {"coins": int(t['coins'])}})
    return "ok"

# ==========================================
# 💎 প্রিমিয়াম এবং প্রোফাইল
# ==========================================
@app.route('/premium')
def premium():
    user = get_user()
    if not user: return redirect('/login')
    pkgs = list(packages_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>💎 Premium Access</header>
            <div class="container">
                {{% for p in pkgs %}}
                <div class="glass-panel" style="text-align:center; border: 2px solid gold;">
                    <h2 style="color:gold; margin:0;">{{{{p.name}}}}</h2>
                    <p>{{{{p.days}}}} দিন প্রিমিয়াম মেয়াদ। কোনো অ্যাড আসবে না।</p>
                    <div style="font-size:25px; font-weight:bold;">মূল্য: {{{{p.coins}}}} Coins</div>
                    <a href="/buy/{{{{p._id}}}}" class="btn" style="background:gold; color:black; margin-top:20px;">Activate Now</a>
                </div>
                {{% endfor %}}
            </div>
            {get_nav('/premium')}
        </body></html>
    """, pkgs=pkgs)

@app.route('/buy/<pid>')
def buy_pkg(pid):
    user = get_user()
    p = packages_col.find_one({"_id": ObjectId(pid)})
    if user and p and user['coins'] >= int(p['coins']):
        expiry = max(user.get('premium_until', datetime.utcnow()), datetime.utcnow()) + timedelta(days=int(p['days']))
        users_col.update_one({"_id": user['_id']}, {"$set": {"premium_until": expiry}, "$inc": {"coins": -int(p['coins'])}})
    return redirect('/premium')

@app.route('/profile')
def profile():
    user = get_user()
    if not user: return redirect('/login')
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>👤 User Profile</header>
            <div class="container" style="text-align:center;">
                <div class="glass-panel">
                    <i class="fas fa-user-circle" style="font-size:70px; color:var(--primary); margin-bottom:15px;"></i>
                    <h2>{{{{user.fname}}}}</h2>
                    <p>Mobile: {{{{user.mobile}}}}</p>
                    <p>Coins: {{{{user.coins}}}} 🪙</p>
                    <div style="padding:15px; border-radius:15px; background:rgba(0,210,255,0.1); border:1px solid var(--primary);">
                        Status: {{{{ '🌟 Premium User' if user.premium_until > now else '🆓 Free Member' }}}}
                    </div>
                </div>
                <a href="/logout" class="btn btn-red" style="margin-top:20px;">Logout Account</a>
            </div>
            {get_nav('/profile')}
        </body></html>
    """, user=user, now=datetime.utcnow())

# ==========================================
# ⚡ প্রিমিয়াম অ্যাডমিন প্যানেল (Full Manual Control)
# ==========================================
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'admin' in session: return redirect('/admin/dashboard')
    if request.method == 'POST' and request.form.get('p') == ADMIN_PASS:
        session['admin'] = True; return redirect('/admin/dashboard')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container' style='max-width:450px; margin-top:50px;'><div class='glass-panel'><h2>Admin Access</h2><form method='post'><input type='password' name='p' style='padding:15px;border-radius:10px;'><button class='btn' style='max-width:200px;margin:20px auto;'>Login</button></form></div></div></body></html>")

@app.route('/admin/dashboard')
def admin_dash():
    if 'admin' not in session: return redirect('/admin')
    conf = settings_col.find_one({"key": "main_config"})
    movies = list(movies_col.find().sort("_id", -1))
    cats = list(categories_col.find())
    l_tasks = list(link_tasks_col.find())
    a_tasks = list(ad_tasks_col.find())
    pkgs = list(packages_col.find())

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>🛠 Admin Control Panel</header>
            <div class="container">
                <div class="admin-nav">
                    <a href="#settings">Settings</a> <a href="#movies">Manage Movies</a> <a href="#tasks">Tasks</a> <a href="#pkgs">Packages</a> <a href="/logout">Logout</a>
                </div>

                <!-- সেটিংস সেকশন -->
                <section id="settings" class="glass-panel">
                    <h3>⚙️ Global Settings</h3>
                    <form action="/admin/update_settings" method="post">
                        Site Name: <input name="sn" value="{{{{conf['site_name']}}}}">
                        Notice: <input name="nt" value="{{{{conf['notice']}}}}">
                        <b>Unlock Ad Limit:</b> <input name="ul" type="number" value="{{{{conf['unlock_limit']}}}}">
                        <b>Episode Ad Zone ID:</b> <input name="ez" value="{{{{conf['ep_zone_id']}}}}">
                        <b>Task Ad Zone IDs (Comma Separated):</b> <input name="tz" value="{{{{conf['task_zone_ids']}}}}">
                        <button class="btn">Save Configuration</button>
                    </form>
                </section>

                <!-- মুভি সেকশন -->
                <section id="movies" class="glass-panel">
                    <h3>🎬 Add New Movie</h3>
                    <form action="/admin/add_movie" method="post" enctype="multipart/form-data">
                        <input name="name" placeholder="Movie Name" required>
                        <select name="cat">
                            {{% for c in cats %}}<option>{{{{c.name}}}}</option>{{% endfor %}}
                        </select>
                        <label>Poster Image (Gallery):</label>
                        <input type="file" name="poster" accept="image/*" required>
                        <label>Episode Links (One per line):</label>
                        <textarea name="episodes" rows="5" placeholder="https://link1.com&#10;https://link2.com"></textarea>
                        <button class="btn btn-unlock">Upload & Save Movie</button>
                    </form>
                    <hr>
                    <h4>Movie List</h4>
                    {{% for m in movies %}}
                    <div style="display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #333;">
                        <span>{{{{m.name}}}}</span>
                        <a href="/admin/del/movie/{{{{m._id}}}}" style="color:red; text-decoration:none;">[Delete]</a>
                    </div>
                    {{% endfor %}}
                </section>

                <!-- টাস্ক সেকশন -->
                <section id="tasks" class="glass-panel">
                    <h3>🔗 Task Management</h3>
                    <form action="/admin/add_task" method="post">
                        <input name="n" placeholder="Task Name"> <input name="l" placeholder="Link (for Link Task)"> <input name="c" placeholder="Coins">
                        <select name="type"><option value="link">Link Task</option><option value="ad">Ad Task</option></select>
                        <button class="btn">Add Task</button>
                    </form>
                    <hr>
                    {{% for t in l_tasks %}}
                    <div style="display:flex; justify-content:space-between; padding:5px;">
                        <span>(Link) {{{{t.name}}}}</span> <a href="/admin/del/link/{{{{t._id}}}}" style="color:red;">[Del]</a>
                    </div>
                    {{% endfor %}}
                    {{% for t in a_tasks %}}
                    <div style="display:flex; justify-content:space-between; padding:5px;">
                        <span>(Ad) {{{{t.name}}}}</span> <a href="/admin/del/ad/{{{{t._id}}}}" style="color:red;">[Del]</a>
                    </div>
                    {{% endfor %}}
                </section>
                
                <!-- প্যাকেজ সেকশন -->
                <section id="pkgs" class="glass-panel">
                    <h3>💎 Premium Packages</h3>
                    <form action="/admin/add_pkg" method="post">
                        <input name="n" placeholder="Package Name"> <input name="d" placeholder="Days"> <input name="c" placeholder="Coins">
                        <button class="btn">Add Package</button>
                    </form>
                    {{% for p in pkgs %}}
                    <div style="display:flex; justify-content:space-between; padding:5px;">
                        <span>{{{{p.name}}}} - {{{{p.coins}}}} Coins</span> <a href="/admin/del/pkg/{{{{p._id}}}}" style="color:red;">[Del]</a>
                    </div>
                    {{% endfor %}}
                </section>
            </div>
        </body></html>
    """, conf=conf, movies=movies, cats=cats, l_tasks=l_tasks, a_tasks=a_tasks, pkgs=pkgs)

# অ্যাডমিন অ্যাকশন রাউটস
@app.route('/admin/update_settings', methods=['POST'])
def admin_up_settings():
    if 'admin' in session:
        settings_col.update_one({"key": "main_config"}, {"$set": {
            "site_name": request.form.get('sn'), "notice": request.form.get('nt'),
            "unlock_limit": int(request.form.get('ul')),
            "ep_zone_id": request.form.get('ez'), "task_zone_ids": request.form.get('tz')
        }})
    return redirect('/admin/dashboard')

@app.route('/admin/add_movie', methods=['POST'])
def admin_add_movie():
    if 'admin' in session:
        poster = request.files.get('poster')
        if poster:
            encoded = base64.b64encode(poster.read()).decode('utf-8')
            p_url = f"data:{poster.content_type};base64,{encoded}"
            eps = [e.strip() for e in request.form.get('episodes').split('\n') if e.strip()]
            movies_col.insert_one({"name": request.form.get('name'), "category": request.form.get('cat'), "poster": p_url, "episodes": eps, "created_at": datetime.utcnow()})
    return redirect('/admin/dashboard')

@app.route('/admin/add_task', methods=['POST'])
def admin_add_task():
    if 'admin' in session:
        t_type = request.form.get('type')
        data = {"name": request.form.get('n'), "coins": int(request.form.get('c'))}
        if t_type == "link": data['link'] = request.form.get('l'); link_tasks_col.insert_one(data)
        else: ad_tasks_col.insert_one(data)
    return redirect('/admin/dashboard')

@app.route('/admin/add_pkg', methods=['POST'])
def admin_add_pkg():
    if 'admin' in session:
        packages_col.insert_one({"name": request.form.get('n'), "days": int(request.form.get('d')), "coins": int(request.form.get('c'))})
    return redirect('/admin/dashboard')

@app.route('/admin/del/<type>/<id>')
def admin_delete(type, id):
    if 'admin' in session:
        col = movies_col if type == 'movie' else link_tasks_col if type == 'link' else ad_tasks_col if type == 'ad' else packages_col
        col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin/dashboard')

# ==========================================
# 🧭 নেভিগেশন মেনু
# ==========================================
def get_nav(active):
    return f"""<div class="bottom-nav">
        <a href="/" class="{'active' if active=='/' else ''}"><i class="fas fa-home"></i>Home</a>
        <a href="/tasks" class="{'active' if active=='/tasks' else ''}"><i class="fas fa-coins"></i>Earn</a>
        <a href="/premium" class="{'active' if active=='/premium' else ''}"><i class="fas fa-gem"></i>Premium</a>
        <a href="/profile" class="{'active' if active=='/profile' else ''}"><i class="fas fa-user"></i>Profile</a>
    </div>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
