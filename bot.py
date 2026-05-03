import os
import threading
import math
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# --- ⚙️ কনফিগারেশন ---
API_ID = int(os.getenv("API_ID", "29904834"))
API_HASH = os.getenv("API_HASH", "8b4fd9ef578af114502feeafa2d31938")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8655043839:AAGmoyWwzJFAi9hOovKNeySOp6UzrHBPibQ")
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
app.secret_key = "ultra_secure_secret_key_v3"

# --- 🎨 প্রিমিয়াম রেসপন্সিভ সিএসএস (Mobile & Desktop Auto) ---
STYLE = """
<style>
    :root { --primary: #0ea5e9; --secondary: #6366f1; --dark: #0f172a; --card: #1e293b; --text: #f8fafc; }
    * { box-sizing: border-box; }
    body { background: var(--dark); color: var(--text); font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding-bottom: 80px; }
    header { background: linear-gradient(135deg, var(--primary), var(--secondary)); padding: 15px; text-align: center; font-size: 24px; font-weight: bold; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
    .notice-bar { background: #334155; padding: 10px; font-size: 14px; text-align: center; border-bottom: 2px solid var(--primary); }
    .container { width: 95%; max-width: 1200px; margin: auto; padding: 15px; }
    
    /* 📱 স্লাইডার */
    .slider { display: flex; overflow-x: auto; gap: 15px; padding: 10px 0; scrollbar-width: none; }
    .slider::-webkit-scrollbar { display: none; }
    .slider-item { flex: 0 0 160px; position: relative; border-radius: 15px; overflow: hidden; border: 2px solid #334155; transition: 0.3s; }
    .slider-item img { width: 100%; height: 230px; object-fit: cover; }
    .top-badge { position: absolute; top: 5px; left: 5px; background: #fbbf24; color: black; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; }

    /* 📦 গ্রিড সিস্টেম (Auto Mobile/Desktop) */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; margin-top: 20px; }
    @media (min-width: 768px) { .grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); } }
    
    .card { background: var(--card); border-radius: 15px; overflow: hidden; border: 1px solid #334155; text-decoration: none; color: inherit; transition: 0.3s; }
    .card:hover { transform: translateY(-5px); border-color: var(--primary); }
    .card img { width: 100%; height: 200px; object-fit: cover; }
    .card-info { padding: 10px; text-align: center; font-size: 14px; }
    
    .btn { background: linear-gradient(90deg, var(--primary), var(--secondary)); color: white; padding: 12px; border-radius: 10px; text-decoration: none; display: block; text-align: center; border: none; font-weight: bold; cursor: pointer; margin: 5px 0; font-size: 15px; }
    .btn-red { background: #ef4444 !important; }
    input, select { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #334155; background: #0f172a; color: white; margin-bottom: 15px; font-size: 16px; }
    
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: var(--card); display: flex; justify-content: space-around; padding: 12px 0; border-top: 1px solid #334155; z-index: 1000; }
    .bottom-nav a { color: #94a3b8; text-decoration: none; font-size: 13px; text-align: center; font-weight: bold; }
    .bottom-nav a.active { color: var(--primary); }
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

# --- 🔐 অথেনটিকেশন ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname, lname, mobile = request.form.get('fname'), request.form.get('lname'), request.form.get('mobile')
        password = generate_password_hash(request.form.get('password'))
        if users_col.find_one({"mobile": mobile}): flash("❌ নম্বরটি ব্যবহৃত হচ্ছে!")
        else:
            users_col.insert_one({"fname": fname, "lname": lname, "mobile": mobile, "password": password, "coins": 0, "premium_until": datetime.utcnow()})
            return redirect('/login')
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container'><h2>📝 রেজিস্ট্রেশন</h2><form method='post'><input name='fname' placeholder='First Name' required><input name='lname' placeholder='Last Name' required><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>🚀 অ্যাকাউন্ট খুলুন</button></form><br><a href='/login' style='color:gray'>ইতিমধ্যে অ্যাকাউন্ট আছে? লগইন করুন</a></div></body></html>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({"mobile": request.form.get('mobile')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['uid'] = str(user['_id']); return redirect('/')
        flash("❌ ভুল তথ্য!")
    return render_template_string(f"<html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body><div class='container'><h2>🔑 লগইন</h2><form method='post'><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>🔓 লগইন</button></form><br><a href='/register' style='color:gray'>নতুন অ্যাকাউন্ট খুলুন</a></div></body></html>")

# --- 🏠 মেইন সাইট ---
@app.route('/')
def home():
    user = get_user()
    if not user: return redirect('/login')
    conf = get_site_conf()
    top_movies = list(movies_col.find().sort("views", -1).limit(10))
    page = request.args.get('page', 1, type=int)
    per_page = 30
    all_movies = list(movies_col.find().sort("_id", -1).skip((page-1)*per_page).limit(per_page))
    total_pages = math.ceil(movies_col.count_documents({}) / per_page)
    
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'><title>{conf['site_name']}</title>{STYLE}</head><body>
            <header>💎 {conf['site_name']}</header>
            <div class="notice-bar"><marquee>{conf['notice']}</marquee></div>
            <div class="container">
                <h3>🔥 জনপ্রিয় মুভি (Top Views)</h3>
                <div class="slider">
                    {{% for m in top_movies %}}
                    <a href="/movie/{{{{m._id}}}}" class="slider-item">
                        <span class="top-badge">⭐ TOP {{{{loop.index}}}}</span>
                        <img src="{{{{m.poster}}}}">
                    </a>
                    {{% endfor %}}
                </div>
                <h3>🎬 সকল মুভি</h3>
                <div class="grid">
                    {{% for m in all_movies %}}
                    <a href="/movie/{{{{m._id}}}}" class="card">
                        <img src="{{{{m.poster}}}}">
                        <div class="card-info"><b>{{{{m.name}}}}</b><br><small>👁️ {{{{m.views}}}} views</small></div>
                    </a>
                    {{% endfor %}}
                </div>
                <div style="text-align:center; margin-top:20px;">
                    {{% if page > 1 %}}<a href="/?page={{{{page-1}}}}" class="btn" style="display:inline-block;width:100px;">Prev</a>{{% endif %}}
                    {{% if page < total_pages %}}<a href="/?page={{{{page+1}}}}" class="btn" style="display:inline-block;width:100px;">Next</a>{{% endif %}}
                </div>
            </div>
            {bottom_nav('/')}
        </body></html>
    """, top_movies=top_movies, all_movies=all_movies, page=page, total_pages=total_pages)

