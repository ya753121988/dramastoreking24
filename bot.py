import os
import telebot
import random
import string
from pymongo import MongoClient
from flask import Flask, jsonify, request, render_template_string, redirect, make_response, session
from flask_cors import CORS
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from threading import Thread

# ==========================================
# ১. কনফিগারেশন ও ডাটাবেস সেটআপ
# ==========================================
BOT_TOKEN = "8655043839:AAGMxkYoZXR-nUzlcapZZfVwci09Z6x0-UE"
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0"
FILE_CHANNEL_ID = -1003985353441 
ADMIN_IDS = [7120801813]
ADMIN_PASS = "admin7120" # অ্যাডমিন প্যানেল লগইন পাসওয়ার্ড

client = MongoClient(MONGO_URI)
db = client["movie_db"]
movies_col = db["movies"]
settings_col = db["settings"]
users_col = db["users"]
tasks_col = db["tasks"]
monetag_tasks_col = db["monetag_tasks"]
plans_col = db["premium_plans"]
otp_col = db["otps"]
ep_ads_col = db["episode_ads"] 
ep_unlock_col = db["episode_unlocks"]
user_tasks_history = db["user_tasks_history"]

app = Flask(__name__)
app.secret_key = "ultimate_secret_key_7120"
CORS(app)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# ডিফল্ট কনফিগারেশন চেক
def init_db():
    if not settings_col.find_one({"type": "site_config"}):
        settings_col.insert_one({
            "type": "site_config", "site_name": "Premium Movies", 
            "site_logo": "https://via.placeholder.com/200x60?text=LOGO",
            "header_notice": "আমাদের সাইটে স্বাগতম! একাউন্ট খুলে মুভি দেখুন। 🍿",
            "movies_per_page": 12
        })
    if not ep_ads_col.find_one({"type": "ep_ad_config"}):
        ep_ads_col.insert_one({
            "type": "ep_ad_config", "direct_link": "", "monetag_id": "",
            "unlock_minutes": 30, "active_type": "off", "daily_limit": 10
        })

init_db()

# ==========================================
# ২. রেসপনসিভ ডিজাইন (CSS)
# ==========================================
COMMON_CSS = """
<style>
    :root { --primary: #3b82f6; --bg: #0b0f19; --glass: rgba(30, 41, 59, 0.7); }
    body { background: var(--bg); color: white; font-family: 'Inter', sans-serif; margin:0; padding:0; }
    .glass { background: var(--glass); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); }
    .btn-blue { background: var(--primary); color: white; border-radius: 12px; font-weight: bold; padding: 12px; border:none; cursor:pointer; width:100%; transition: 0.3s; }
    .movie-card img { transition: 0.5s; width:100%; aspect-ratio: 2/3; object-fit:cover; border-radius: 20px; }
    .movie-card:hover img { transform: scale(1.05); }
    .marquee { background: rgba(59, 130, 246, 0.1); padding: 10px 0; overflow: hidden; border-bottom: 1px solid rgba(255,255,255,0.05); }
    .marquee p { display: inline-block; animation: marquee 20s linear infinite; font-size: 13px; color: #fbbf24; margin:0; white-space: nowrap; }
    @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; display: flex; justify-content: space-around; padding: 12px; z-index: 100; border-top: 1px solid rgba(255,255,255,0.1); background: rgba(11, 15, 25, 0.9); }
    .bottom-nav a { text-decoration: none; color: #94a3b8; font-size: 10px; text-align: center; font-weight: bold; }
    .bottom-nav a.active { color: #3b82f6; }
    input, textarea, select { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: white; padding: 12px; border-radius: 12px; outline: none; width:100%; }
</style>
"""

# ==========================================
# ৩. ইউজার প্যানেল HTML ডিজাইনসমূহ
# ==========================================

USER_LAYOUT = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
""" + COMMON_CSS + """</head><body class="pb-24">
<header class="glass sticky top-0 z-50 p-4 flex justify-between items-center">
    <img src="{{ config.site_logo }}" class="h-8">
    <div class="text-right"><span class="text-blue-400 font-bold block text-sm">{{ config.site_name }}</span></div>
