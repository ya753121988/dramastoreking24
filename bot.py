import os
import random
import base64
import math
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# ⚙️ কনফিগারেশন ও ডাটাবেস
# ==========================================
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

client = MongoClient(MONGO_URL)
db = client['Ultimate_Mega_DB']
movies_col = db['movies']
users_col = db['users']
link_tasks_col = db['link_tasks']
ad_tasks_col = db['ad_tasks']
packages_col = db['packages']
settings_col = db['settings']
categories_col = db['categories']
unlock_logs = db['unlock_logs'] # মুভি আনলক ট্র্যাকিং

def init_db():
    if not settings_col.find_one({"key": "config"}):
        settings_col.insert_one({
            "key": "config",
            "site_name": "Premium Drama Store",
            "notice": "🌟 ৫টি অ্যাড দেখে মুভি আনলক করুন!",
            "unlock_limit": 5,
            "ep_zone_id": "10351894",
            "task_zone_ids": "10351894, 10351895, 10351896"
        })
    if categories_col.count_documents({}) == 0:
        categories_col.insert_many([{"name": "Chinese Drama"}, {"name": "Korean Drama"}, {"name": "Action"}])

init_db()

app = Flask(__name__)
app.secret_key = "SUPER_ULTRA_SECRET_FINAL"