@app.route('/movie/<id>')
def movie_detail(id):
    user = get_user()
    if not user: return redirect('/login')
    # 👁️ ভিউ কাউন্ট আপডেট
    movies_col.update_one({"_id": ObjectId(id)}, {"$inc": {"views": 1}})
    movie = movies_col.find_one({"_id": ObjectId(id)})
    conf = get_site_conf()
    zone_id = conf.get('zone_id', '10351894')
    premium = is_premium(user)
    ad_script = f"<script src='//libtl.com/sdk.js' data-zone='{zone_id}' data-sdk='show_{zone_id}'></script>" if not premium else ""

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <div class="container" style="text-align:center;">
                <img src="{{{{movie.poster}}}}" style="width:100%; max-width:350px; border-radius:20px; box-shadow: 0 10px 20px rgba(0,0,0,0.5);">
                <h2>{{{{movie.name}}}}</h2>
                <p>👁️ Views: {{{{movie.views}}}} | 📅 {{{{movie.created_at.strftime('%Y-%m-%d') if movie.created_at else ''}}}}</p>
                <hr style="border:0.5px solid #334155;">
                <div style="margin-top:20px;">
                    {{% for ep in movie.episodes %}}
                        <div style="margin-bottom:15px;">
                            {ad_script}
                            <a href="{{{{ep}}}}" class="btn">▶️ Play Episode {{{{loop.index}}}}</a>
                        </div>
                    {{% endfor %}}
                </div>
                <br><a href="/" class="btn" style="background:#475569;">🔙 হোমপেজে ফিরুন</a>
            </div>
        </body></html>
    """, movie=movie)

# --- 💰 কয়েন ও টাস্ক ---
@app.route('/tasks')
def tasks():
    user = get_user()
    if not user: return redirect('/login')
    lt = list(link_tasks_col.find())
    at = list(ad_tasks_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <div class="container">
                <h2>🤑 কয়েন ইনকাম করুন</h2>
                <div class="card" style="padding:15px; text-align:center; margin-bottom:20px; border-color:gold;">
                    💰 বর্তমান ব্যালেন্স: <b>{{{{user.coins}}}} কয়েন</b>
                </div>
                <h4>🔗 লিঙ্ক টাস্ক</h4>
                {{% for t in lt %}}
                <div class="card" style="padding:15px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                    <span><b>{{{{t.name}}}}</b> (+💰{{{{t.coins}}}})</span>
                    <a href="{{{{t.link}}}}" class="btn" style="width:auto; padding:5px 15px;" onclick="fetch('/claim/link/{{{{t._id}}}}')">Complete</a>
                </div>
                {{% endfor %}}
                <h4>📺 ভিডিও এড টাস্ক</h4>
                {{% for t in at %}}
                <div class="card" style="padding:15px; margin-bottom:10px;">
                    <p><b>{{{{t.name}}}}</b> (+💰{{{{t.coins}}}})</p>
                    <button class="btn" onclick="showAd('{{{{t.zone_id}}}}', '{{{{t._id}}}}')">📽️ Watch Ad</button>
                    <div id="ad-{{{{t._id}}}}"></div>
                </div>
                {{% endfor %}}
            </div>
            <script>
                function showAd(z, i) {{
                    document.getElementById('ad-'+i).innerHTML = `<script src='//libtl.com/sdk.js' data-zone='${{z}}' data-sdk='show_${{z}}'><\/script>`;
                    fetch('/claim/ad/'+i);
                }}
            </script>
            {bottom_nav('/tasks')}
        </body></html>
    """, user=user, lt=lt, at=at)

