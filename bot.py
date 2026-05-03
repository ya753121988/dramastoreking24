import os
import threading
import math
import time
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# --- ⚙️ কনফিগারেশন (পরিবেশ ভেরিয়েবল থেকে নিবে) ---
API_ID = int(os.getenv("API_ID", "29904834"))
API_HASH = os.getenv("API_HASH", "8b4fd9ef578af114502feeafa2d31938")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8655043839:AAFSI7Tqk6bftnVNqtBB-kRdbFDmr8b3Lf0")
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7120801813"))
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

# 🗄️ ডাটাবেস কানেকশন
client = MongoClient(MONGO_URL)
db = client['ProMovieFinalDB']
movies_col = db['movies']
users_col = db['users']
link_tasks_col = db['link_tasks']
ad_tasks_col = db['ad_tasks']
packages_col = db['packages']
settings_col = db['settings']

# 🛠️ ডিফল্ট সেটিংস ইনিশিয়ালাইজেশন
def init_settings():
    if not settings_col.find_one({"key": "site_config"}):
        settings_col.insert_one({
            "key": "site_config",
            "site_name": "Premium Movie Store",
            "notice": "🌟 স্বাগতম! টাস্ক কমপ্লিট করে কয়েন ইনকাম করুন এবং প্রিমিয়াম মুভি দেখুন।",
            "zone_id": "10351894"
        })

init_settings()
app = Flask(__name__)
app.secret_key = "ultra_secure_secret_key_v99"

# --- 🎨 সিএসএস (সম্পূর্ণ রেসপন্সিভ) ---
STYLE = """
<style>
    :root { --primary: #0ea5e9; --secondary: #6366f1; --dark: #0f172a; --card: #1e293b; --text: #f8fafc; }
    * { box-sizing: border-box; outline: none; }
    body { background: var(--dark); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; padding-bottom: 80px; }
    header { background: linear-gradient(135deg, var(--primary), var(--secondary)); padding: 15px; text-align: center; font-size: 22px; font-weight: bold; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 15px rgba(0,0,0,0.4); }
    .notice-bar { background: #334155; padding: 10px; font-size: 13px; text-align: center; border-bottom: 2px solid var(--primary); color: #fbbf24; }
    .container { width: 95%; max-width: 1200px; margin: auto; padding: 15px; }
    
    /* 📱 কার্ড ও গ্রিড */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-top: 15px; }
    @media (min-width: 768px) { .grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); } }
    .card { background: var(--card); border-radius: 12px; overflow: hidden; border: 1px solid #334155; text-decoration: none; color: inherit; transition: 0.2s; position: relative; }
    .card img { width: 100%; height: 210px; object-fit: cover; }
    .card-info { padding: 8px; text-align: center; font-size: 13px; font-weight: 500; }
    
    .btn { background: linear-gradient(90deg, var(--primary), var(--secondary)); color: white; padding: 12px; border-radius: 8px; text-decoration: none; display: block; text-align: center; border: none; font-weight: bold; cursor: pointer; margin: 5px 0; }
    .btn-red { background: #ef4444 !important; }
    input, select { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #334155; background: #1e293b; color: white; margin-bottom: 15px; }
    
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: var(--card); display: flex; justify-content: space-around; padding: 10px 0; border-top: 1px solid #334155; z-index: 1000; }
    .bottom-nav a { color: #94a3b8; text-decoration: none; font-size: 12px; text-align: center; }
    .bottom-nav a.active { color: var(--primary); font-weight: bold; }
    
    .pagination { display: flex; justify-content: center; gap: 10px; margin-top: 20px; }
    .page-link { padding: 8px 15px; background: #334155; border-radius: 5px; text-decoration: none; color: white; }
    .page-link.active { background: var(--primary); }
</style>
"""

# --- 🛠️ হেল্পারস ---
def get_site_conf(): return settings_col.find_one({"key": "site_config"})
def get_user(): 
    if 'uid' in session: return users_col.find_one({"_id": ObjectId(session['uid'])})
    return None
def is_premium(user):
    if not user or 'premium_until' not in user: return False
    return user['premium_until'] > datetime.utcnow()