</header>
<div class="marquee"><p>📢 {{ config.header_notice }}</p></div>
<main class="p-4 container mx-auto">{% block content %}{% endblock %}</main>
<nav class="glass bottom-nav">
    <a href="/" class="{{ 'active' if act == 'home' }}"><i class="fas fa-home text-xl"></i><br>HOME</a>
    <a href="/tasks" class="{{ 'active' if act == 'task' }}"><i class="fas fa-tasks text-xl"></i><br>TASK</a>
    <a href="/premium" class="{{ 'active' if act == 'premium' }}"><i class="fas fa-crown text-xl"></i><br>PREMIUM</a>
    <a href="/profile" class="{{ 'active' if act == 'profile' }}"><i class="fas fa-user text-xl"></i><br>PROFILE</a>
</nav>
</body></html>
"""

# ==========================================
# ৪. ইউজার এন্ডপয়েন্টস (লগইন, রেজিস্টার, মুভি, প্রোফাইল)
# ==========================================

def get_user():
    mob = request.cookies.get('mobile')
    return users_col.find_one({"mobile": str(mob)}) if mob else None

@app.route('/')
def user_index():
    u = get_user()
    if not u: return redirect('/login')
    c = settings_col.find_one({"type":"site_config"})
    page = int(request.args.get('page', 1))
    movies = list(movies_col.find().sort('_id', -1).skip((page-1)*c['movies_per_page']).limit(c['movies_per_page']))
    for m in movies: m['_id'] = str(m['_id'])
    return render_template_string(USER_LAYOUT + """
    {% block content %}
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {% for m in movies %}
        <a href="/movie/{{ m._id }}" class="movie-card glass rounded-3xl overflow-hidden block">
            <img src="{{ m.poster }}">
            <div class="p-3"><h3 class="text-[11px] font-bold truncate">{{ m.title }}</h3><p class="text-[9px] text-blue-400 uppercase">{{ m.category }}</p></div>
        </a>
        {% endfor %}
    </div>
    <div class="mt-10 flex justify-center gap-4 items-center">
        {% if page > 1 %}<a href="/?page={{ page-1 }}" class="glass px-4 py-2 rounded-xl text-xs">⬅️ Preview</a>{% endif %}
        <span class="text-blue-400 font-bold text-sm">🔢 {{ page }}</span>
        <a href="/?page={{ page+1 }}" class="glass px-4 py-2 rounded-xl text-xs">Next ➡️</a>
    </div>
    {% endblock %}""", act='home', config=c, movies=movies, page=page, user=u)

@app.route('/movie/<id>')
def movie_details(id):
    u = get_user()
    if not u: return redirect('/login')
    m = movies_col.find_one({"_id": ObjectId(id)})
    c = settings_col.find_one({"type":"site_config"})
    return render_template_string(USER_LAYOUT + """
    {% block content %}
    <div class="max-w-4xl mx-auto flex flex-col md:flex-row gap-8">
        <img src="{{ m.poster }}" class="w-full md:w-64 rounded-3xl shadow-2xl border border-white/10">
        <div class="flex-1">
            <h1 class="text-3xl font-black mb-2">{{ m.title }}</h1>
            <span class="bg-blue-600 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest">{{ m.category }}</span>
            <div class="mt-10">
                <h4 class="text-gray-400 font-bold mb-4 border-l-4 border-blue-500 pl-2 uppercase text-xs">Available Episodes:</h4>
                <div class="grid grid-cols-3 md:grid-cols-6 gap-3">
                    {% for ep in m.episodes %}
                    <button onclick="play('{{ ep.link }}')" class="glass p-3 rounded-xl text-[10px] font-bold border-b-2 border-blue-500 hover:bg-blue-600 transition">EP {{ loop.index }}</button>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    <script>
        async function play(link) {
            const r = await fetch('/api/check-access', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mobile:'{{ user.mobile }}'})});
            const d = await r.json();
            if(d.status === 'unlocked') { window.open(link, '_blank'); }
            else { 
                alert("⚠️ Ad Lock! বাটন আনলক করতে এড দেখুন। (৩০ মিনিট আনলক থাকবে)"); 
                if(d.ad_config.active_type === 'direct') { window.open(d.ad_config.direct_link, '_blank'); unlock(); }
                else if(d.ad_config.active_type === 'monetag') { /* Monetag Logic Here */ unlock(); }
            }
        }
        function unlock() { fetch('/api/unlock', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mobile:'{{ user.mobile }}'})}).then(()=>location.reload()); }
    </script>
    {% endblock %}""", act='home', config=c, m=m, user=u)

@app.route('/profile')
def profile():
    u = get_user()
    if not u: return redirect('/login')
    c = settings_col.find_one({"type":"site_config"})
    return render_template_string(USER_LAYOUT + """
    {% block content %}
    <div class="max-w-md mx-auto glass p-8 rounded-3xl text-center">
        <div class="w-20 h-20 bg-blue-600 rounded-full mx-auto flex items-center justify-center text-3xl font-bold mb-4">{{ u.first_name[0] }}</div>
        <h2 class="text-xl font-bold uppercase tracking-tight">{{ u.first_name }} {{ u.last_name }}</h2>
        <p class="text-xs text-gray-500 mb-6">📱 {{ u.mobile }}</p>
        <div class="grid grid-cols-2 gap-3 mb-8">
            <div class="bg-black/30 p-4 rounded-2xl"><p class="text-[9px] text-gray-500 uppercase">Balance</p><p class="text-lg font-black text-yellow-400">{{ u.balance }}</p></div>
            <div class="bg-black/30 p-4 rounded-2xl"><p class="text-[9px] text-gray-500 uppercase">Premium</p><p class="text-[10px] font-bold {{ 'text-green-400' if u.is_premium else 'text-red-400' }}">{{ 'ACTIVE' if u.is_premium else 'INACTIVE' }}</p></div>
        </div>
        <form action="/api/update-profile" method="POST" class="space-y-4 text-left">
            <input type="hidden" name="mobile" value="{{ u.mobile }}">
            <div><label class="text-[10px] text-gray-500 ml-1">Change First Name</label><input type="text" name="first_name" value="{{ u.first_name }}"></div>
            <div><label class="text-[10px] text-gray-500 ml-1">Update Password</label><input type="password" name="password" placeholder="New Password"></div>
            <button class="btn-blue mt-4">UPDATE PROFILE</button>
        </form>
        <a href="/logout" class="block mt-6 text-red-500 text-xs font-bold uppercase tracking-widest">Logout Account</a>
    </div>
    {% endblock %}""", act='profile', config=c, user=u)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mob = str(request.form.get('mobile'))
        pw = str(request.form.get('password'))
        u = users_col.find_one({"mobile": mob, "password": pw})
        if u:
            r = make_response(redirect('/'))
            r.set_cookie('mobile', mob, max_age=30*24*60*60); return r
        return "ভুল মোবাইল বা পাসওয়ার্ড! <a href='/login'>আবার চেষ্টা করুন</a>"
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">"""+COMMON_CSS+"""</head>
    <body class="flex items-center justify-center min-h-screen p-6"><div class="glass p-10 rounded-[40px] w-full max-w-sm text-center">
        <h1 class="text-3xl font-black text-blue-400 mb-8 uppercase tracking-tighter">User Login</h1>
        <form method="POST" class="space-y-4"><input type="text" name="mobile" placeholder="Mobile Number" required><input type="password" name="password" placeholder="Password" required><button class="btn-blue shadow-lg shadow-blue-500/20">LOGIN NOW</button></form>
        <p class="mt-8 text-xs text-gray-500">একাউন্ট নেই? <a href="/register" class="text-blue-400 font-bold">রেজিস্টার করুন</a></p>
        <p class="mt-2 text-[10px] text-gray-600"><a href="/forgot">পাসওয়ার্ড ভুলে গেছেন?</a></p>
    </div></body></html>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        mob = str(request.form.get('mobile'))
        if users_col.find_one({"mobile": mob}): return "এই নাম্বারটি ইতিমধ্যে নিবন্ধিত!"
        users_col.insert_one({"first_name":request.form.get('first_name'),"last_name":request.form.get('last_name'),"mobile":mob,"telegram_id":str(request.form.get('telegram_id')),"password":str(request.form.get('password')),"balance":0,"is_premium":False})
        return redirect('/login')
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">"""+COMMON_CSS+"""</head>
    <body class="flex items-center justify-center min-h-screen p-6"><div class="glass p-10 rounded-[40px] w-full max-w-sm text-center">
        <h1 class="text-3xl font-black text-green-400 mb-8 uppercase tracking-tighter">Register</h1>
        <form method="POST" class="space-y-4">
            <div class="flex gap-2"><input type="text" name="first_name" placeholder="First Name" required><input type="text" name="last_name" placeholder="Last Name" required></div>
            <input type="text" name="mobile" placeholder="Mobile Number" required>
            <input type="number" name="telegram_id" placeholder="Telegram ID (Bot থেকে নিন)" required>
            <input type="password" name="password" placeholder="Set Password" required>
            <button class="btn-blue bg-green-600 shadow-lg shadow-green-500/20">CREATE ACCOUNT</button>
        </form>
    </div></body></html>""")

