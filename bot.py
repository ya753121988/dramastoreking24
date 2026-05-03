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
# ⚙️ কনফিগারেশন
# ==========================================
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

# ==========================================
# 🗄️ ডাটাবেস কানেকশন
# ==========================================
db_client = MongoClient(MONGO_URL)
db = db_client['UltimateMovieDB_Full']
movies_col = db['movies']
users_col = db['users']
link_tasks_col = db['link_tasks']
ad_tasks_col = db['ad_tasks']
packages_col = db['packages']
settings_col = db['settings']
categories_col = db['categories']

def init_settings():
    if not settings_col.find_one({"key": "site_config"}):
        settings_col.insert_one({
            "key": "site_config",
            "site_name": "Premium Drama Store",
            "notice": "🌟 আমাদের সাইটে স্বাগতম! মুভি দেখে কয়েন ইনকাম করুন।",
            "zone_ids": "10351894" # কমা দিয়ে একাধিক আইডি দেওয়া যাবে
        })
    if categories_col.count_documents({}) == 0:
        categories_col.insert_many([{"name": "Chinese Drama"}, {"name": "Korean Drama"}, {"name": "Action"}, {"name": "Romantic"}])

init_settings()

app = Flask(__name__)
app.secret_key = "ULTRA_PRO_MAX_SECRET_999"