@app.route('/claim/<type>/<tid>')
def claim(type, tid):
    user = get_user()
    col = link_tasks_col if type == "link" else ad_tasks_col
    t = col.find_one({"_id": ObjectId(tid)})
    if t and user: users_col.update_one({"_id": user['_id']}, {"$inc": {"coins": int(t['coins'])}})
    return "OK"

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = get_user()
    if not user: return redirect('/login')
    if request.method == 'POST':
        upd = {"fname": request.form.get('fname'), "lname": request.form.get('lname')}
        if request.form.get('p'): upd["password"] = generate_password_hash(request.form.get('p'))
        users_col.update_one({"_id": user['_id']}, {"$set": upd}); return redirect('/profile')
    
    status = "🌟 Premium" if is_premium(user) else "🆓 Free Member"
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <div class="container">
                <div class="card" style="text-align:center; padding:30px;">
                    <h2>{{{{user.fname}}}} {{{{user.lname}}}}</h2>
                    <p>📱 {{{{user.mobile}}}}</p>
                    <p style="color:var(--primary); font-size:22px;">💰 {{{{user.coins}}}} কয়েন</p>
                    <span style="background:green; padding:5px 15px; border-radius:8px;">{status}</span>
                </div>
                <form class="card" style="padding:20px; margin-top:20px;" method="post">
                    <h3>🛠 প্রোফাইল আপডেট</h3>
                    <input name="fname" value="{{{{user.fname}}}}">
                    <input name="lname" value="{{{{user.lname}}}}">
                    <input type="password" name="p" placeholder="নতুন পাসওয়ার্ড (ঐচ্ছিক)">
                    <button class="btn">✅ আপডেট করুন</button>
                </form>
                <a href="/logout" class="btn btn-red" style="margin-top:20px;">🚪 লগআউট</a>
            </div>
            {bottom_nav('/profile')}
        </body></html>
    """, user=user)

@app.route('/premium')
def premium_store():
    user = get_current_user_if_exists() # Simplified helper check
    if not 'uid' in session: return redirect('/login')
    pkgs = list(packages_col.find())
    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body>
            <div class="container">
                <h2>💎 প্রিমিয়াম স্টোর</h2>
                <p>প্যাকেজ কিনলে মুভি দেখার সময় কোনো এড আসবে না।</p>
                {{% for p in pkgs %}}
                <div class="card" style="padding:20px; margin-bottom:15px; text-align:center; border: 2px solid gold;">
                    <h2 style="color:gold;">{{{{p.name}}}}</h2>
                    <p>⏳ মেয়াদ: {{{{p.days}}}} দিন | 💰 মূল্য: {{{{p.coins}}}} কয়েন</p>
                    <a href="/buy_pkg/{{{{p._id}}}}" class="btn">🔥 এখনই কিনুন</a>
                </div>
                {{% endfor %}}
            </div>
            {bottom_nav('/premium')}
        </body></html>
    """, pkgs=pkgs)