# ==========================================
# ৫. মেগা অ্যাডমিন প্যানেল (সব ফিচার এক জায়গায়)
# ==========================================

ADMIN_PAGE = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
""" + COMMON_CSS + """</head><body class="flex flex-col md:flex-row min-h-screen">
<div class="w-full md:w-64 glass p-6 space-y-6">
    <h1 class="text-xl font-bold text-blue-400 text-center uppercase tracking-widest">Master Admin</h1>
    <nav class="flex flex-col gap-2 text-sm">
        <a href="/admin/dashboard" class="p-3 bg-white/5 rounded-xl"><i class="fas fa-home mr-3"></i> Dashboard</a>
        <a href="#movies" class="p-3 hover:bg-white/5 rounded-xl"><i class="fas fa-film mr-3"></i> Movie Database</a>
        <a href="#ep_ads" class="p-3 hover:bg-red-500/10 rounded-xl text-red-400 font-bold"><i class="fas fa-lock mr-3"></i> Ep Ad Lock</a>
        <a href="#tasks" class="p-3 hover:bg-green-500/10 rounded-xl text-green-400"><i class="fas fa-link mr-3"></i> Tasks & Coins</a>
        <a href="#plans" class="p-3 hover:bg-purple-500/10 rounded-xl text-purple-400 font-bold"><i class="fas fa-crown mr-3"></i> Premium Plans</a>
        <a href="#settings" class="p-3 hover:bg-white/5 rounded-xl"><i class="fas fa-cog mr-3"></i> Settings</a>
        <a href="/admin/logout" class="p-3 text-red-500 mt-10"><i class="fas fa-sign-out-alt mr-3"></i> Admin Logout</a>
    </nav>
