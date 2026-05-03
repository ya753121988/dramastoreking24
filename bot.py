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
db = client['MoviePremiumDB']
movies_col = db['movies']
users_col = db['users']
link_tasks_col = db['link_tasks']
ad_tasks_col = db['ad_tasks']
packages_col = db['packages']
settings_col = db['settings']

# 🛠️ ডিফল্ট সেটিংস
if not settings_col.find_one({"key": "config"}):
    settings_col.insert_one({
        "key": "config",
        "site_name": "Premium Cinema",
        "notice": "🌟 আমাদের মুভি পোর্টালে স্বাগতম! টাস্ক কমপ্লিট করে কয়েন ইনকাম করুন।"
    })

app = Flask(__name__)
app.secret_key = "super_secret_key_pro"

# --- 🎨 প্রিমিয়াম সিএসএস স্টাইল ---
STYLE = """
<style>
    :root { --primary: #00d2ff; --secondary: #3a7bd5; --dark: #0f172a; --card: #1e293b; --text: #f8fafc; }
    body { background: var(--dark); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; padding-bottom: 80px; overflow-x: hidden; }
    header { background: linear-gradient(90deg, var(--primary), var(--secondary)); padding: 15px; text-align: center; font-size: 22px; font-weight: bold; position: sticky; top: 0; z-index: 1000; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .notice-bar { background: #334155; padding: 8px; font-size: 13px; text-align: center; border-bottom: 1px solid var(--primary); }
    .container { padding: 15px; max-width: 1200px; margin: auto; }
    
    /* 🎞️ স্লাইডার স্টাইল */
    .slider { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 15px; padding: 10px 0; scrollbar-width: none; }
    .slider-item { flex: 0 0 160px; scroll-snap-align: start; position: relative; transition: 0.3s; }
    .slider-item img { width: 100%; height: 230px; border-radius: 15px; object-fit: cover; border: 2px solid #334155; }
    .top-badge { position: absolute; top: 8px; left: 8px; background: gold; color: black; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; }

    /* 📦 গ্রিড ও কার্ড */
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 15px; margin-top: 20px; }
    .card { background: var(--card); border-radius: 15px; overflow: hidden; border: 1px solid #334155; text-decoration: none; color: inherit; transition: 0.3s; }
    .card:hover { transform: scale(1.03); border-color: var(--primary); }
    .card img { width: 100%; height: 200px; object-fit: cover; }
    .card h3 { font-size: 13px; padding: 10px; margin: 0; text-align: center; }
    
    .btn { background: linear-gradient(90deg, var(--primary), var(--secondary)); color: white; padding: 12px; border-radius: 10px; text-decoration: none; display: block; text-align: center; border: none; font-weight: bold; cursor: pointer; margin: 5px 0; }
    .btn-red { background: #ef4444; }
    input { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #334155; background: #0f172a; color: white; box-sizing: border-box; margin-bottom: 15px; }
    
    .bottom-nav { position: fixed; bottom: 0; width: 100%; background: var(--card); display: flex; justify-content: space-around; padding: 12px 0; border-top: 1px solid #334155; box-shadow: 0 -5px 15px rgba(0,0,0,0.2); }
    .bottom-nav a { color: #94a3b8; text-decoration: none; font-size: 13px; text-align: center; font-weight: bold; }
    .bottom-nav a.active { color: var(--primary); }
</style>
"""

# --- 🛠️ হেল্পার ফাংশন ---
def get_conf(): return settings_col.find_one({"key": "config"})
def get_user():
    if 'uid' in session: return users_col.find_one({"_id": ObjectId(session['uid'])})
    return None
def is_premium(user):
    if not user or 'premium_until' not in user: return False
    return user['premium_until'] > datetime.utcnow()