# --- 🔐 অথেনটিকেশন (রেজিস্ট্রেশন ও লগইন) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        mobile = request.form.get('mobile')
        password = generate_password_hash(request.form.get('password'))
        if users_col.find_one({"mobile": mobile}): flash("❌ নম্বরটি ব্যবহৃত হচ্ছে!")
        else:
            users_col.insert_one({
                "fname": fname, "lname": lname, "mobile": mobile, 
                "password": password, "coins": 0, "premium_until": datetime.utcnow()
            })
            return redirect('/login')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container'><h2>📝 রেজিস্ট্রেশন</h2><form method='post'><input name='fname' placeholder='First Name' required><input name='lname' placeholder='Last Name' required><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>অ্যাকাউন্ট খুলুন</button></form><br><a href='/login' style='color:gray'>ইতিমধ্যে অ্যাকাউন্ট আছে? লগইন করুন</a></div></body></html>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({"mobile": request.form.get('mobile')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['uid'] = str(user['_id']); return redirect('/')
        flash("❌ ভুল তথ্য!")
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container'><h2>🔑 লগইন</h2><form method='post'><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>লগইন</button></form><br><a href='/register' style='color:gray'>নতুন অ্যাকাউন্ট খুলুন</a></div></body></html>")

# --- 🏠 হোমপেজ (মুভি ও পেজিনেশন) ---
@app.route('/')
def home():
    user = get_user()
    if not user: return redirect('/login')
    conf = get_site_conf()
    page = request.args.get('page', 1, type=int)
    per_page = 30
    total_movies = movies_col.count_documents({})
    total_pages = math.ceil(total_movies / per_page)
    movies = list(movies_col.find().sort("_id", -1).skip((page-1)*per_page).limit(per_page))
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>{conf['site_name']}</title>{STYLE}</head><body>
            <header>{conf['site_name']}</header>
            <div class="notice-bar"><marquee>{conf['notice']}</marquee></div>
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
                    {{% if page > 1 %}}<a href="/?page={{{{page-1}}}}" class="page-link">Prev</a>{{% endif %}}
                    <span class="page-link active">{{{{page}}}}</span>
                    {{% if page < total_pages %}}<a href="/?page={{{{page+1}}}}" class="page-link">Next</a>{{% endif %}}
                </div>
            </div>
            {bottom_nav('/')}
        </body></html>
    """, movies=movies, page=page, total_pages=total_pages)

# --- 🎬 মুভি ডিটেইলস (এডমিনের জোন আইডি অনুযায়ী এড) ---
@app.route('/movie/<id>')
def movie_detail(id):
    user = get_user()
    if not user: return redirect('/login')
    movie = movies_col.find_one({"_id": ObjectId(id)})
    conf = get_site_conf()
    zid = conf.get('zone_id', '10351894')
    premium = is_premium(user)
    
    # প্রিমিয়াম না হলে এড দেখাবে
    ad_code = f"<script src='//libtl.com/sdk.js' data-zone='{zid}' data-sdk='show_{zid}'></script>" if not premium else ""
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>{{{{movie.name}}}}</header>
            <div class="container" style="text-align:center;">
                <img src="{{{{movie.poster}}}}" style="width:100%; max-width:400px; border-radius:15px; margin-bottom:20px;">
                <h3>Episodes List:</h3>
                {{% for ep in movie.episodes %}}
                    <div style="margin-bottom:10px;">
                        {ad_code}
                        <a href="{{{{ep}}}}" class="btn">▶️ Play Episode {{{{loop.index}}}}</a>
                    </div>
                {{% endfor %}}
                <br><a href="/" class="btn" style="background:#475569;">Back Home</a>
            </div>
        </body></html>
    """, movie=movie)