</div>
<div class="flex-1 p-6 space-y-8 overflow-y-auto">
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="glass p-5 rounded-3xl text-center"><p class="text-[10px] text-gray-500 uppercase">Users</p><p class="text-2xl font-bold text-blue-400">{{ u_count }}</p></div>
        <div class="glass p-5 rounded-3xl text-center"><p class="text-[10px] text-gray-500 uppercase">Movies</p><p class="text-2xl font-bold text-green-400">{{ m_count }}</p></div>
    </div>

    <section id="movies" class="glass p-8 rounded-[35px] border-blue-500/20 border">
        <h2 class="text-xl font-bold mb-6 text-blue-400 border-b border-white/5 pb-2">Movie Range Uploader</h2>
        <form action="/admin/movie/add-range" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <input type="text" name="title" placeholder="Movie Name" class="md:col-span-2" required>
            <input type="number" name="start_id" placeholder="Start Msg ID" required>
            <input type="number" name="end_id" placeholder="End Msg ID" required>
            <button class="btn-blue bg-indigo-600 md:col-span-4">UPLOAD RANGE NOW</button>
        </form>
        <div class="overflow-x-auto"><table class="w-full text-left text-xs">
            <thead><tr class="text-gray-500"><th>TITLE</th><th>ACTION</th></tr></thead>
            <tbody>{% for m in movies %}<tr class="border-b border-white/5"><td>{{ m.title }}</td><td><a href="/admin/movie/delete/{{ m._id }}" class="text-red-500">Delete</a></td></tr>{% endfor %}</tbody>
        </table></div>
    </section>

    <section id="ep_ads" class="glass p-8 rounded-[35px] border-red-500/20 border">
        <h2 class="text-xl font-bold mb-6 text-red-400 border-b border-white/5 pb-2">Episode Ad Controller</h2>
        <form action="/admin/update-ep-ads" method="POST" class="space-y-4">
            <input type="text" name="direct_link" value="{{ ep_c.direct_link }}" placeholder="Direct Ad Link">
            <input type="text" name="monetag_id" value="{{ ep_c.monetag_id }}" placeholder="Monetag Zone ID">
            <div class="flex gap-4"><input type="number" name="unlock_minutes" value="{{ ep_c.unlock_minutes }}" class="w-1/2"><select name="active_type" class="w-1/2"><option value="direct" {{ 'selected' if ep_c.active_type=='direct' }}>Direct Link</option><option value="off" {{ 'selected' if ep_c.active_type=='off' }}>OFF</option></select></div>
            <button class="btn-blue bg-red-600">UPDATE AD LOCK</button>
        </form>
    </section>

    <section id="settings" class="glass p-8 rounded-[35px]">
        <h2 class="text-xl font-bold mb-6 border-b border-white/5 pb-2">Global Site Config</h2>
        <form action="/admin/update-settings" method="POST" class="space-y-4">
            <input type="text" name="site_name" value="{{ config.site_name }}">
            <input type="text" name="site_logo" value="{{ config.site_logo }}">
            <textarea name="header_notice" class="h-24">{{ config.header_notice }}</textarea>
            <input type="number" name="movies_per_page" value="{{ config.movies_per_page }}">
            <button class="btn-blue">SAVE SETTINGS</button>
        </form>
    </section>