# ==========================================
# 🎨 প্রিমিয়াম সিএসএস (Glassmorphism)
# ==========================================
STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    :root { --primary: #00d2ff; --secondary: #3a7bd5; --accent: #ff007a; --dark: #0b0e14; --card: #161b22; }
    * { box-sizing: border-box; font-family: 'Poppins', sans-serif; transition: 0.3s; }
    body { background: var(--dark); color: #e6edf3; margin: 0; padding-bottom: 90px; overflow-x: hidden; }
    
    header { background: linear-gradient(135deg, var(--primary), var(--secondary)); padding: 20px; text-align: center; font-size: 24px; font-weight: 700; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    .notice-bar { background: rgba(255, 193, 7, 0.1); color: #ffc107; padding: 10px; font-size: 13px; text-align: center; border-bottom: 1px solid #ffc107; }
    
    .container { width: 95%; max-width: 1200px; margin: auto; padding: 15px; }
    
    /* Movie UI */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; }
    @media (min-width: 768px) { .grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); } }
    
    .card { background: var(--card); border-radius: 15px; overflow: hidden; border: 1px solid #30363d; text-decoration: none; color: inherit; position: relative; }
    .card:hover { transform: translateY(-5px); border-color: var(--primary); }
    .card img { width: 100%; height: 240px; object-fit: cover; }
    .card-info { padding: 10px; text-align: center; font-weight: 600; font-size: 14px; }
    .cat-badge { position: absolute; top: 8px; left: 8px; background: var(--accent); color: white; padding: 3px 8px; border-radius: 5px; font-size: 10px; font-weight: bold; }

    /* Buttons */
    .btn { background: linear-gradient(90deg, var(--primary), var(--secondary)); color: white; padding: 12px; border-radius: 10px; text-decoration: none; display: block; text-align: center; border: none; font-weight: 600; cursor: pointer; margin: 10px 0; width: 100%; }
    .btn-red { background: linear-gradient(90deg, #ff416c, #ff4b2b); }
    .btn-green { background: linear-gradient(90deg, #1D976C, #93F9B9); color: #000; }

    /* Forms */
    input, select, textarea { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #30363d; background: #0d1117; color: white; margin-bottom: 15px; }
    
    /* Bottom Nav */
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: #161b22; display: flex; justify-content: space-around; padding: 12px 0; border-top: 1px solid #30363d; z-index: 1000; }
    .bottom-nav a { color: #8b949e; text-decoration: none; font-size: 12px; text-align: center; display: flex; flex-direction: column; }
    .bottom-nav a.active { color: var(--primary); font-weight: bold; }
    .bottom-nav i { font-size: 20px; margin-bottom: 4px; }

    /* Admin Tabs */
    .admin-menu { display: flex; overflow-x: auto; gap: 10px; margin-bottom: 20px; padding-bottom: 10px; }
    .admin-menu a { background: #21262d; color: white; padding: 10px 20px; border-radius: 20px; text-decoration: none; white-space: nowrap; font-size: 14px; border: 1px solid #30363d; }
    .admin-menu a.active { background: var(--primary); border-color: var(--primary); }
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
    if not user or 'premium_until' not in user: return False
    return user['premium_until'] > datetime.utcnow()

def get_random_ad():
    conf = settings_col.find_one({"key": "site_config"})
    zones = conf.get('zone_ids', '10351894').split(',')
    zid = random.choice(zones).strip()
    return f"<script src='//libtl.com/sdk.js' data-zone='{zid}' data-sdk='show_{zid}'></script>"

# ==========================================
# 🔐 ইউজার অথেনটিকেশন
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({"mobile": request.form.get('mobile')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['uid'] = str(user['_id']); return redirect('/')
        flash("❌ ভুল নম্বর বা পাসওয়ার্ড!")
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container'><h2>🔑 Login</h2><form method='post'><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>Login</button></form><a href='/register' style='color:gray;text-decoration:none;'>নতুন অ্যাকাউন্ট? রেজিস্ট্রেশন করুন</a></div></body></html>")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname, mobile, pwd = request.form.get('fname'), request.form.get('mobile'), request.form.get('password')
        if users_col.find_one({"mobile": mobile}): flash("❌ নম্বরটি ইতিমধ্যে ব্যবহৃত!")
        else:
            users_col.insert_one({"fname": fname, "mobile": mobile, "password": generate_password_hash(pwd), "coins": 0, "premium_until": datetime.utcnow()})
            return redirect('/login')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container'><h2>🚀 Register</h2><form method='post'><input name='fname' placeholder='Full Name' required><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>Register</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

# ==========================================
# 🏠 হোমপেজ (ইউজার সাইড)
# ==========================================
@app.route('/')
def index():
    user = get_user()
    if not user: return redirect('/login')
    conf = settings_col.find_one({"key": "site_config"})
    page = request.args.get('page', 1, type=int)
    cat_filter = request.args.get('cat')
    
    query = {"category": cat_filter} if cat_filter else {}
    total_movies = movies_col.count_documents(query)
    movies = list(movies_col.find(query).sort("_id", -1).skip((page-1)*30).limit(30))
    cats = list(categories_col.find())
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>{{{{conf['site_name']}}}}</title>{STYLE}</head><body>
            <header>{{{{conf['site_name']}}}}</header>
            <div class="notice-bar"><marquee>{{{{conf['notice']}}}}</marquee></div>
            <div class="container">
                <div style="overflow-x:auto; display:flex; gap:10px; margin-bottom:15px; scrollbar-width:none;">
                    <a href="/" class="btn" style="width:auto; padding:6px 15px; font-size:12px; background:{{{{'var(--primary)' if not request.args.get('cat') else '#21262d'}}}}">All</a>
                    {{% for c in cats %}}
                    <a href="/?cat={{{{c.name}}}}" class="btn" style="width:auto; padding:6px 15px; font-size:12px; background:{{{{'var(--primary)' if request.args.get('cat')==c.name else '#21262d'}}}}">{{{{c.name}}}}</a>
                    {{% endfor %}}
                </div>
                <div class="grid">
                    {{% for m in movies %}}
                    <a href="/movie/{{{{m._id}}}}" class="card">
                        <span class="cat-badge">{{{{m.category}}}}</span>
                        <img src="{{{{m.poster}}}}">
                        <div class="card-info">{{{{m.name}}}}</div>
                    </a>
                    {{% endfor %}}
                </div>
            </div>
            {get_nav('/')}
        </body></html>
    """, conf=conf, movies=movies, cats=cats)

@app.route('/movie/<id>')
def movie_detail(id):
    user = get_user()
    if not user: return redirect('/login')
    movie = movies_col.find_one({"_id": ObjectId(id)})
    ad_script = get_random_ad() if not is_premium(user) else ""
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>{{{{movie.name}}}}</header>
            <div class="container" style="text-align:center;">
                <img src="{{{{movie.poster}}}}" style="width:100%; max-width:400px; border-radius:15px; box-shadow: 0 5px 20px rgba(0,0,0,0.5);">
                <h3 style="margin-top:20px; text-align:left; border-left:4px solid var(--primary); padding-left:10px;">Episodes</h3>
                {{% for ep in movie.episodes %}}
                    <div style="margin-bottom:12px;">
                        {ad_script}
                        <a href="{{{{ep}}}}" class="btn">🚀 Play Episode {{{{loop.index}}}}</a>
                    </div>
                {{% endfor %}}
                <a href="/" class="btn btn-red" style="margin-top:20px;">Back to Home</a>
            </div>
        </body></html>
    """, movie=movie)

# ==========================================
# 💰 টাস্ক ও প্রিমিয়াম সিস্টেম (আগের সব ফিচারসহ)
# ==========================================
@app.route('/tasks')
def tasks():
    user = get_user()
    if not user: return redirect('/login')
    l_tasks = list(link_tasks_col.find())
    a_tasks = list(ad_tasks_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>💰 Earn Coins</header>
            <div class="container">
                <div class="card" style="padding:20px; text-align:center; background:linear-gradient(45deg, #161b22, #21262d);">
                    <span>Your Balance</span><br>
                    <span style="font-size:30px; color:var(--primary); font-weight:bold;">{{{{user.coins}}}} 🪙</span>
                </div>
                <h3>🔗 Link Tasks</h3>
                {{% for t in l_tasks %}}
                <div class="card" style="padding:15px; display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-left:5px solid var(--primary);">
                    <div><b>{{{{t.name}}}}</b><br><small>Reward: +{{{{t.coins}}}} Coins</small></div>
                    <a href="{{{{t.link}}}}" target="_blank" onclick="fetch('/claim/link/{{{{t._id}}}}')" class="btn" style="width:80px; margin:0;">Go</a>
                </div>
                {{% endfor %}}

                <h3>📺 Ad Tasks</h3>
                {{% for t in a_tasks %}}
                <div class="card" style="padding:15px; margin-bottom:10px; border-left:5px solid #ffc107;">
                    <b>{{{{t.name}}}}</b> (Reward: {{{{t.coins}}}})
                    <div id="ad-{{{{t._id}}}}"></div>
                    <button onclick="watchAd('{{{{t.zone_id}}}}', '{{{{t._id}}}}')" class="btn" style="background:#ffc107; color:black;">Watch Now</button>
                </div>
                {{% endfor %}}
            </div>
            <script>
                function watchAd(zid, tid) {{
                    document.getElementById('ad-'+tid).innerHTML = "<script src='//libtl.com/sdk.js' data-zone='"+zid+"' data-sdk='show_"+zid+"'><\/script>";
                    fetch('/claim/ad/'+tid);
                    alert("Ad loading... Coins will be added.");
                }}
            </script>
            {get_nav('/tasks')}
        </body></html>
    """, user=user, l_tasks=l_tasks, a_tasks=a_tasks)

@app.route('/claim/<type>/<tid>')
def claim_reward(type, tid):
    user = get_user()
    if not user: return "error"
    col = link_tasks_col if type == "link" else ad_tasks_col
    t = col.find_one({"_id": ObjectId(tid)})
    if t: users_col.update_one({"_id": user['_id']}, {"$inc": {"coins": int(t['coins'])}})
    return "ok"

@app.route('/premium')
def premium():
    user = get_user()
    if not user: return redirect('/login')
    pkgs = list(packages_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>💎 Premium Store</header>
            <div class="container">
                {{% for p in pkgs %}}
                <div class="card" style="padding:20px; text-align:center; border: 2px solid gold; margin-bottom:20px;">
                    <h2 style="color:gold; margin:0;">{{{{p.name}}}}</h2>
                    <p>{{{{p.days}}}} Days Premium Access</p>
                    <div style="font-size:20px; font-weight:bold;">Price: {{{{p.coins}}}} Coins</div>
                    <a href="/buy/{{{{p._id}}}}" class="btn" style="background:gold; color:black; margin-top:15px;">Activate Now</a>
                </div>
                {{% endfor %}}
            </div>
            {get_nav('/premium')}
        </body></html>
    """, pkgs=pkgs)

@app.route('/buy/<pid>')
def buy(pid):
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
            <header>👤 My Profile</header>
            <div class="container" style="text-align:center;">
                <div class="card" style="padding:30px;">
                    <i class="fas fa-user-circle" style="font-size:60px; color:var(--primary);"></i>
                    <h2>{{{{user.fname}}}}</h2>
                    <p>{{{{user.mobile}}}}</p>
                    <div style="padding:10px; border-radius:10px; background:#21262d;">
                        Status: {{{{ '🌟 Premium User' if user.premium_until > now else '🆓 Free User' }}}}
                    </div>
                </div>
                <a href="/logout" class="btn btn-red" style="margin-top:20px;">Logout Account</a>
            </div>
            {get_nav('/profile')}
        </body></html>
    """, user=user, now=datetime.utcnow())

# ==========================================
# ⚡ প্রিমিয়াম অ্যাডমিন প্যানেল (নতুন ম্যানুয়াল সিস্টেম)
# ==========================================
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'admin' in session: return redirect('/admin/movies')
    if request.method == 'POST' and request.form.get('pass') == ADMIN_PASS:
        session['admin'] = True; return redirect('/admin/movies')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container'><form method='post'><h2>Admin Access</h2><input type='password' name='pass' placeholder='Admin Password'><button class='btn'>Login</button></form></div></body></html>")

@app.route('/admin/movies', methods=['GET', 'POST'])
def admin_movies():
    if 'admin' not in session: return redirect('/admin')
    if request.method == 'POST':
        name = request.form.get('name')
        cat = request.form.get('cat')
        eps_raw = request.form.get('episodes').split('\n')
        poster_file = request.files.get('poster')
        
        if poster_file:
            encoded = base64.b64encode(poster_file.read()).decode('utf-8')
            poster_url = f"data:{poster_file.content_type};base64,{encoded}"
            movies_col.insert_one({
                "name": name, "category": cat, "poster": poster_url,
                "episodes": [e.strip() for e in eps_raw if e.strip()],
                "created_at": datetime.utcnow()
            })
            flash("✅ Movie Added Successfully!")
        return redirect('/admin/movies')
    
    movies = list(movies_col.find().sort("_id", -1))
    cats = list(categories_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>🛠 Admin Panel</header>
            <div class="container">
                {get_admin_nav('movies')}
                <form class="card" style="padding:20px;" method="post" enctype="multipart/form-data">
                    <h3>🎬 Add New Movie</h3>
                    <input name="name" placeholder="Movie Name" required>
                    <select name="cat">
                        {{% for c in cats %}}<option>{{{{c.name}}}}</option>{{% endfor %}}
                    </select>
                    <label>Poster Image (Gallery):</label>
                    <input type="file" name="poster" accept="image/*" required>
                    <label>Episode Links (One per line):</label>
                    <textarea name="episodes" rows="5" placeholder="https://link1.com&#10;https://link2.com"></textarea>
                    <button class="btn btn-green">Upload Movie</button>
                </form>

                <h3>Existing Movies</h3>
                {{% for m in movies %}}
                <div class="card" style="padding:10px; display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
                    <span>{{{{m.name}}}}</span>
                    <a href="/admin/delete/movie/{{{{m._id}}}}" style="color:red; text-decoration:none;">[Delete]</a>
                </div>
                {{% endfor %}}
            </div>
        </body></html>
    """, movies=movies, cats=cats)

@app.route('/admin/tasks', methods=['GET', 'POST'])
def admin_tasks():
    if 'admin' not in session: return redirect('/admin')
    if request.method == 'POST':
        action = request.form.get('action')
        if action == "link":
            link_tasks_col.insert_one({"name": request.form.get('n'), "link": request.form.get('l'), "coins": int(request.form.get('c'))})
        elif action == "ad":
            ad_tasks_col.insert_one({"name": request.form.get('n'), "zone_id": request.form.get('z'), "coins": int(request.form.get('c'))})
        return redirect('/admin/tasks')
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>🛠 Admin Tasks</header>
            <div class="container">
                {get_admin_nav('tasks')}
                <form class="card" style="padding:15px;" method="post">
                    <h4>Add Link Task</h4><input type="hidden" name="action" value="link">
                    <input name="n" placeholder="Task Name">
                    <input name="l" placeholder="Direct Link">
                    <input name="c" placeholder="Coins Reward">
                    <button class="btn">Add Link Task</button>
                </form>
                <form class="card" style="padding:15px;" method="post">
                    <h4>Add Ad Task</h4><input type="hidden" name="action" value="ad">
                    <input name="n" placeholder="Task Name">
                    <input name="z" placeholder="Monetag Zone ID">
                    <input name="c" placeholder="Coins Reward">
                    <button class="btn" style="background:#ffc107; color:black;">Add Ad Task</button>
                </form>
            </div>
        </body></html>
    """)

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if 'admin' not in session: return redirect('/admin')
    if request.method == 'POST':
        settings_col.update_one({"key": "site_config"}, {"$set": {
            "site_name": request.form.get('sn'),
            "notice": request.form.get('nt'),
            "zone_ids": request.form.get('zids')
        }})
        flash("Settings Updated!")
        return redirect('/admin/settings')
    
    conf = settings_col.find_one({"key": "site_config"})
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>⚙️ Site Settings</header>
            <div class="container">
                {get_admin_nav('settings')}
                <form class="card" style="padding:20px;" method="post">
                    Site Name: <input name="sn" value="{{{{conf['site_name']}}}}">
                    Notice: <textarea name="nt">{{{{conf['notice']}}}}</textarea>
                    Random Zone IDs (Comma separated):
                    <input name="zids" value="{{{{conf['zone_ids']}}}}">
                    <button class="btn">Save All Settings</button>
                </form>
            </div>
        </body></html>
    """, conf=conf)

@app.route('/admin/delete/<type>/<id>')
def delete_item(type, id):
    if 'admin' not in session: return redirect('/admin')
    if type == "movie": movies_col.delete_one({"_id": ObjectId(id)})
    return redirect(request.referrer)

def get_nav(active):
    return f"""
    <div class="bottom-nav">
        <a href="/" class="{'active' if active=='/' else ''}"><i class="fas fa-home"></i>Home</a>
        <a href="/tasks" class="{'active' if active=='/tasks' else ''}"><i class="fas fa-coins"></i>Earn</a>
        <a href="/premium" class="{'active' if active=='/premium' else ''}"><i class="fas fa-gem"></i>Premium</a>
        <a href="/profile" class="{'active' if active=='/profile' else ''}"><i class="fas fa-user-circle"></i>Profile</a>
    </div>
    """

def get_admin_nav(active):
    return f"""
    <div class="admin-menu">
        <a href="/admin/movies" class="{'active' if active=='movies' else ''}">Movies</a>
        <a href="/admin/tasks" class="{'active' if active=='tasks' else ''}">Tasks</a>
        <a href="/admin/settings" class="{'active' if active=='settings' else ''}">Settings</a>
        <a href="/logout">Logout Admin</a>
    </div>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