# --- 🔐 রেজিস্ট্রেশন ও লগইন ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname, lname, mobile = request.form.get('fname'), request.form.get('lname'), request.form.get('mobile')
        password = generate_password_hash(request.form.get('password'))
        if users_col.find_one({"mobile": mobile}): flash("❌ নম্বরটি ইতিমধ্যে নিবন্ধিত!")
        else:
            users_col.insert_one({"fname": fname, "lname": lname, "mobile": mobile, "password": password, "coins": 0, "premium_until": datetime.utcnow()})
            return redirect('/login')
    return render_template_string(f"<html><head>{STYLE}</head><body><div class='container'><h2>💎 Register</h2><form method='post'><input name='fname' placeholder='First Name' required><input name='lname' placeholder='Last Name' required><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>🚀 Register Now</button></form><br><a href='/login' style='color:gray;text-decoration:none;'>লগইন করুন</a></div></body></html>")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({"mobile": request.form.get('mobile')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['uid'] = str(user['_id'])
            return redirect('/')
        flash("❌ মোবাইল নম্বর বা পাসওয়ার্ড ভুল!")
    return render_template_string(f"<html><head>{STYLE}</head><body><div class='container'><h2>🔑 Login</h2><form method='post'><input name='mobile' placeholder='Mobile Number' required><input type='password' name='password' placeholder='Password' required><button class='btn'>🔓 Login</button></form><br><a href='/register' style='color:gray;text-decoration:none;'>নতুন অ্যাকাউন্ট খুলুন</a></div></body></html>")

# --- 🏠 হোমপেজ ---
@app.route('/')
def home():
    user = get_user()
    if not user: return redirect('/login')
    conf = get_conf()
    
    top_movies = list(movies_col.find().sort("views", -1).limit(10))
    page = request.args.get('page', 1, type=int)
    all_movies = list(movies_col.find().sort("_id", -1).skip((page-1)*30).limit(30))
    total_pages = math.ceil(movies_col.count_documents({}) / 30)
    
    return render_template_string(f"""
        <html><head><title>{conf['site_name']}</title>{STYLE}</head><body>
            <header>💎 {conf['site_name']}</header>
            <div class="notice-bar"><marquee>{conf['notice']}</marquee></div>
            <div class="container">
                <h3>👑 Top 10 Viewed Movies</h3>
                <div class="slider">
                    {{% for m in top_movies %}}
                    <a href="/movie/{{{{m._id}}}}" class="slider-item">
                        <span class="top-badge">⭐ TOP {{{{loop.index}}}}</span>
                        <img src="{{{{m.poster}}}}">
                    </a>
                    {{% endfor %}}
                </div>
                <h3>🎬 All Movies</h3>
                <div class="grid">
                    {{% for m in all_movies %}}
                    <a href="/movie/{{{{m._id}}}}" class="card">
                        <img src="{{{{m.poster}}}}">
                        <h3>{{{{m.name}}}}</h3>
                    </a>
                    {{% endfor %}}
                </div>
                <div style="text-align:center; margin-top:20px;">
                    {{% if page > 1 %}}<a href="/?page={{{{page-1}}}}" class="btn" style="display:inline-block;width:80px;">Prev</a>{{% endif %}}
                    {{% if page < total_pages %}}<a href="/?page={{{{page+1}}}}" class="btn" style="display:inline-block;width:80px;">Next</a>{{% endif %}}
                </div>
            </div>
            {bot_nav('/')}
        </body></html>
    """, top_movies=top_movies, all_movies=all_movies, page=page, total_pages=total_pages)

# --- 🎥 মুভি ডিটেইলস ---
@app.route('/movie/<id>')
def movie_detail(id):
    user = get_user()
    if not user: return redirect('/login')
    movies_col.update_one({"_id": ObjectId(id)}, {"$inc": {"views": 1}})
    movie = movies_col.find_one({"_id": ObjectId(id)})
    premium = is_premium(user)
    ad_tag = "<script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>" if not premium else ""

    return render_template_string(f"""
        <html><head>{STYLE}</head><body>
            <div class="container" style="text-align:center;">
                <img src="{{{{movie.poster}}}}" style="width:100%; border-radius:20px; max-width:400px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <h2 style="margin-top:20px;">{{{{movie.name}}}}</h2>
                <p>📈 Views: {{{{movie.views}}}}</p>
                <div style="margin-top:30px;">
                    {{% for ep in movie.episodes %}}
                        <div style="margin-bottom:15px;">
                            {ad_tag}
                            <a href="{{{{ep}}}}" class="btn">🚀 Watch Episode {{{{loop.index}}}}</a>
                        </div>
                    {{% endfor %}}
                </div>
                <br><a href="/" class="btn" style="background:#475569;">🔙 Back Home</a>
            </div>
        </body></html>
    """, movie=movie)

# --- 💰 টাস্ক ও কয়েন ---
@app.route('/tasks')
def tasks():
    user = get_user()
    if not user: return redirect('/login')
    lt = list(link_tasks_col.find())
    at = list(ad_tasks_col.find())
    return render_template_string(f"""
        <html><head>{STYLE}</head><body>
            <div class="container">
                <h2>🤑 Earn Unlimited Coins</h2>
                <h4>🔗 Link Tasks</h4>
                {{% for t in lt %}}
                <div class="card" style="padding:15px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                    <span>{{{{t.name}}}} (💰{{{{t.coins}}}})</span>
                    <a href="{{{{t.link}}}}" class="btn" style="width:auto; padding:5px 15px;" onclick="fetch('/claim/link/{{{{t._id}}}}')">Complete</a>
                </div>
                {{% endfor %}}
                <h4>📺 Ad Tasks</h4>
                {{% for t in at %}}
                <div class="card" style="padding:15px; margin-bottom:10px;">
                    <p>{{{{t.name}}}} (💰{{{{t.coins}}}})</p>
                    <button class="btn" onclick="showAd('{{{{t.zone_id}}}}', '{{{{t._id}}}}')">📽 Watch Video Ad</button>
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
            {bot_nav('/tasks')}
        </body></html>
    """, lt=lt, at=at)

@app.route('/claim/<type>/<tid>')
def claim(type, tid):
    user = get_user()
    col = link_tasks_col if type == "link" else ad_tasks_col
    t = col.find_one({"_id": ObjectId(tid)})
    if t and user: users_col.update_one({"_id": user['_id']}, {"$inc": {"coins": int(t['coins'])}})
    return "OK"

# --- 👤 প্রোফাইল ---
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = get_user()
    if not user: return redirect('/login')
    if request.method == 'POST':
        upd = {"fname": request.form.get('fname'), "lname": request.form.get('lname')}
        if request.form.get('pass'): upd["password"] = generate_password_hash(request.form.get('pass'))
        users_col.update_one({"_id": user['_id']}, {"$set": upd})
        return redirect('/profile')
    
    status = "🌟 Premium" if is_premium(user) else "🆓 Free Member"
    return render_template_string(f"""
        <html><head>{STYLE}</head><body>
            <div class="container">
                <div class="card" style="text-align:center; padding:30px;">
                    <h2 style="margin:0;">{{{{user.fname}}}} {{{{user.lname}}}}</h2>
                    <p style="color:var(--primary); font-size:20px;">💰 Balance: {{{{user.coins}}}} Coins</p>
                    <span style="background:green; padding:5px 12px; border-radius:8px;">{status}</span>
                </div>
                <form class="card" style="padding:20px; margin-top:20px;" method="post">
                    <h3>🛠 Edit Profile</h3>
                    <input name="fname" value="{{{{user.fname}}}}">
                    <input name="lname" value="{{{{user.lname}}}}">
                    <input type="password" name="pass" placeholder="নতুন পাসওয়ার্ড (ঐচ্ছিক)">
                    <button class="btn">✅ Update Changes</button>
                </form>
                <a href="/logout" class="btn btn-red" style="margin-top:20px;">🚪 Logout</a>
            </div>
            {bot_nav('/profile')}
        </body></html>
    """, user=user)

# --- 🛒 প্রিমিয়াম শপ ---
@app.route('/buy-premium')
def shop():
    user = get_user()
    if not user: return redirect('/login')
    pkgs = list(packages_col.find())
    return render_template_string(f"""
        <html><head>{STYLE}</head><body>
            <div class="container">
                <h2>💎 Premium Store</h2>
                <p>প্যাকেজ কিনলে মুভি বাটনে কোনো অ্যাড আসবে না!</p>
                {{% for p in pkgs %}}
                <div class="card" style="padding:20px; margin-bottom:15px; text-align:center; border: 2px solid gold;">
                    <h2 style="color:gold;">{{{{p.name}}}}</h2>
                    <p>⏳ মেয়াদ: {{{{p.days}}}} দিন</p>
                    <p>💰 মূল্য: {{{{p.coins}}}} কয়েন</p>
                    <a href="/purchase/{{{{p._id}}}}" class="btn">🔥 Buy Now</a>
                </div>
                {{% endfor %}}
            </div>
            {bot_nav('/buy-premium')}
        </body></html>
    """, pkgs=pkgs)

@app.route('/purchase/<pid>')
def purchase(pid):
    user = get_user()
    p = packages_col.find_one({"_id": ObjectId(pid)})
    if user and p and user['coins'] >= int(p['coins']):
        now = max(user.get('premium_until', datetime.utcnow()), datetime.utcnow())
        expiry = now + timedelta(days=int(p['days']))
        users_col.update_one({"_id": user['_id']}, {"$set": {"premium_until": expiry}, "$inc": {"coins": -int(p['coins'])}})
        flash("🎉 Premium Activated!")
    return redirect('/buy-premium')

def bot_nav(active):
    return f"""
    <div class="bottom-nav">
        <a href="/" class="{'active' if active=='/' else ''}">🏠 Home</a>
        <a href="/tasks" class="{'active' if active=='/tasks' else ''}">💰 Earn</a>
        <a href="/buy-premium" class="{'active' if active=='/buy-premium' else ''}">💎 Shop</a>
        <a href="/profile" class="{'active' if active=='/profile' else ''}">👤 Me</a>
    </div>
    """

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

# --- ⚡ এডমিন প্যানেল ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        if request.method == 'POST' and request.form.get('p') == ADMIN_PASS:
            session['admin'] = True; return redirect('/admin')
        return "<html><body style='background:#0f172a;color:white;padding:50px;'><form method='post'><h2>🔑 Admin</h2><input type='password' name='p'><button class='btn'>Login</button></form></body></html>"
    
    conf = get_conf()
    if request.method == 'POST':
        action = request.form.get('a')
        if action == "site": settings_col.update_one({"key": "config"}, {"$set": {"site_name": request.form.get('n'), "notice": request.form.get('nt')}})
        elif action == "pkg": packages_col.insert_one({"name": request.form.get('n'), "days": request.form.get('d'), "coins": request.form.get('c')})
        elif action == "link": link_tasks_col.insert_one({"name": request.form.get('n'), "link": request.form.get('l'), "coins": request.form.get('c')})
        elif action == "ad": ad_tasks_col.insert_one({"name": request.form.get('n'), "zone_id": request.form.get('z'), "coins": request.form.get('c')})
        elif action == "del_m": movies_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        elif action == "del_pkg": packages_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        elif action == "del_link": link_tasks_col.delete_one({"_id": ObjectId(request.form.get('id'))})
        return redirect('/admin')

    return render_template_string(f"""
        <html><head>{STYLE}</head><body style="padding:20px;">
            <h2>🛠 Admin Panel</h2>
            <div class="card" style="padding:15px;">
                <h3>⚙️ Settings</h3>
                <form method="post"><input type="hidden" name="a" value="site">
                    Name: <input name="n" value="{conf['site_name']}">
                    Notice: <input name="nt" value="{conf['notice']}">
                    <button class="btn">Update</button>
                </form>
            </div>
            <div class="card" style="padding:15px; margin-top:20px;">
                <h3>📦 Add Package</h3>
                <form method="post"><input type="hidden" name="a" value="pkg">
                    <input name="n" placeholder="Package Name">
                    <input name="d" placeholder="Days">
                    <input name="c" placeholder="Price Coins">
                    <button class="btn">Add Pkg</button>
                </form>
            </div>
            <div class="card" style="padding:15px; margin-top:20px;">
                <h3>🔗 Add Link Task</h3>
                <form method="post"><input type="hidden" name="a" value="link">
                    <input name="n" placeholder="Task Name">
                    <input name="l" placeholder="Direct Link">
                    <input name="c" placeholder="Reward Coins">
                    <button class="btn">Add Link Task</button>
                </form>
            </div>
            <div class="card" style="padding:15px; margin-top:20px;">
                <h3>🗑 Delete Movies</h3>
                {{% for m in movies %}}
                <p>{{{{m.name}}}} <form method="post" style="display:inline;"><input type="hidden" name="a" value="del_m"><input type="hidden" name="id" value="{{{{m._id}}}}"><button style="color:red;">Del</button></form></p>
                {{% endfor %}}
            </div>
        </body></html>
    """, movies=list(movies_col.find()))

# --- 🤖 টেলিগ্রাম বট লজিক ---
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
        await m.reply_text("🖼 পোস্টার URL দিন:")
    elif st[uid]["step"] == "poster":
        st[uid]["poster"] = m.text; st[uid]["step"] = "eps"
        await m.reply_text("🔗 এপিসোড লিঙ্ক দিন (একটা একটা করে)। শেষ হলে Done দিন।", 
                           reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Done ✅", callback_data="save")]]))
    elif st[uid]["step"] == "eps":
        st[uid]["eps"].append(m.text)
        await m.reply_text(f"✅ এপিসোড {len(st[uid]['eps'])} যুক্ত হয়েছে।")

@bot.on_callback_query(filters.regex("save"))
async def save_m(c, q):
    uid = q.from_user.id
    d = st.get(uid)
    if d:
        movies_col.insert_one({"name": d["name"], "poster": d["poster"], "episodes": d["eps"], "views": 0})
        await q.message.edit_text("🚀 মুভিটি সফলভাবে লাইভ হয়েছে!")
        del st[uid]

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.run()).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