</div>
</body></html>
"""

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASS: session['admin']=True; return redirect('/admin/dashboard')
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">"""+COMMON_CSS+"""</head>
    <body class="flex items-center justify-center min-h-screen p-6"><form method="POST" class="glass p-10 rounded-[40px] w-full max-w-sm text-center">
        <h1 class="text-2xl font-bold text-red-500 mb-6 uppercase">Admin Login</h1><input type="password" name="password" placeholder="Password" class="mb-4" required><button class="btn-blue bg-red-600">ENTER DASHBOARD</button>
    </form></body></html>""")

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'): return redirect('/admin')
    c = settings_col.find_one({"type": "site_config"})
    ep_c = ep_ads_col.find_one({"type": "ep_ad_config"})
    m = list(movies_col.find().sort('_id', -1))
    return render_template_string(ADMIN_PAGE, config=c, ep_c=ep_c, movies=m, u_count=users_col.count_documents({}), m_count=len(m))

# ==========================================
# ৬. টেলিগ্রাম বট ও এপিআই লজিক
# ==========================================

@bot.message_handler(commands=['start'])
def bot_start(message):
    bot.reply_to(message, f"👋 স্বাগতম!\nআপনার আইডি: `{message.from_user.id}`")

@bot.message_handler(commands=['movie'])
def bot_movie(message):
    if message.from_user.id not in ADMIN_IDS: return bot.reply_to(message, "❌ অনুমতি নেই।")
    msg = bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন:")
    bot.register_next_step_handler(msg, bot_step_cat)

def bot_step_cat(m):
    title = m.text
    msg = bot.send_message(m.chat.id, "📂 ক্যাটাগরি:")
    bot.register_next_step_handler(msg, lambda m: bot_step_poster(m, title))

def bot_step_poster(m, title):
    cat = m.text
    msg = bot.send_message(m.chat.id, "🖼 পোস্টার লিংক:")
    bot.register_next_step_handler(msg, lambda m: bot_step_files(m, title, cat))