# --- 💰 টাস্ক সিস্টেম (লিঙ্ক ও এড টাস্ক) ---
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
                <div class="card" style="padding:15px; text-align:center; border-color: gold;">
                    Current Balance: <b>{{{{user.coins}}}} Coins</b>
                </div>
                
                <h3 style="margin-top:20px;">🔗 Direct Link Tasks</h3>
                {{% for t in l_tasks %}}
                <div class="card" style="padding:15px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                    <span>{{{{t.name}}}} (+{{{{t.coins}}}})</span>
                    <a href="{{{{t.link}}}}" target="_blank" class="btn" style="width:100px; margin:0;" onclick="fetch('/claim/link/{{{{t._id}}}}')">Visit</a>
                </div>
                {{% endfor %}}

                <h3 style="margin-top:20px;">📺 Monetag Video Ads</h3>
                {{% for t in a_tasks %}}
                <div class="card" style="padding:15px; margin-bottom:10px;">
                    <p>{{{{t.name}}}} (+{{{{t.coins}}}}) | Limit: {{{{t.limit}}}}/Day</p>
                    <button class="btn" onclick="watchAd('{{{{t.zone_id}}}}', '{{{{t._id}}}}')">Watch Ads</button>
                    <div id="ad-area-{{{{t._id}}}}"></div>
                </div>
                {{% endfor %}}
            </div>
            <script>
                function watchAd(zid, tid) {{
                    const area = document.getElementById('ad-area-'+tid);
                    const script = document.createElement('script');
                    script.src = '//libtl.com/sdk.js';
                    script.setAttribute('data-zone', zid);
                    script.setAttribute('data-sdk', 'show_' + zid);
                    area.innerHTML = '';
                    area.appendChild(script);
                    fetch('/claim/ad/' + tid);
                    alert("Ad is loading... Once finished, coins will be added!");
                }}
            </script>
            {bottom_nav('/tasks')}
        </body></html>
    """, user=user, l_tasks=l_tasks, a_tasks=a_tasks)

@app.route('/claim/<type>/<tid>')
def claim(type, tid):
    user = get_user()
    if not user: return "Unauthorized"
    col = link_tasks_col if type == "link" else ad_tasks_col
    t = col.find_one({"_id": ObjectId(tid)})
    if t:
        users_col.update_one({"_id": user['_id']}, {"$inc": {"coins": int(t['coins'])}})
    return "OK"

# --- 💎 প্রিমিয়াম স্টোর ---
@app.route('/premium')
def premium_store():
    user = get_user()
    if not user: return redirect('/login')
    pkgs = list(packages_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>💎 Buy Premium</header>
            <div class="container">
                <p style="text-align:center;">Buy a package to remove all ads from movie buttons!</p>
                {{% for p in pkgs %}}
                <div class="card" style="padding:20px; text-align:center; border: 2px solid gold; margin-bottom:15px;">
                    <h2 style="color:gold; margin:0;">{{{{p.name}}}}</h2>
                    <p>Duration: {{{{p.days}}}} Days | Cost: {{{{p.coins}}}} Coins</p>
                    <a href="/buy/{{{{p._id}}}}" class="btn">Buy Now</a>
                </div>
                {{% endfor %}}
            </div>
            {bottom_nav('/premium')}
        </body></html>
    """, pkgs=pkgs)

@app.route('/buy/<pid>')
def buy_package(pid):
    user = get_user()
    if not user: return redirect('/login')
    p = packages_col.find_one({"_id": ObjectId(pid)})
    if user['coins'] >= int(p['coins']):
        expiry = max(user.get('premium_until', datetime.utcnow()), datetime.utcnow()) + timedelta(days=int(p['days']))
        users_col.update_one({"_id": user['_id']}, {"$set": {"premium_until": expiry}, "$inc": {"coins": -int(p['coins'])}})
        flash("✅ Premium Activated!")
    else:
        flash("❌ Not enough coins!")
    return redirect('/premium')