@app.route('/buy_pkg/<pid>')
def buy_pkg(pid):
    user = get_user()
    p = packages_col.find_one({"_id": ObjectId(pid)})
    if user and p and user['coins'] >= int(p['coins']):
        expiry = max(user.get('premium_until', datetime.utcnow()), datetime.utcnow()) + timedelta(days=int(p['days']))
        users_col.update_one({"_id": user['_id']}, {"$set": {"premium_until": expiry}, "$inc": {"coins": -int(p['coins'])}})
    return redirect('/premium')

def bottom_nav(active):
    return f"""
    <div class="bottom-nav">
        <a href="/" class="{'active' if active=='/' else ''}">🏠 হোম</a>
        <a href="/tasks" class="{'active' if active=='/tasks' else ''}">💰 ইনকাম</a>
        <a href="/premium" class="{'active' if active=='/premium' else ''}">💎 প্রিমিয়াম</a>
        <a href="/profile" class="{'active' if active=='/profile' else ''}">👤 প্রোফাইল</a>
    </div>
    """

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

# --- ⚡ এডমিন প্যানেল (ফিক্সড টাস্ক এড/ডিলিট ও জোন আইডি) ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        if request.method == 'POST' and request.form.get('p') == ADMIN_PASS:
            session['admin'] = True; return redirect('/admin')
        return "<html><body style='background:#0f172a;color:white;padding:50px;text-align:center;'><form method='post'><h2>🔑 এডমিন লগইন</h2><input type='password' name='p'><button class='btn'>Login</button></form></body></html>"
    
    if request.method == 'POST':
        a = request.form.get('a')
        if a == "site":
            settings_col.update_one({"key": "site_config"}, {"$set": {
                "site_name": request.form.get('sn'), 
                "notice": request.form.get('nt'),
                "zone_id": request.form.get('zid')
            }})
        elif a == "add_link":
            link_tasks_col.insert_one({"name": request.form.get('n'), "link": request.form.get('l'), "coins": int(request.form.get('c'))})
        elif a == "add_ad":
            ad_tasks_col.insert_one({"name": request.form.get('n'), "zone_id": request.form.get('z'), "coins": int(request.form.get('c'))})
        elif a == "add_pkg":
            packages_col.insert_one({"name": request.form.get('n'), "days": int(request.form.get('d')), "coins": int(request.form.get('c'))})
        elif a == "del_m": movies_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        elif a == "del_l": link_tasks_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        elif a == "del_a": ad_tasks_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        elif a == "del_p": packages_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        return redirect('/admin')

    conf = get_site_conf()
    movies = list(movies_col.find())
    lt = list(link_tasks_col.find())
    at = list(ad_tasks_col.find())
    pkgs = list(packages_col.find())

    return render_template_string(f"""
        <html><head><meta name='viewport' content='width=device-width, initial-scale=1'>{STYLE}</head><body style="padding:20px;">
            <h2>🛠️ এডমিন ড্যাশবোর্ড</h2>
            
            <div class="card" style="padding:15px;">
                <h3>⚙️ সাইট সেটিংস</h3>
                <form method="post"><input type="hidden" name="a" value="site">
                    নাম: <input name="sn" value="{conf['site_name']}">
                    নোটিশ: <input name="nt" value="{conf['notice']}">
                    মুভি এড জোন আইডি (Zone ID): <input name="zid" value="{conf.get('zone_id', '')}">
                    <button class="btn">Settings Update</button>
                </form>
            </div>

            <div class="card" style="padding:15px; margin-top:20px;">
                <h3>🔗 লিঙ্ক টাস্ক এড করুন</h3>
                <form method="post"><input type="hidden" name="a" value="add_link">
                    <input name="n" placeholder="টাস্ক নাম">
                    <input name="l" placeholder="লিঙ্ক">
                    <input name="c" placeholder="কয়েন">
                    <button class="btn">Add Link Task</button>
                </form>
            </div>

            <div class="card" style="padding:15px; margin-top:20px;">
                <h3>📺 এড টাস্ক এড করুন</h3>
                <form method="post"><input type="hidden" name="a" value="add_ad">
                    <input name="n" placeholder="টাস্ক নাম">
                    <input name="z" placeholder="Zone ID">
                    <input name="c" placeholder="কয়েন">
                    <button class="btn">Add Ad Task</button>
                </form>
            </div>

            <div class="card" style="padding:15px; margin-top:20px;">
                <h3>🛒 মুভি ও টাস্ক ম্যানেজমেন্ট</h3>
                <h4>লিঙ্ক টাস্কসমূহ:</h4>
                {{% for t in lt %}}
                <p>{{{{t.name}}}} <form method="post" style="display:inline;"><input type="hidden" name="a" value="del_l"><input type="hidden" name="id" value="{{{{t._id}}}}"><button style="color:red">Del</button></form></p>
                {{% endfor %}}
                <h4>এড টাস্কসমূহ:</h4>
                {{% for t in at %}}
                <p>{{{{t.name}}}} <form method="post" style="display:inline;"><input type="hidden" name="a" value="del_a"><input type="hidden" name="id" value="{{{{t._id}}}}"><button style="color:red">Del</button></form></p>
                {{% endfor %}}
                <h4>মুভিসমূহ:</h4>
                {{% for m in movies %}}
                <p>{{{{m.name}}}} (👁️{{{{m.views}}}}) <form method="post" style="display:inline;"><input type="hidden" name="a" value="del_m"><input type="hidden" name="id" value="{{{{m._id}}}}"><button style="color:red">Del</button></form></p>
                {{% endfor %}}
            </div>
            <br><a href="/logout" class="btn btn-red">Logout Admin</a>
        </body></html>
    """, conf=conf, movies=movies, lt=lt, at=at, pkgs=pkgs)

