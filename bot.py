import os
import threading
import math
import time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# ==========================================
# ⚙️ কনফিগারেশন (ENVIRONMENT VARIABLES)
# ==========================================
API_ID = int(os.getenv("API_ID", "29904834"))
API_HASH = os.getenv("API_HASH", "8b4fd9ef578af114502feeafa2d31938")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8655043839:AAFSI7Tqk6bftnVNqtBB-kRdbFDmr8b3Lf0")
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7120801813"))
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

# ==========================================
# 🗄️ ডাটাবেস কানেকশন ও সেটিংস
# ==========================================
db_client = MongoClient(MONGO_URL)
db = db_client['UltimateMovieDB']
movies_col = db['movies']
users_col = db['users']
link_tasks_col = db['link_tasks']
ad_tasks_col = db['ad_tasks']
packages_col = db['packages']
settings_col = db['settings']
task_logs_col = db['task_logs'] # ডেইলি লিমিট ট্র্যাকিং এর জন্য

def init_settings():
    if not settings_col.find_one({"key": "site_config"}):
        settings_col.insert_one({
            "key": "site_config",
            "site_name": "Premium Drama Store",
            "notice": "🌟 আমাদের সাইটে স্বাগতম! টাস্ক পূরণ করে প্রিমিয়াম মুভি উপভোগ করুন।",
            "zone_id": "10351894"
        })

init_settings()

app = Flask(__name__)
app.secret_key = "ULTRA_PRO_SECRET_KEY_999"