# --- 👤 প্রোফাইল (পাসওয়ার্ড ও নাম পরিবর্তন) ---
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = get_user()
    if not user: return redirect('/login')
    if request.method == 'POST':
        upd = {"fname": request.form.get('fname'), "lname": request.form.get('lname')}
        if request.form.get('pass'):
            upd['password'] = generate_password_hash(request.form.get('pass'))
        users_col.update_one({"_id": user['_id']}, {"$set": upd})
        return redirect('/profile')
    
    status = "🌟 Premium User" if is_premium(user) else "🆓 Free User"
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <header>👤 My Profile</header>
            <div class="container">
                <div class="card" style="padding:20px; text-align:center;">
                    <h3>{{{{user.fname}}}} {{{{user.lname}}}}</h3>
                    <p>Mobile: {{{{user.mobile}}}}</p>
                    <p style="color:var(--primary); font-weight:bold;">Coins: {{{{user.coins}}}}</p>
                    <span style="background:green; padding:5px 10px; border-radius:5px;">{status}</span>
                </div>
                <form method="post" class="card" style="padding:20px; margin-top:20px;">
                    <h4>Edit Information</h4>
                    First Name: <input name="fname" value="{{{{user.fname}}}}">
                    Last Name: <input name="lname" value="{{{{user.lname}}}}">
                    New Password (Optional): <input type="password" name="pass">
                    <button class="btn">Update Profile</button>
                </form>
                <a href="/logout" class="btn btn-red">Logout</a>
            </div>
            {bottom_nav('/profile')}
        </body></html>
    """, user=user)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

def bottom_nav(active):
    return f"""
    <div class="bottom-nav">
        <a href="/" class="{'active' if active=='/' else ''}">🏠 Home</a>
        <a href="/tasks" class="{'active' if active=='/tasks' else ''}">💰 Tasks</a>
        <a href="/premium" class="{'active' if active=='/premium' else ''}">💎 Premium</a>
        <a href="/profile" class="{'active' if active=='/profile' else ''}">👤 Profile</a>
    </div>
    """

# --- ⚡ এডমিন প্যানেল (সব কন্ট্রোল এখানে) ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        if request.method == 'POST' and request.form.get('p') == ADMIN_PASS:
            session['admin'] = True; return redirect('/admin')
        return "<html><body style='background:#0f172a;color:white;padding:50px;'><form method='post'>Password: <input type='password' name='p'><button>Login</button></form></body></html>"
    
    if request.method == 'POST':
        action = request.form.get('a')
        if action == "site":
            settings_col.update_one({"key": "site_config"}, {"$set": {
                "site_name": request.form.get('sn'), "notice": request.form.get('nt'), "zone_id": request.form.get('zid')
            }})
        elif action == "add_link":
            link_tasks_col.insert_one({"name": request.form.get('n'), "link": request.form.get('l'), "coins": int(request.form.get('c'))})
        elif action == "add_ad":
            ad_tasks_col.insert_one({"name": request.form.get('n'), "zone_id": request.form.get('z'), "coins": int(request.form.get('c')), "limit": int(request.form.get('lim'))})
        elif action == "add_pkg":
            packages_col.insert_one({"name": request.form.get('n'), "days": int(request.form.get('d')), "coins": int(request.form.get('c'))})
        elif action == "del_m": movies_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        elif action == "del_l": link_tasks_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        elif action == "del_a": ad_tasks_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        elif action == "del_p": packages_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        return redirect('/admin')

    conf = get_site_conf()
    movies = list(movies_col.find())
    l_tasks = list(link_tasks_col.find())
    a_tasks = list(ad_tasks_col.find())
    pkgs = list(packages_col.find())

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body style="padding:20px;">
            <h2>🛠 Admin Dashboard</h2>
            <div class="card" style="padding:15px;">
                <h3>Site Config</h3>
                <form method="post"><input type="hidden" name="a" value="site">
                    Name: <input name="sn" value="{conf['site_name']}">
                    Notice: <input name="nt" value="{conf['notice']}">
                    Global Ad Zone ID: <input name="zid" value="{conf.get('zone_id','')}">
                    <button class="btn">Update Site</button>
                </form>
            </div>
            
            <div class="card" style="padding:15px; margin-top:15px;">
                <h3>Add Link Task</h3>
                <form method="post"><input type="hidden" name="a" value="add_link">
                    Name: <input name="n"> Link: <input name="l"> Coins: <input name="c">
                    <button class="btn">Add Link Task</button>
                </form>
            </div>

            <div class="card" style="padding:15px; margin-top:15px;">
                <h3>Add Ad Task (Monetag)</h3>
                <form method="post"><input type="hidden" name="a" value="add_ad">
                    Name: <input name="n"> Zone ID: <input name="z"> Coins: <input name="c"> Daily Limit: <input name="lim">
                    <button class="btn">Add Ad Task</button>
                </form>
            </div>

            <div class="card" style="padding:15px; margin-top:15px;">
                <h3>Add Premium Package</h3>
                <form method="post"><input type="hidden" name="a" value="add_pkg">
                    Name: <input name="n"> Days: <input name="d"> Coins: <input name="c">
                    <button class="btn">Add Package</button>
                </form>
            </div>

            <h3 style="margin-top:30px;">Manage All</h3>
            <h4>Movies:</h4>
            {{% for m in movies %}}
            <p>{{{{m.name}}}} <a href="/admin?a=del_m&id={{{{m._id}}}}" style="color:red;">[Del]</a></p>
            {{% endfor %}}
            <h4>Packages:</h4>
            {{% for p in pkgs %}}
            <p>{{{{p.name}}}} - {{{{p.coins}}}} Coins <form method="post" style="display:inline;"><input type="hidden" name="a" value="del_p"><input type="hidden" name="id" value="{{{{p._id}}}}"><button style="color:red; background:none; border:none; cursor:pointer;">[Del]</button></form></p>
            {{% endfor %}}
        </body></html>
    """, conf=conf, movies=movies, l_tasks=l_tasks, a_tasks=a_tasks, pkgs=pkgs)