# --- 🤖 টেলিগ্রাম বট ---
bot = Client("ProMovieBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
st = {}

@bot.on_message(filters.command("movie") & filters.user(ADMIN_ID))
async def add_m(c, m):
    st[m.from_user.id] = {"step": "name", "eps": []}
    await m.reply_text("🎬 মুভির নাম দিন:")

@bot.on_message(filters.text & filters.user(ADMIN_ID))
async def handle_m(c, m):
    uid = m.from_user.id
    if uid not in st: return
    if st[uid]["step"] == "name":
        st[uid]["name"] = m.text; st[uid]["step"] = "poster"
        await m.reply_text("🖼️ মুভির পোস্টার ডিরেক্ট URL দিন:")
    elif st[uid]["step"] == "poster":
        st[uid]["poster"] = m.text; st[uid]["step"] = "eps"
        await m.reply_text("🔗 এপিসোড বা ফাইল লিঙ্ক দিন। শেষ হলে Done বাটনে ক্লিক করুন।", 
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Done ✅", callback_data="save")]]))
    elif st[uid]["step"] == "eps":
        st[uid]["eps"].append(m.text); await m.reply_text(f"✅ ইপিসোড {len(st[uid]['eps'])} এড হয়েছে।")

@bot.on_callback_query(filters.regex("save"))
async def save_m(c, q):
    uid = q.from_user.id
    d = st.get(uid)
    if d:
        movies_col.insert_one({"name": d["name"], "poster": d["poster"], "episodes": d["eps"], "views": 0, "created_at": datetime.utcnow()})
        await q.message.edit_text(f"🚀 '{d['name']}' সফলভাবে সাইটে আপলোড হয়েছে!"); del st[uid]

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.run()).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
