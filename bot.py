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
db = db_client['UltimateMovieDB_Final']
movies_col = db['movies']
users_col = db['users']
link_tasks_col = db['link_tasks']
packages_col = db['packages']
settings_col = db['settings']
categories_col = db['categories']

def init_settings():
    if not settings_col.find_one({"key": "site_config"}):
        settings_col.insert_one({
            "key": "site_config",
            "site_name": "Premium Drama Store",
            "notice": "🌟 আমাদের সাইটে স্বাগতম! মুভি দেখে এবং টাস্ক পূরণ করে কয়েন ইনকাম করুন।",
            "ep_zone_id": "10351894", # ইপিসোড অ্যাড জোন
            "task_zone_ids": "10351895, 10351896, 10351897" # আনলিমিটেড টাস্ক জোন (কমা দিয়ে)
        })
    if categories_col.count_documents({}) == 0:
        categories_col.insert_many([{"name": "Chinese Drama"}, {"name": "Korean Drama"}, {"name": "Action"}, {"name": "Romantic"}])

init_settings()

app = Flask(__name__)
app.secret_key = "ULTRA_FINAL_SECRET_2024"

# ==========================================
# 🎨 প্রিমিয়াম সিএসএস (Modern Dark Glass)
# ==========================================
STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    :root { --primary: #00d2ff; --secondary: #3a7bd5; --accent: #ff007a; --dark: #0b0e14; --card: #161b22; }
    * { box-sizing: border-box; font-family: 'Poppins', sans-serif; transition: 0.3s; }
    body { background: var(--dark); color: #e6edf3; margin: 0; padding-bottom: 90px; }
    
    header { background: linear-gradient(135deg, var(--primary), var(--secondary)); padding: 20px; text-align: center; font-size: 22px; font-weight: 700; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    .notice-bar { background: rgba(255, 193, 7, 0.1); color: #ffc107; padding: 10px; font-size: 13px; text-align: center; border-bottom: 1px solid #ffc107; }
    
    .container { width: 95%; max-width: 1200px; margin: auto; padding: 15px; }
    
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; }
    @media (min-width: 768px) { .grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); } }
    
    .card { background: var(--card); border-radius: 15px; overflow: hidden; border: 1px solid #30363d; text-decoration: none; color: inherit; position: relative; }
    .card img { width: 100%; height: 230px; object-fit: cover; }
    .card-info { padding: 10px; text-align: center; font-weight: 600; font-size: 13px; }
    .cat-badge { position: absolute; top: 8px; left: 8px; background: var(--accent); color: white; padding: 3px 8px; border-radius: 5px; font-size: 10px; font-weight: bold; }

    .btn { background: linear-gradient(90deg, var(--primary), var(--secondary)); color: white; padding: 12px; border-radius: 10px; text-decoration: none; display: block; text-align: center; border: none; font-weight: 600; cursor: pointer; margin: 10px 0; width: 100%; }
    .btn-red { background: linear-gradient(90deg, #ff416c, #ff4b2b); }
    .btn-green { background: linear-gradient(90deg, #1D976C, #93F9B9); color: #000; }

    input, select, textarea { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #30363d; background: #0d1117; color: white; margin-bottom: 15px; }
    
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: #161b22; display: flex; justify-content: space-around; padding: 12px 0; border-top: 1px solid #30363d; z-index: 1000; }
    .bottom-nav a { color: #8b949e; text-decoration: none; font-size: 12px; text-align: center; display: flex; flex-direction: column; }
    .bottom-nav a.active { color: var(--primary); font-weight: bold; }
    .bottom-nav i { font-size: 20px; margin-bottom: 4px; }

    .admin-menu { display: flex; overflow-x: auto; gap: 10px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #333; }
    .admin-menu a { background: #21262d; color: white; padding: 8px 18px; border-radius: 20px; text-decoration: none; white-space: nowrap; font-size: 13px; border: 1px solid #30363d; }
    .admin-menu a.active { background: var(--primary); }
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

# ==========================================
# 🔐 অথেনটিকেশন
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({"mobile": request.form.get('mobile')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['uid'] = str(user['_id']); return redirect('/')
        flash("❌ ভুল মোবাইল বা পাসওয়ার্ড!")
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container' style='max-width:400px; margin-top:50px;'><h2>🔑 Login</h2><form method='post'><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>Login</button></form><a href='/register' style='color:gray;text-decoration:none;'>অ্যাকাউন্ট নেই? রেজিস্ট্রেশন করুন</a></div></body></html>")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname, mobile, pwd = request.form.get('fname'), request.form.get('mobile'), request.form.get('password')
        if not users_col.find_one({"mobile": mobile}):
            users_col.insert_one({"fname": fname, "mobile": mobile, "password": generate_password_hash(pwd), "coins": 0, "premium_until": datetime.utcnow()})
            return redirect('/login')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container' style='max-width:400px; margin-top:50px;'><h2>🚀 Register</h2><form method='post'><input name='fname' placeholder='Full Name' required><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>Register</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

# ==========================================
# 🏠 ইউজার প্যানেল (হোম ও মুভি)
# ==========================================
@app.route('/')
def index():
    user = get_user()
    if not user: return redirect('/login')
    conf = settings_col.find_one({"key": "site_config"})
    cat_filter = request.args.get('cat')
    query = {"category": cat_filter} if cat_filter else {}
    movies = list(movies_col.find(query).sort("_id", -1))
    cats = list(categories_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>{{{{conf['site_name']}}}}</header>
            <div class="notice-bar"><marquee>{{{{conf['notice']}}}}</marquee></div>
            <div class="container">
                <div style="overflow-x:auto; display:flex; gap:10px; margin-bottom:15px; scrollbar-width:none;">
                    <a href="/" class="btn" style="width:auto; padding:6px 15px; font-size:12px; background:{{{{'var(--primary)' if not cat_filter else '#21262d'}}}}">All</a>
                    {{% for c in cats %}}
                    <a href="/?cat={{{{c.name}}}}" class="btn" style="width:auto; padding:6px 15px; font-size:12px; background:{{{{'var(--primary)' if cat_filter==c.name else '#21262d'}}}}">{{{{c.name}}}}</a>
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
    """, conf=conf, movies=movies, cats=cats, cat_filter=cat_filter)

@app.route('/movie/<id>')
def movie_detail(id):
    user = get_user()
    if not user: return redirect('/login')
    movie = movies_col.find_one({"_id": ObjectId(id)})
    conf = settings_col.find_one({"key": "site_config"})
    
    # ইপিসোড অ্যাড লজিক (ইপিসোড জোন আইডি ব্যবহার করে)
    ep_zid = conf.get('ep_zone_id', '10351894')
    ad_script = f"<script src='//libtl.com/sdk.js' data-zone='{ep_zid}' data-sdk='show_{ep_zid}'></script>" if not is_premium(user) else ""
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>{{{{movie.name}}}}</header>
            <div class="container" style="text-align:center;">
                <img src="{{{{movie.poster}}}}" style="width:100%; max-width:400px; border-radius:15px;">
                <h3 style="text-align:left; border-left:4px solid var(--primary); padding-left:10px; margin-top:20px;">All Episodes</h3>
                {{% for ep in movie.episodes %}}
                    <div style="margin-bottom:15px;">
                        {ad_script}
                        <a href="{{{{ep}}}}" class="btn">▶️ Play Episode {{{{loop.index}}}}</a>
                    </div>
                {{% endfor %}}
            </div>
        </body></html>
    """, movie=movie)

# ==========================================
# 💰 টাস্ক সিস্টেম (আনলিমিটেড জোন আইডি অ্যাডস)
# ==========================================
@app.route('/tasks')
def tasks():
    user = get_user()
    if not user: return redirect('/login')
    conf = settings_col.find_one({"key": "site_config"})
    l_tasks = list(link_tasks_col.find())
    
    # টাস্ক জোন আইডি লিস্ট প্রসেসিং
    task_zones = conf.get('task_zone_ids', '10351894').split(',')
    task_zones = [z.strip() for z in task_zones]

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>💰 Task Center</header>
            <div class="container">
                <div class="card" style="padding:20px; text-align:center; background:linear-gradient(45deg, #161b22, #21262d);">
                    <span>My Balance</span><br>
                    <span style="font-size:30px; color:var(--primary); font-weight:bold;">{{{{user.coins}}}} 🪙</span>
                </div>

                <h3>🔗 Click Links</h3>
                {{% for t in l_tasks %}}
                <div class="card" style="padding:15px; display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-left:5px solid var(--primary);">
                    <div><b>{{{{t.name}}}}</b><br><small>+{{{{t.coins}}}} Coins</small></div>
                    <a href="{{{{t.link}}}}" target="_blank" onclick="fetch('/claim/link/{{{{t._id}}}}')" class="btn" style="width:70px; margin:0; padding:8px;">Go</a>
                </div>
                {{% endfor %}}

                <h3>📺 Watch Ads (Unlimited)</h3>
                <p style="font-size:12px; color:gray;">প্রতিটি অ্যাড দেখলে ৫ কয়েন করে পাবেন।</p>
                <div id="ad-container"></div>
                <button onclick="watchTaskAd()" class="btn btn-green">Watch Ad & Earn Coins</button>
            </div>
            
            <script>
                const zones = {task_zones};
                function watchTaskAd() {{
                    // র্যান্ডমলি একটি জোন আইডি সিলেক্ট করা
                    const zid = zones[Math.floor(Math.random() * zones.length)];
                    const container = document.getElementById('ad-container');
                    container.innerHTML = "";
                    
                    const s = document.createElement('script');
                    s.src = '//libtl.com/sdk.js';
                    s.setAttribute('data-zone', zid);
                    s.setAttribute('data-sdk', 'show_'+zid);
                    container.appendChild(s);
                    
                    fetch('/claim/ad/task').then(() => console.log("Coins Added"));
                    alert("Ad is loading... Please wait and watch to earn coins.");
                }}
            </script>
            {get_nav('/tasks')}
        </body></html>
    """, user=user, l_tasks=l_tasks, task_zones=task_zones)

@app.route('/claim/<type>/<tid>')
def claim(type, tid):
    user = get_user()
    if not user: return "error"
    if type == "link":
        t = link_tasks_col.find_one({"_id": ObjectId(tid)})
        if t: users_col.update_one({"_id": user['_id']}, {"$inc": {"coins": int(t['coins'])}})
    elif type == "ad":
        users_col.update_one({"_id": user['_id']}, {"$inc": {"coins": 5}}) # অ্যাড রিওয়ার্ড ৫
    return "ok"

# ==========================================
# 💎 প্রিমিয়াম ও প্রোফাইল
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
                <div class="card" style="padding:20px; text-align:center; border: 2px solid gold; margin-bottom:20px;">
                    <h2 style="color:gold;">{{{{p.name}}}}</h2>
                    <p>{{{{p.days}}}} Days - No Ads - Fast Loading</p>
                    <div style="font-size:22px; font-weight:bold;">Price: {{{{p.coins}}}} Coins</div>
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
            <header>👤 User Profile</header>
            <div class="container" style="text-align:center;">
                <div class="card" style="padding:30px;">
                    <i class="fas fa-user-circle" style="font-size:60px; color:var(--primary); margin-bottom:15px;"></i>
                    <h2>{{{{user.fname}}}}</h2>
                    <p>Mobile: {{{{user.mobile}}}}</p>
                    <p>Balance: {{{{user.coins}}}} 🪙</p>
                    <div style="padding:10px; border-radius:10px; background:#21262d;">
                        Status: {{{{ '🌟 Premium' if user.premium_until > now else '🆓 Free' }}}}
                    </div>
                </div>
                <a href="/logout" class="btn btn-red" style="margin-top:20px;">Logout</a>
            </div>
            {get_nav('/profile')}
        </body></html>
    """, user=user, now=datetime.utcnow())

# ==========================================
# ⚡ প্রিমিয়াম অ্যাডমিন প্যানেল (Full Manual)
# ==========================================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        if request.method == 'POST' and request.form.get('pass') == ADMIN_PASS:
            session['admin'] = True; return redirect('/admin')
        return render_template_string(f"<html><body style='background:#0b0e14; color:white; padding:50px; text-align:center;'><form method='post'><h2>Admin Login</h2><input type='password' name='pass' style='padding:12px; border-radius:8px;'><button class='btn' style='max-width:200px; margin:20px auto;'>Login</button></form></body></html>")
    
    # হ্যান্ডলিং বিভিন্ন পোস্ট রিকোয়েস্ট
    if request.method == 'POST':
        act = request.form.get('action')
        if act == "add_movie":
            poster = request.files.get('poster')
            if poster:
                encoded = base64.b64encode(poster.read()).decode('utf-8')
                p_url = f"data:{poster.content_type};base64,{encoded}"
                eps = [e.strip() for e in request.form.get('episodes').split('\n') if e.strip()]
                movies_col.insert_one({"name": request.form.get('name'), "category": request.form.get('cat'), "poster": p_url, "episodes": eps, "created_at": datetime.utcnow()})
        elif act == "update_settings":
            settings_col.update_one({"key": "site_config"}, {"$set": {
                "site_name": request.form.get('sn'), "notice": request.form.get('nt'),
                "ep_zone_id": request.form.get('ep_zid'), "task_zone_ids": request.form.get('task_zids')
            }})
        elif act == "add_link":
            link_tasks_col.insert_one({"name": request.form.get('n'), "link": request.form.get('l'), "coins": int(request.form.get('c'))})
        elif act == "add_pkg":
            packages_col.insert_one({"name": request.form.get('n'), "days": int(request.form.get('d')), "coins": int(request.form.get('c'))})
        return redirect('/admin')

    conf = settings_col.find_one({"key": "site_config"})
    movies = list(movies_col.find().sort("_id", -1))
    cats = list(categories_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>🛠 Admin Dashboard</header>
            <div class="container">
                <div class="admin-menu">
                    <a href="#movies">Movies</a> <a href="#tasks">Tasks</a> <a href="#settings">Settings</a> <a href="/logout">Logout</a>
                </div>

                <section id="settings" class="card" style="padding:20px; margin-bottom:20px;">
                    <h3>⚙️ Site Settings</h3>
                    <form method="post"><input type="hidden" name="action" value="update_settings">
                        Site Name: <input name="sn" value="{{{{conf['site_name']}}}}">
                        Notice: <input name="nt" value="{{{{conf['notice']}}}}">
                        <b>Episode Ad Zone ID:</b> <input name="ep_zid" value="{{{{conf['ep_zone_id']}}}}">
                        <b>Task Ad Zone IDs (Comma Separated):</b> <input name="task_zids" value="{{{{conf['task_zone_ids']}}}}">
                        <button class="btn">Update Config</button>
                    </form>
                </section>

                <section id="movies" class="card" style="padding:20px; margin-bottom:20px;">
                    <h3>🎬 Add New Movie</h3>
                    <form method="post" enctype="multipart/form-data"><input type="hidden" name="action" value="add_movie">
                        <input name="name" placeholder="Movie Name" required>
                        <select name="cat">
                            {{% for c in cats %}}<option>{{{{c.name}}}}</option>{{% endfor %}}
                        </select>
                        Poster Image: <input type="file" name="poster" accept="image/*" required>
                        Episode Links (One per line):
                        <textarea name="episodes" rows="5" placeholder="https://link1.com&#10;https://link2.com"></textarea>
                        <button class="btn btn-green">Upload Movie</button>
                    </form>
                    <hr>
                    <h4>Recent Movies</h4>
                    {{% for m in movies %}}
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span>{{{{m.name}}}}</span> <a href="/admin/delete/movie/{{{{m._id}}}}" style="color:red;">[Del]</a>
                    </div>
                    {{% endfor %}}
                </section>
                
                <section id="tasks" class="card" style="padding:20px;">
                    <h3>🔗 Link Tasks</h3>
                    <form method="post"><input type="hidden" name="action" value="add_link">
                        <input name="n" placeholder="Name"> <input name="l" placeholder="Link"> <input name="c" placeholder="Coins">
                        <button class="btn">Add Link Task</button>
                    </form>
                </section>
            </div>
        </body></html>
    """, conf=conf, movies=movies, cats=cats)

@app.route('/admin/delete/<type>/<id>')
def delete(type, id):
    if 'admin' in session:
        if type == "movie": movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

def get_nav(active):
    return f"""
    <div class="bottom-nav">
        <a href="/" class="{'active' if active=='/' else ''}"><i class="fas fa-home"></i>Home</a>
        <a href="/tasks" class="{'active' if active=='/tasks' else ''}"><i class="fas fa-coins"></i>Earn</a>
        <a href="/premium" class="{'active' if active=='/premium' else ''}"><i class="fas fa-gem"></i>Premium</a>
        <a href="/profile" class="{'active' if active=='/profile' else ''}"><i class="fas fa-user"></i>Profile</a>
    </div>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