# --- 🤖 টেলিগ্রাম বট (অটোমেটেড মুভি আপলোডার) ---
bot = Client("ProMovieBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
bot_states = {} # এডমিনদের ডাটা টেম্পোরারি সেভ করার জন্য

@bot.on_message(filters.command("movie") & filters.user(ADMIN_ID))
async def add_movie_start(c, m):
    bot_states[m.from_user.id] = {"step": "name", "eps": []}
    await m.reply_text("🎬 **মুভির নাম দিন:**")

@bot.on_message(filters.text & filters.user(ADMIN_ID))
async def movie_input_handler(c, m):
    uid = m.from_user.id
    if uid not in bot_states: return

    state = bot_states[uid]
    if state["step"] == "name":
        state["name"] = m.text
        state["step"] = "poster"
        await m.reply_text("🖼 **মুভির ডিরেক্ট পোস্টার লিঙ্ক (URL) দিন:**\n(এটি অটো ডাটাবেসে সেভ হবে)")
    
    elif state["step"] == "poster":
        state["poster"] = m.text
        state["step"] = "eps"
        await m.reply_text("🔗 **ইপিসোড ফাইল বা লিঙ্ক দিন:**\nআপনি চাইলে একটার পর একটা দিতে পারেন। শেষ হলে নিচের **Done** বাটনে ক্লিক করুন।", 
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Done (আপলোড করুন)", callback_data="finish")]]))
    
    elif state["step"] == "eps":
        state["eps"].append(m.text)
        await m.reply_text(f"✅ ইপিসোড {len(state['eps'])} যুক্ত হয়েছে। আরও থাকলে দিন নয়তো Done দিন।")

@bot.on_callback_query(filters.regex("finish"))
async def finish_upload(c, q):
    uid = q.from_user.id
    if uid not in bot_states: return
    
    data = bot_states[uid]
    movies_col.insert_one({
        "name": data["name"],
        "poster": data["poster"],
        "episodes": data["eps"],
        "views": 0,
        "created_at": datetime.utcnow()
    })
    
    await q.message.edit_text(f"🚀 **'{data['name']}'** সফলভাবে সাইটে আপলোড হয়ে গেছে!")
    del bot_states[uid]

# বট এবং ফ্ল্যাক্স একসাথে চালানোর জন্য থ্রেড
def run_bot():
    bot.run()

if __name__ == "__main__":
    # বট থ্রেড স্টার্ট
    threading.Thread(target=run_bot, daemon=True).start()
    # ফ্ল্যাক্স অ্যাপ স্টার্ট
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