# ==========================================
# 🎨 আল্ট্রা প্রিমিয়াম সিএসএস (Glassmorphism UI)
# ==========================================
STYLE = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    :root { --primary: #00d2ff; --secondary: #3a7bd5; --dark-bg: #0b0e14; --card-bg: #161b22; --text: #e6edf3; }
    * { box-sizing: border-box; font-family: 'Poppins', sans-serif; transition: 0.3s; }
    body { background-color: var(--dark-bg); color: var(--text); margin: 0; padding-bottom: 90px; overflow-x: hidden; }
    
    header { background: linear-gradient(135deg, var(--primary), var(--secondary)); padding: 20px; text-align: center; font-size: 24px; font-weight: 700; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.5); border-bottom: 1px solid rgba(255,255,255,0.1); }
    .notice-bar { background: rgba(255, 193, 7, 0.1); color: #ffc107; padding: 12px; font-size: 14px; text-align: center; border-bottom: 1px solid #ffc107; }
    
    .container { width: 95%; max-width: 1200px; margin: auto; padding: 15px; }
    
    /* Movie Grid */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 15px; margin-top: 20px; }
    @media (min-width: 768px) { .grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); } }
    
    .card { background: var(--card-bg); border-radius: 15px; overflow: hidden; border: 1px solid #30363d; text-decoration: none; color: inherit; position: relative; }
    .card:hover { transform: translateY(-8px); border-color: var(--primary); box-shadow: 0 10px 25px rgba(0, 210, 255, 0.2); }
    .card img { width: 100%; height: 240px; object-fit: cover; }
    .card-info { padding: 12px; text-align: center; font-weight: 600; font-size: 14px; }
    
    /* Buttons */
    .btn { background: linear-gradient(90deg, var(--primary), var(--secondary)); color: white; padding: 14px; border-radius: 12px; text-decoration: none; display: block; text-align: center; border: none; font-weight: 600; cursor: pointer; margin: 10px 0; width: 100%; font-size: 16px; }
    .btn:active { transform: scale(0.95); }
    .btn-red { background: linear-gradient(90deg, #ff416c, #ff4b2b) !important; }
    .btn-outline { background: transparent; border: 1px solid var(--primary); color: var(--primary); }

    /* Forms */
    input, select { width: 100%; padding: 15px; border-radius: 10px; border: 1px solid #30363d; background: #0d1117; color: white; margin-bottom: 20px; font-size: 16px; }
    
    /* Pagination */
    .pagination { display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 30px; }
    .page-link { padding: 10px 18px; background: #21262d; border-radius: 8px; text-decoration: none; color: white; border: 1px solid #30363d; }
    .page-link.active { background: var(--primary); border-color: var(--primary); }

    /* Bottom Nav */
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: #161b22; display: flex; justify-content: space-around; padding: 15px 0; border-top: 1px solid #30363d; z-index: 1000; box-shadow: 0 -5px 20px rgba(0,0,0,0.5); }
    .bottom-nav a { color: #8b949e; text-decoration: none; font-size: 13px; text-align: center; display: flex; flex-direction: column; align-items: center; }
    .bottom-nav a.active { color: var(--primary); font-weight: 700; }
    .bottom-nav i { font-size: 20px; margin-bottom: 5px; }

    /* Task Card */
    .task-card { background: #1c2128; padding: 20px; border-radius: 15px; margin-bottom: 15px; border-left: 5px solid var(--primary); display: flex; justify-content: space-between; align-items: center; }
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
# 🔐 ইউজার সিস্টেম (AUTH)
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname, lname, mobile, pwd = request.form.get('fname'), request.form.get('lname'), request.form.get('mobile'), request.form.get('password')
        if users_col.find_one({"mobile": mobile}):
            flash("❌ এই নম্বর দিয়ে অলরেডি অ্যাকাউন্ট আছে!")
        else:
            users_col.insert_one({
                "fname": fname, "lname": lname, "mobile": mobile,
                "password": generate_password_hash(pwd), "coins": 0, "premium_until": datetime.utcnow()
            })
            return redirect('/login')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container'><h2>🚀 রেজিস্ট্রেশন করুন</h2><form method='post'><input name='fname' placeholder='First Name' required><input name='lname' placeholder='Last Name' required><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>Create Account</button></form><br><a href='/login' style='color:gray;text-decoration:none;'>ইতিমধ্যে অ্যাকাউন্ট আছে? লগইন করুন</a></div></body></html>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({"mobile": request.form.get('mobile')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['uid'] = str(user['_id']); return redirect('/')
        flash("❌ মোবাইল নম্বর বা পাসওয়ার্ড ভুল!")
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container'><h2>🔑 লগইন করুন</h2><form method='post'><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>Login Now</button></form><br><a href='/register' style='color:gray;text-decoration:none;'>নতুন অ্যাকাউন্ট খুলুন</a></div></body></html>")

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

# ==========================================
# 🏠 হোমপেজ (মুভি ও পেজিনেশন)
# ==========================================
@app.route('/')
def index():
    user = get_user()
    if not user: return redirect('/login')
    conf = get_site_conf()
    page = request.args.get('page', 1, type=int)
    per_page = 30
    total_movies = movies_col.count_documents({})
    total_pages = math.ceil(total_movies / per_page)
    movies = list(movies_col.find().sort("_id", -1).skip((page-1)*per_page).limit(per_page))
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>{{{{conf['site_name']}}}}</title>{STYLE}</head><body>
            <header>{{{{conf['site_name']}}}}</header>
            <div class="notice-bar"><marquee>{{{{conf['notice']}}}}</marquee></div>
            <div class="container">
                <div class="grid">
                    {{% for m in movies %}}
                    <a href="/movie/{{{{m._id}}}}" class="card">
                        <img src="{{{{m.poster}}}}">
                        <div class="card-info">{{{{m.name}}}}</div>
                    </a>
                    {{% endfor %}}
                </div>
                
                <div class="pagination">
                    {{% if page > 1 %}}
                    <a href="/?page={{{{page-1}}}}" class="page-link">Preview</a>
                    {{% endif %}}
                    
                    {{% for p in range(max(1, page-2), min(total_pages, page+2)+1) %}}
                    <a href="/?page={{{{p}}}}" class="page-link {{{{ 'active' if p == page else '' }}}}">{{{{p}}}}</a>
                    {{% endfor %}}
                    
                    {{% if page < total_pages %}}
                    <a href="/?page={{{{page+1}}}}" class="page-link">Next</a>
                    {{% endif %}}
                </div>
            </div>
            {get_nav('/')}
        </body></html>
    """, conf=settings_col.find_one({"key": "site_config"}), movies=movies, page=page, total_pages=total_pages, max=max, min=min)

# ==========================================
# 🎬 মুভি ডিটেইল পেজ (AD LOGIC)
# ==========================================
@app.route('/movie/<id>')
def movie_detail(id):
    user = get_user()
    if not user: return redirect('/login')
    movie = movies_col.find_one({"_id": ObjectId(id)})
    conf = settings_col.find_one({"key": "site_config"})
    premium = is_premium(user)
    
    # এডমিন প্যানেল থেকে জোন আইডি কন্ট্রোল
    zid = conf.get('zone_id', '10351894')
    ad_script = f"<script src='//libtl.com/sdk.js' data-zone='{zid}' data-sdk='show_{zid}'></script>" if not premium else ""
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>{{{{movie.name}}}}</header>
            <div class="container" style="text-align:center;">
                <img src="{{{{movie.poster}}}}" style="width:100%; max-width:500px; border-radius:20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <h2 style="margin-top:20px;">{{{{movie.name}}}}</h2>
                <hr style="border: 0.5px solid #30363d;">
                
                <h3 style="text-align:left;">Episodes List:</h3>
                {{% for ep in movie.episodes %}}
                    <div style="margin-bottom:15px;">
                        {ad_script}
                        <a href="{{{{ep}}}}" class="btn">🚀 Play Episode {{{{loop.index}}}}</a>
                    </div>
                {{% endfor %}}
                <a href="/" class="btn btn-outline">Back to Home</a>
            </div>
        </body></html>
    """, movie=movie)

# ==========================================
# 💰 টাস্ক সিস্টেম (EARNING SYSTEM)
# ==========================================
@app.route('/tasks')
def tasks():
    user = get_user()
    if not user: return redirect('/login')
    l_tasks = list(link_tasks_col.find())
    a_tasks = list(ad_tasks_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>💰 Task Center</header>
            <div class="container">
                <div class="card" style="padding:20px; text-align:center; background: linear-gradient(45deg, #161b22, #21262d);">
                    <span style="font-size:18px;">Your Coins</span><br>
                    <span style="font-size:32px; color:var(--primary); font-weight:700;">{{{{user.coins}}}} 🪙</span>
                </div>

                <h3>🔗 Direct Link Tasks</h3>
                {{% for t in l_tasks %}}
                <div class="task-card">
                    <div>
                        <div style="font-weight:600;">{{{{t.name}}}}</div>
                        <div style="color:var(--primary); font-size:13px;">Reward: +{{{{t.coins}}}} Coins</div>
                    </div>
                    <a href="{{{{t.link}}}}" target="_blank" class="btn" style="width:80px; padding:8px; margin:0;" onclick="claim('link', '{{{{t._id}}}}')">Go</a>
                </div>
                {{% endfor %}}

                <h3>📺 Monetag Ads (Unlimited)</h3>
                {{% for t in a_tasks %}}
                <div class="task-card">
                    <div>
                        <div style="font-weight:600;">{{{{t.name}}}}</div>
                        <div style="color:#ffc107; font-size:13px;">Daily Limit: {{{{t.limit}}}}</div>
                    </div>
                    <button class="btn" style="width:100px; padding:8px; margin:0;" onclick="watchAd('{{{{t.zone_id}}}}', '{{{{t._id}}}}')">Watch</button>
                </div>
                <div id="ad-box-{{{{t._id}}}}"></div>
                {{% endfor %}}
            </div>
            <script>
                function claim(type, tid) {{ fetch('/claim/'+type+'/'+tid); }}
                function watchAd(zid, tid) {{
                    const box = document.getElementById('ad-box-'+tid);
                    const s = document.createElement('script');
                    s.src = '//libtl.com/sdk.js';
                    s.setAttribute('data-zone', zid);
                    s.setAttribute('data-sdk', 'show_'+zid);
                    box.innerHTML = ''; box.appendChild(s);
                    fetch('/claim/ad/'+tid).then(r => alert("Wait for Ad to finish! Coins will be added."));
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
    if t:
        # এখানে ডেইলি লিমিট চেক লজিক যোগ করা যায়
        users_col.update_one({"_id": user['_id']}, {"$inc": {"coins": int(t['coins'])}})
    return "ok"

# ==========================================
# 💎 প্রিমিয়াম প্যাকেজ ও প্রোফাইল
# ==========================================
@app.route('/premium')
def premium():
    user = get_user()
    if not user: return redirect('/login')
    pkgs = list(packages_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>💎 Premium Store</header>
            <div class="container">
                <p style="text-align:center; color:#8b949e;">প্রিমিয়াম কিনলে মুভি দেখার সময় কোনো এড আসবে না।</p>
                {{% for p in pkgs %}}
                <div class="card" style="padding:25px; text-align:center; border: 1px solid gold; margin-bottom:20px;">
                    <h2 style="color:gold; margin-top:0;">{{{{p.name}}}}</h2>
                    <div style="font-size:18px;">মেয়াদ: {{{{p.days}}}} দিন</div>
                    <div style="font-size:22px; margin:10px 0;">মূল্য: {{{{p.coins}}}} Coins</div>
                    <a href="/buy/{{{{p._id}}}}" class="btn" style="background: gold; color:black;">এখনই কিনুন</a>
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
        flash("✅ Premium Activated!")
    return redirect('/premium')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = get_user()
    if not user: return redirect('/login')
    if request.method == 'POST':
        upd = {"fname": request.form.get('fname'), "lname": request.form.get('lname')}
        if request.form.get('p'): upd['password'] = generate_password_hash(request.form.get('p'))
        users_col.update_one({"_id": user['_id']}, {"$set": upd}); return redirect('/profile')
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>👤 User Profile</header>
            <div class="container">
                <div class="card" style="padding:25px; text-align:center;">
                    <i class="fas fa-user-circle" style="font-size:60px; color:var(--primary);"></i>
                    <h3>{{{{user.fname}}}} {{{{user.lname}}}}</h3>
                    <p>Mobile: {{{{user.mobile}}}}</p>
                    <p>Status: {{{{ '🌟 Premium' if user.premium_until > now else '🆓 Free' }}}}</p>
                </div>
                <form method="post" class="card" style="padding:20px; margin-top:20px;">
                    <h4>Edit Profile</h4>
                    <input name="fname" value="{{{{user.fname}}}}">
                    <input name="lname" value="{{{{user.lname}}}}">
                    <input type="password" name="p" placeholder="New Password (optional)">
                    <button class="btn">Update Information</button>
                </form>
                <a href="/logout" class="btn btn-red">Logout Account</a>
            </div>
            {get_nav('/profile')}
        </body></html>
    """, user=user, now=datetime.utcnow())

def get_nav(active):
    return f"""
    <div class="bottom-nav">
        <a href="/" class="{'active' if active=='/' else ''}"><i class="fas fa-home"></i>Home</a>
        <a href="/tasks" class="{'active' if active=='/tasks' else ''}"><i class="fas fa-tasks"></i>Tasks</a>
        <a href="/premium" class="{'active' if active=='/premium' else ''}"><i class="fas fa-gem"></i>Premium</a>
        <a href="/profile" class="{'active' if active=='/profile' else ''}"><i class="fas fa-user"></i>Profile</a>
    </div>
    """

# ==========================================
# ⚡ এডমিন প্যানেল (৫টি আলাদা ম্যানেজমেন্ট মেনু)
# ==========================================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        if request.method == 'POST' and request.form.get('pass') == ADMIN_PASS:
            session['admin'] = True; return redirect('/admin')
        return "<html><body style='background:#0b0e14; color:white; padding:50px; text-align:center;'><form method='post'><h2>Admin Access</h2><input type='password' name='pass' style='max-width:300px;'><br><button class='btn' style='max-width:300px;'>Login</button></form></body></html>"
    
    # পোস্ট হ্যান্ডলিং (Add/Delete/Update)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == "site_update":
            settings_col.update_one({"key": "site_config"}, {"$set": {"site_name": request.form.get('sn'), "notice": request.form.get('nt'), "zone_id": request.form.get('zid')}})
        elif action == "add_link":
            link_tasks_col.insert_one({"name": request.form.get('n'), "link": request.form.get('l'), "coins": int(request.form.get('c'))})
        elif action == "add_ad":
            ad_tasks_col.insert_one({"name": request.form.get('n'), "zone_id": request.form.get('z'), "coins": int(request.form.get('c')), "limit": int(request.form.get('lim'))})
        elif action == "add_pkg":
            packages_col.insert_one({"name": request.form.get('n'), "days": int(request.form.get('d')), "coins": int(request.form.get('c'))})
        elif action == "delete":
            col_map = {"movie": movies_col, "link": link_tasks_col, "ad": ad_tasks_col, "pkg": packages_col}
            col_map[request.form.get('type')].delete_one({"_id": ObjectId(request.form.get('id'))})
        return redirect('/admin')

    conf = settings_col.find_one({"key": "site_config"})
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body style="padding:20px;">
            <h2>🛠 Control Panel</h2>
            
            <div class="task-card" style="display:block;">
                <h3>1. ⚙️ Site Settings</h3>
                <form method="post"><input type="hidden" name="action" value="site_update">
                    Site Name: <input name="sn" value="{conf['site_name']}">
                    Notice: <input name="nt" value="{conf['notice']}">
                    Movie Ad Zone ID: <input name="zid" value="{conf.get('zone_id','')}">
                    <button class="btn">Save Configuration</button>
                </form>
            </div>

            <div class="task-card" style="display:block; margin-top:20px;">
                <h3>2. 🔗 Manage Link Tasks</h3>
                <form method="post"><input type="hidden" name="action" value="add_link">
                    Name: <input name="n"> Link: <input name="l"> Coins: <input name="c">
                    <button class="btn">Add Link Task</button>
                </form>
                <hr>
                {{% for t in l_tasks %}}
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span>{{{{t.name}}}}</span>
                    <form method="post" style="margin:0;"><input type="hidden" name="action" value="delete"><input type="hidden" name="type" value="link"><input type="hidden" name="id" value="{{{{t._id}}}}"><button style="color:red; background:none; border:none; cursor:pointer;">[Delete]</button></form>
                </div>
                {{% endfor %}}
            </div>

            <div class="task-card" style="display:block; margin-top:20px;">
                <h3>3. 📺 Manage Ad Tasks</h3>
                <form method="post"><input type="hidden" name="action" value="add_ad">
                    Task Name: <input name="n"> Monetag Zone ID: <input name="z"> Coins: <input name="c"> Daily Limit: <input name="lim">
                    <button class="btn">Add Ad Task</button>
                </form>
                <hr>
                {{% for t in a_tasks %}}
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span>{{{{t.name}}}}</span>
                    <form method="post" style="margin:0;"><input type="hidden" name="action" value="delete"><input type="hidden" name="type" value="ad"><input type="hidden" name="id" value="{{{{t._id}}}}"><button style="color:red; background:none; border:none; cursor:pointer;">[Delete]</button></form>
                </div>
                {{% endfor %}}
            </div>

            <div class="task-card" style="display:block; margin-top:20px;">
                <h3>4. 💎 Manage Packages</h3>
                <form method="post"><input type="hidden" name="action" value="add_pkg">
                    Name: <input name="n"> Days: <input name="d"> Coins: <input name="c">
                    <button class="btn">Add Package</button>
                </form>
                <hr>
                {{% for p in pkgs %}}
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span>{{{{p.name}}}} - {{{{p.coins}}}} Coins</span>
                    <form method="post" style="margin:0;"><input type="hidden" name="action" value="delete"><input type="hidden" name="type" value="pkg"><input type="hidden" name="id" value="{{{{p._id}}}}"><button style="color:red; background:none; border:none; cursor:pointer;">[Delete]</button></form>
                </div>
                {{% endfor %}}
            </div>

            <div class="task-card" style="display:block; margin-top:20px;">
                <h3>5. 🎬 Manage Movies</h3>
                <p>Movies can be added via Telegram Bot using /movie command.</p>
                <hr>
                {{% for m in movies %}}
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span>{{{{m.name}}}}</span>
                    <form method="post" style="margin:0;"><input type="hidden" name="action" value="delete"><input type="hidden" name="type" value="movie"><input type="hidden" name="id" value="{{{{m._id}}}}"><button style="color:red; background:none; border:none; cursor:pointer;">[Delete]</button></form>
                </div>
                {{% endfor %}}
            </div>

            <a href="/logout" class="btn btn-red">Logout Admin</a>
        </body></html>
    """, l_tasks=list(link_tasks_col.find()), a_tasks=list(ad_tasks_col.find()), pkgs=list(packages_col.find()), movies=list(movies_col.find()))

def get_site_conf():
    return settings_col.find_one({"key": "site_config"})

# ==========================================
# 🤖 টেলিগ্রাম বট (AUTO MOVIE UPLOADER)
# ==========================================
bot = Client("MegaMovieBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
upload_flow = {}

@bot.on_message(filters.command("start"))
async def start(c, m):
    await m.reply_text("👋 Hello Admin! Use /movie to add a new movie to the site.")

@bot.on_message(filters.command("movie") & filters.user(ADMIN_ID))
async def add_movie_start(c, m):
    upload_flow[m.from_user.id] = {"step": "name", "episodes": []}
    await m.reply_text("🎬 **Step 1: মুভির নাম দিন**")

@bot.on_message(filters.text & filters.user(ADMIN_ID))
async def handle_input(c, m):
    uid = m.from_user.id
    if uid not in upload_flow: return

    state = upload_flow[uid]
    if state["step"] == "name":
        state["name"] = m.text
        state["step"] = "poster"
        await m.reply_text("🖼 **Step 2: পোস্টারের ডিরেক্ট URL দিন**\n(এটি অটো সাইটে সেভ হবে)")
    elif state["step"] == "poster":
        state["poster"] = m.text
        state["step"] = "eps"
        await m.reply_text("🔗 **Step 3: ইপিসোড লিঙ্ক দিন**\nআপনি একটার পর একটা লিঙ্ক দিতে পারেন। সব দেওয়া শেষ হলে নিচের **Done** বাটনে ক্লিক করুন।",
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done (Save)", callback_data="save_movie")]]))
    elif state["step"] == "eps":
        state["episodes"].append(m.text)
        await m.reply_text(f"✅ Episode {len(state['episodes'])} Added. আরও লিঙ্ক দিন অথবা Done ক্লিক করুন।")

@bot.on_callback_query(filters.regex("save_movie"))
async def save_movie(c, q):
    uid = q.from_user.id
    if uid not in upload_flow: return
    data = upload_flow[uid]
    movies_col.insert_one({
        "name": data["name"], "poster": data["poster"], "episodes": data["episodes"],
        "created_at": datetime.utcnow(), "views": 0
    })
    await q.message.edit_text(f"🚀 **Successfully Uploaded!**\nMovie: {data['name']}\nEpisodes: {len(data['episodes'])}")
    del upload_flow[uid]

# ==========================================
# 🚀 রান প্রসেস
# ==========================================
def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    # বটকে আলাদা থ্রেডে রান করা
    bot_thread = threading.Thread(target=lambda: bot.run())
    bot_thread.daemon = True
    bot_thread.start()
    
    # ফ্ল্যাক্স অ্যাপ রান করা
    run_flask()