def bot_step_files(m, title, cat):
    p = m.text
    msg = bot.send_message(m.chat.id, "📥 ফাইল দিন (শেষ হলে /done):")
    bot.register_next_step_handler(msg, lambda m: bot_collect(m, title, cat, p, []))

def bot_collect(m, title, cat, p, eps):
    if m.text == "/done":
        movies_col.insert_one({"title": title, "category": cat, "poster": p, "episodes": eps})
        return bot.send_message(m.chat.id, "✅ যোগ হয়েছে!")
    if m.content_type in ['video', 'document']:
        sent = bot.forward_message(FILE_CHANNEL_ID, m.chat.id, m.message_id)
        cid = str(FILE_CHANNEL_ID).replace("-100","")
        ep_name = f"{title} - EP {len(eps)+1}"
        eps.append({"name": ep_name, "link": f"https://t.me/c/{cid}/{sent.message_id}"})
        bot.send_message(m.chat.id, f"📥 {ep_name} যোগ হয়েছে।")
    bot.register_next_step_handler(m, lambda m: bot_collect(m, title, cat, p, eps))

@app.route('/api/webhook', methods=['POST'])
def webhook_handler():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update]); return ''
    return 'Forbidden', 403

# API Endpoints
@app.route('/api/check-access', methods=['POST'])
def api_check():
    u = users_col.find_one({"mobile": str(request.json.get('mobile'))})
    if u.get('is_premium'): return jsonify({"status": "unlocked"})
    un = ep_unlock_col.find_one({"mobile": str(u['mobile'])})
    if un and datetime.now() < un['expiry']: return jsonify({"status": "unlocked"})
    return jsonify({"status": "locked", "ad_config": ep_ads_col.find_one({"type":"ep_ad_config"})})

@app.route('/api/unlock', methods=['POST'])
def api_unl():
    ep_unlock_col.update_one({"mobile": str(request.json.get('mobile'))}, {"$set": {"expiry": datetime.now() + timedelta(minutes=30)}}, upsert=True)
    return jsonify({"status": "success"})

@app.route('/api/update-profile', methods=['POST'])
def up_prof():
    users_col.update_one({"mobile": str(request.form.get('mobile'))}, {"$set": {"first_name": request.form.get('first_name'), "password": request.form.get('password')}})
    return redirect('/profile')

@app.route('/admin/movie/add-range', methods=['POST'])
def add_range():
    title = request.form.get('title')
    start, end = int(request.form.get('start_id')), int(request.form.get('end_id'))
    cid = str(FILE_CHANNEL_ID).replace("-100", "")
    eps = [{"name": f"{title} - EP {idx+1}", "link": f"https://t.me/c/{cid}/{i}"} for idx, i in enumerate(range(start, end + 1))]
    movies_col.insert_one({"title": title, "category": "Action", "poster": "https://via.placeholder.com/300", "episodes": eps})
    return redirect('/admin/dashboard')

@app.route('/admin/movie/delete/<id>')
def del_mov(id):
    movies_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin/dashboard')

@app.route('/admin/update-settings', methods=['POST'])
def up_set():
    settings_col.update_one({"type":"site_config"}, {"$set": {"site_name":request.form.get('site_name'),"site_logo":request.form.get('site_logo'),"header_notice":request.form.get('header_notice'),"movies_per_page":int(request.form.get('movies_per_page'))}})
    return redirect('/admin/dashboard')

@app.route('/admin/update-ep-ads', methods=['POST'])
def up_ep():
    ep_ads_col.update_one({"type":"ep_ad_config"}, {"$set": {"direct_link":request.form.get('direct_link'),"monetag_id":request.form.get('monetag_id'),"unlock_minutes":int(request.form.get('unlock_minutes')),"active_type":request.form.get('active_type')}})
    return redirect('/admin/dashboard')

@app.route('/logout')
def logout():
    r = make_response(redirect('/login'))
    r.set_cookie('mobile', '', expires=0); return r

@app.route('/admin/logout')
def ad_logout():
    session.pop('admin', None); return redirect('/admin')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