# ==========================================
# 🎨 প্রিমিয়াম সিএসএস (বিন্দুমাত্র কমতি নেই)
# ==========================================
STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    :root { --primary: #00d2ff; --secondary: #3a7bd5; --accent: #ff007a; --dark: #0b0e14; --card: rgba(22, 27, 34, 0.8); }
    * { box-sizing: border-box; font-family: 'Poppins', sans-serif; transition: 0.3s; }
    body { background: var(--dark); color: #e6edf3; margin: 0; padding-bottom: 90px; }
    
    header { background: linear-gradient(135deg, var(--primary), var(--secondary)); padding: 20px; text-align: center; font-size: 22px; font-weight: 700; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
    .container { width: 95%; max-width: 1200px; margin: auto; padding: 15px; }
    
    .card { background: var(--card); backdrop-filter: blur(10px); border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); padding: 15px; margin-bottom: 15px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
    .movie-card { background: #161b22; border-radius: 12px; overflow: hidden; border: 1px solid #30363d; text-decoration: none; color: white; position: relative; }
    .movie-card img { width: 100%; height: 220px; object-fit: cover; }
    .movie-card .info { padding: 8px; text-align: center; font-size: 12px; font-weight: 600; }
    .cat-tag { position: absolute; top: 5px; left: 5px; background: var(--accent); font-size: 10px; padding: 2px 8px; border-radius: 5px; }

    .btn { background: linear-gradient(90deg, var(--primary), var(--secondary)); color: white; padding: 12px; border-radius: 10px; border: none; cursor: pointer; text-decoration: none; display: block; text-align: center; font-weight: 600; width: 100%; margin: 10px 0; }
    .btn-unlock { background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%); }
    .btn-red { background: linear-gradient(90deg, #ff416c, #ff4b2b); }
    
    input, select, textarea { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #30363d; background: #0d1117; color: white; margin-bottom: 15px; }
    
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: rgba(22, 27, 34, 0.95); display: flex; justify-content: space-around; padding: 12px 0; border-top: 1px solid #30363d; z-index: 1000; }
    .bottom-nav a { color: #8b949e; text-decoration: none; font-size: 12px; text-align: center; }
    .bottom-nav a.active { color: var(--primary); }
    
    .admin-sidebar { background: #161b22; padding: 15px; border-radius: 10px; margin-bottom: 20px; display: flex; overflow-x: auto; gap: 10px; }
    .admin-sidebar a { white-space: nowrap; padding: 8px 15px; background: #21262d; color: white; border-radius: 20px; text-decoration: none; font-size: 13px; }
    .admin-sidebar a.active { background: var(--primary); }
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
    return user and user.get('premium_until') and user['premium_until'] > datetime.utcnow()

# ==========================================
# 🎬 ইউজার ইন্টারফেস (হোম ও মুভি ডিটেইলস)
# ==========================================
@app.route('/')
def index():
    user = get_user()
    if not user: return redirect('/login')
    conf = settings_col.find_one({"key": "config"})
    movies = list(movies_col.find().sort("_id", -1))
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>{{{{conf['site_name']}}}}</header>
            <div class="container">
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
    """, conf=conf, movies=movies)

@app.route('/movie/<id>')
def movie_detail(id):
    user = get_user()
    if not user: return redirect('/login')
    movie = movies_col.find_one({"_id": ObjectId(id)})
    conf = settings_col.find_one({"key": "config"})
    
    # আনলক ট্র্যাকিং
    log = unlock_logs.find_one({"uid": user['_id'], "mid": movie['_id']})
    watched = log['count'] if log else 0
    limit = int(conf['unlock_limit'])
    
    is_unlocked = watched >= limit or is_premium(user)

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>{{{{movie.name}}}}</header>
            <div class="container" style="text-align:center;">
                <img src="{{{{movie.poster}}}}" style="width:100%; max-width:400px; border-radius:15px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                
                {{% if is_unlocked %}}
                    <h3 style="color:var(--primary); margin-top:20px;">✅ Movie Unlocked</h3>
                    {{% for ep in movie.episodes %}}
                        <a href="{{{{ep}}}}" class="btn">🚀 Episode {{{{loop.index}}}}</a>
                    {{% endfor %}}
                {{% else %}}
                    <div class="card" style="margin-top:20px; border: 1px solid var(--accent);">
                        <h3>🔒 Episodes Locked</h3>
                        <p>Watch <b>{{{{limit}}}}</b> ads to unlock this content.</p>
                        <div style="background:#000; padding:10px; border-radius:10px; margin-bottom:10px;">
                            Watched: {{{{watched}}}} / {{{{limit}}}}
                        </div>
                        <div id="ad-box"></div>
                        <button class="btn btn-unlock" onclick="loadUnlockAd()">Watch Ad to Unlock</button>
                    </div>
                {{% endif %}}
                <a href="/" class="btn btn-red">Back to Home</a>
            </div>
            <script>
                function loadUnlockAd() {{
                    const zid = "{{{{conf['ep_zone_id']}}}}";
                    const box = document.getElementById('ad-box');
                    box.innerHTML = "";
                    const s = document.createElement('script');
                    s.src = '//libtl.com/sdk.js';
                    s.setAttribute('data-zone', zid);
                    s.setAttribute('data-sdk', 'show_'+zid);
                    box.appendChild(s);
                    fetch('/track/{{{{movie._id}}}}').then(() => {{
                        setTimeout(() => {{ location.reload(); }}, 5000);
                    }});
                }}
            </script>
        </body></html>
    """, movie=movie, is_unlocked=is_unlocked, watched=watched, limit=limit, conf=conf)

@app.route('/track/<mid>')
def track_unlock(mid):
    user = get_user()
    if user:
        unlock_logs.update_one({"uid": user['_id'], "mid": ObjectId(mid)}, {"$inc": {"count": 1}}, upsert=True)
    return "ok"

# ==========================================
# 💰 টাস্ক সিস্টেম (আনলিমিটেড জোন আইডি ফিক্স)
# ==========================================
@app.route('/tasks')
def tasks():
    user = get_user()
    if not user: return redirect('/login')
    conf = settings_col.find_one({"key": "config"})
    l_tasks = list(link_tasks_col.find())
    a_tasks = list(ad_tasks_col.find())
    z_ids = [z.strip() for z in conf['task_zone_ids'].split(',')]

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>💰 Earn Center</header>
            <div class="container">
                <div class="card" style="text-align:center;">
                    <span style="font-size:14px; color:gray;">My Balance</span><br>
                    <span style="font-size:28px; color:var(--primary); font-weight:bold;">{{{{user.coins}}}} 🪙</span>
                </div>
                
                <h3>🔗 Link Tasks</h3>
                {{% for t in l_tasks %}}
                <div class="card" style="display:flex; justify-content:space-between; align-items:center;">
                    <span><b>{{{{t.name}}}}</b><br><small>+{{{{t.coins}}}} Coins</small></span>
                    <a href="{{{{t.link}}}}" target="_blank" onclick="fetch('/claim/link/{{{{t._id}}}}')" class="btn" style="width:80px; margin:0;">Go</a>
                </div>
                {{% endfor %}}

                <h3>📺 Video Ads</h3>
                {{% for t in a_tasks %}}
                <div class="card">
                    <b>{{{{t.name}}}} (+{{{{t.coins}}}} 🪙)</b>
                    <div id="ad-{{{{t._id}}}}"></div>
                    <button class="btn btn-unlock" onclick="watchTaskAd('{{{{t._id}}}}')">Watch Video</button>
                </div>
                {{% endfor %}}
            </div>
            <script>
                const zones = {z_ids};
                function watchTaskAd(tid) {{
                    const zid = zones[Math.floor(Math.random() * zones.length)];
                    const box = document.getElementById('ad-'+tid);
                    box.innerHTML = "";
                    const s = document.createElement('script');
                    s.src = '//libtl.com/sdk.js';
                    s.setAttribute('data-zone', zid);
                    s.setAttribute('data-sdk', 'show_'+zid);
                    box.appendChild(s);
                    fetch('/claim/ad/'+tid);
                    alert("Ad Loading... Please watch to earn coins.");
                }}
            </script>
            {get_nav('/tasks')}
        </body></html>
    """, user=user, l_tasks=l_tasks, a_tasks=a_tasks)

@app.route('/claim/<type>/<tid>')
def claim(type, tid):
    user = get_user()
    if not user: return "err"
    col = link_tasks_col if type == 'link' else ad_tasks_col
    t = col.find_one({"_id": ObjectId(tid)})
    if t: users_col.update_one({"_id": user['_id']}, {"$inc": {"coins": int(t['coins'])}})
    return "ok"

# ==========================================
# ⚡ অ্যাডমিন প্যানেল (ফুল প্রিমিয়াম ও ডিলিট ফিক্স)
# ==========================================
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if 'admin' not in session:
        if request.method == 'POST' and request.form.get('p') == ADMIN_PASS:
            session['admin'] = True; return redirect('/admin')
        return "<html><body style='background:#0b0e14;color:white;padding:50px;text-align:center;'><form method='post'><h2>Admin Access</h2><input type='password' name='p'><button>Login</button></form></body></html>"
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == "add_movie":
            poster = request.files.get('poster')
            if poster:
                encoded = base64.b64encode(poster.read()).decode('utf-8')
                p_url = f"data:{poster.content_type};base64,{encoded}"
                eps = [e.strip() for e in request.form.get('episodes').split('\n') if e.strip()]
                movies_col.insert_one({"name": request.form.get('name'), "category": request.form.get('cat'), "poster": p_url, "episodes": eps, "created_at": datetime.utcnow()})
        elif action == "update_settings":
            settings_col.update_one({"key": "config"}, {"$set": {
                "site_name": request.form.get('sn'), "notice": request.form.get('nt'),
                "unlock_limit": int(request.form.get('ul')),
                "ep_zone_id": request.form.get('ez'), "task_zone_ids": request.form.get('tz')
            }})
        elif action == "add_link":
            link_tasks_col.insert_one({"name": request.form.get('n'), "link": request.form.get('l'), "coins": int(request.form.get('c'))})
        elif action == "add_ad":
            ad_tasks_col.insert_one({"name": request.form.get('n'), "coins": int(request.form.get('c'))})
        return redirect('/admin')

    conf = settings_col.find_one({"key": "config"})
    movies = list(movies_col.find().sort("_id", -1))
    cats = list(categories_col.find())
    l_tasks = list(link_tasks_col.find())
    a_tasks = list(ad_tasks_col.find())

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>🛠 Master Admin</header>
            <div class="container">
                <div class="admin-sidebar">
                    <a href="#settings">Settings</a> <a href="#movies">Movies</a> <a href="#tasks">Tasks</a> <a href="/logout">Logout</a>
                </div>

                <section id="settings" class="card">
                    <h3>⚙️ Site Configuration</h3>
                    <form method="post"><input type="hidden" name="action" value="update_settings">
                        Site Name: <input name="sn" value="{{{{conf['site_name']}}}}">
                        Notice: <input name="nt" value="{{{{conf['notice']}}}}">
                        Unlock Ad Limit: <input name="ul" type="number" value="{{{{conf['unlock_limit']}}}}">
                        Episode Ad Zone ID: <input name="ez" value="{{{{conf['ep_zone_id']}}}}">
                        Task Ad Zone IDs (Comma separated): <input name="tz" value="{{{{conf['task_zone_ids']}}}}">
                        <button class="btn">Save Config</button>
                    </form>
                </section>

                <section id="movies" class="card">
                    <h3>🎬 Add Movie (Manual)</h3>
                    <form method="post" enctype="multipart/form-data"><input type="hidden" name="action" value="add_movie">
                        <input name="name" placeholder="Movie Name" required>
                        <select name="cat">
                            {{% for c in cats %}}<option>{{{{c.name}}}}</option>{{% endfor %}}
                        </select>
                        Poster Image: <input type="file" name="poster" accept="image/*" required>
                        Episode Links (One per line):
                        <textarea name="episodes" rows="5" placeholder="Paste links here..."></textarea>
                        <button class="btn btn-unlock">Upload Movie</button>
                    </form>
                    <hr>
                    {{% for m in movies %}}
                    <div style="display:flex; justify-content:space-between; padding:5px; border-bottom:1px solid #333;">
                        <span>{{{{m.name}}}}</span> <a href="/admin/del/movie/{{{{m._id}}}}" style="color:red;">Del</a>
                    </div>
                    {{% endfor %}}
                </section>

                <section id="tasks" class="card">
                    <h3>🔗 Manage Tasks</h3>
                    <form method="post"><input type="hidden" name="action" value="add_link">
                        <input name="n" placeholder="Link Task Name"> <input name="l" placeholder="Link"> <input name="c" placeholder="Coins">
                        <button class="btn">Add Link Task</button>
                    </form>
                    {{% for t in l_tasks %}}
                    <div style="display:flex; justify-content:space-between; padding:5px;">
                        <span>{{{{t.name}}}}</span> <a href="/admin/del/link/{{{{t._id}}}}" style="color:red;">Del</a>
                    </div>
                    {{% endfor %}}
                    <hr>
                    <form method="post"><input type="hidden" name="action" value="add_ad">
                        <input name="n" placeholder="Ad Task Name"> <input name="c" placeholder="Coins">
                        <button class="btn" style="background:orange;">Add Ad Task</button>
                    </form>
                    {{% for t in a_tasks %}}
                    <div style="display:flex; justify-content:space-between; padding:5px;">
                        <span>{{{{t.name}}}}</span> <a href="/admin/del/ad/{{{{t._id}}}}" style="color:red;">Del</a>
                    </div>
                    {{% endfor %}}
                </section>
            </div>
        </body></html>
    """, conf=conf, movies=movies, cats=cats, l_tasks=l_tasks, a_tasks=a_tasks)

@app.route('/admin/del/<type>/<id>')
def admin_delete(type, id):
    if 'admin' in session:
        col = movies_col if type == 'movie' else link_tasks_col if type == 'link' else ad_tasks_col
        col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

# ==========================================
# 🔐 লগইন ও রেজিস্ট্রেশন
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = users_col.find_one({"mobile": request.form.get('m')})
        if u and check_password_hash(u['password'], request.form.get('p')):
            session['uid'] = str(u['_id']); return redirect('/')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container' style='max-width:400px;margin-top:50px;'><h2>🔑 Login</h2><form method='post'><input name='m' placeholder='Mobile'><input type='password' name='p' placeholder='Password'><button class='btn'>Login</button></form><a href='/register' style='color:gray;'>Register Account</a></div></body></html>")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users_col.insert_one({"fname": request.form.get('n'), "mobile": request.form.get('m'), "password": generate_password_hash(request.form.get('p')), "coins": 0, "premium_until": datetime.utcnow()})
        return redirect('/login')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container' style='max-width:400px;margin-top:50px;'><h2>🚀 Register</h2><form method='post'><input name='n' placeholder='Full Name'><input name='m' placeholder='Mobile'><input type='password' name='p' placeholder='Password'><button class='btn'>Create Account</button></form></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

def get_nav(active):
    return f"""<div class="bottom-nav">
        <a href="/" class="{'active' if active=='/' else ''}"><i class="fas fa-home"></i><br>Home</a>
        <a href="/tasks" class="{'active' if active=='/tasks' else ''}"><i class="fas fa-coins"></i><br>Earn</a>
        <a href="/admin" style="color:gray;"><i class="fas fa-lock"></i><br>Admin</a>
    </div>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
