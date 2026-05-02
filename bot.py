import os
import telebot
import random
import string
import time
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
ADMIN_PASSWORD = "admin" # অ্যাডমিন প্যানেল পাসওয়ার্ড
WEBHOOK_URL = "https://dramastoreking24.vercel.app/api/webhook"

client = MongoClient(MONGO_URI)
db = client["movie_db"]
movies_col = db["movies"]
settings_col = db["settings"]
users_col = db["users"]
tasks_col = db["tasks"] # ডিরেক্ট লিংক টাস্ক
monetag_tasks_col = db["monetag_tasks"] # মনিটেগ টাস্ক
plans_col = db["premium_plans"]
otp_col = db["otps"]
ep_ads_col = db["episode_ads"] 
ep_unlock_col = db["episode_unlocks"]
user_tasks_history = db["user_tasks_history"]

app = Flask(__name__)
app.secret_key = "ultimate_movie_secret_key"
CORS(app)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# ডিফল্ট সেটিংস সেটআপ (বিন্দু পরিমাণ বাদ নেই)
def init_db():
    if not settings_col.find_one({"type": "site_config"}):
        settings_col.insert_one({
            "type": "site_config", "site_name": "Drama Store", 
            "site_logo": "https://via.placeholder.com/200x60?text=LOGO",
            "header_notice": "আমাদের সাইটে স্বাগতম! একাউন্ট খুলে আনলিমিটেড মুভি দেখুন। 🍿",
            "movies_per_page": 12
        })
    if not ep_ads_col.find_one({"type": "ep_ad_config"}):
        ep_ads_col.insert_one({
            "type": "ep_ad_config", "direct_link": "", "monetag_id": "10351894",
            "unlock_minutes": 30, "active_type": "off", "daily_limit": 10
        })

init_db()

# ==========================================
# ২. ডিজাইন (Responsive CSS)
# ==========================================
CSS = """
<style>
    :root { --primary: #3b82f6; --bg: #0b0f19; --glass: rgba(30, 41, 59, 0.7); }
    body { background: var(--bg); color: white; font-family: 'Inter', sans-serif; margin:0; padding:0; overflow-x: hidden; }
    .glass { background: var(--glass); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); }
    .btn-blue { background: var(--primary); color: white; border-radius: 12px; font-weight: bold; padding: 12px; border:none; cursor:pointer; width:100%; transition: 0.3s; }
    .movie-card img { transition: 0.5s; width:100%; aspect-ratio: 2/3; object-fit:cover; border-radius: 20px; }
    .movie-card:hover img { transform: scale(1.05); }
    .marquee { background: rgba(59, 130, 246, 0.1); padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); overflow: hidden; white-space: nowrap; }
    .marquee p { display: inline-block; animation: marquee 20s linear infinite; font-size: 13px; color: #fbbf24; }
    @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; display: flex; justify-content: space-around; padding: 12px; z-index: 100; background: rgba(11, 15, 25, 0.95); backdrop-filter: blur(10px); border-top: 1px solid rgba(255,255,255,0.1); }
    .bottom-nav a { text-decoration: none; color: #94a3b8; font-size: 10px; text-align: center; font-weight: bold; transition: 0.3s; }
    .bottom-nav a.active { color: #3b82f6; transform: scale(1.1); }
    input, textarea, select { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: white; padding: 12px; border-radius: 12px; outline: none; width:100%; margin-bottom:10px; }
    .grid-container { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
    @media (min-width: 768px) { .grid-container { grid-template-columns: repeat(4, 1fr); } }
    @media (min-width: 1024px) { .grid-container { grid-template-columns: repeat(6, 1fr); } }
</style>
"""

# ==========================================
# ৩. ইউজার প্যানেল লেআউট (Home, Profile, Tasks, Premium)
# ==========================================
# Monetag SDK স্ক্রিপ্ট সহ লেআউট ঠিক করা হয়েছে
USER_LAYOUT = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
<script src='//libtl.com/sdk.js' data-zone='10351894' data-sdk='show_10351894'></script>
""" + CSS + """</head><body class="pb-24">
<header class="glass sticky top-0 z-50 p-4 flex justify-between items-center shadow-xl">
    <img src="{{ config.site_logo }}" class="h-8 md:h-10">
    <div class="text-right"><span class="text-blue-400 font-bold block text-sm">{{ config.site_name }}</span></div>
</header>
<div class="marquee"><p>📢 {{ config.header_notice }}</p></div>
<main class="p-4 container mx-auto">"""

USER_FOOTER = """</main>
<nav class="glass bottom-nav">
    <a href="/" class="{{ 'active' if act == 'home' }}"><i class="fas fa-home text-xl"></i><br>🏠 HOME</a>
    <a href="/tasks" class="{{ 'active' if act == 'task' }}"><i class="fas fa-tasks text-xl"></i><br>📅 TASK</a>
    <a href="/premium" class="{{ 'active' if act == 'premium' }}"><i class="fas fa-crown text-xl"></i><br>👑 PREMIUM</a>
    <a href="/profile" class="{{ 'active' if act == 'profile' }}"><i class="fas fa-user text-xl"></i><br>👤 PROFILE</a>
</nav>
</body></html>
"""

# ==========================================
# ৪. ইউজার লজিক (লগইন, রেজিস্টার, মুভি, এপিআই)
# ==========================================

def get_user():
    mob = request.cookies.get('mobile')
    if not mob: return None
    return users_col.find_one({"mobile": str(mob)})

@app.route('/')
def home():
    u = get_user()
    if not u: return redirect('/login')
    c = settings_col.find_one({"type":"site_config"})
    page = int(request.args.get('page', 1))
    movies = list(movies_col.find().sort('_id', -1).skip((page-1)*c['movies_per_page']).limit(c['movies_per_page']))
    for m in movies: m['_id'] = str(m['_id'])
    return render_template_string(USER_LAYOUT + """
    {% block content %}
    <div class="grid-container">
        {% for m in movies %}
        <a href="/movie/{{ m._id }}" class="movie-card glass rounded-[25px] overflow-hidden block">
            <img src="{{ m.poster }}">
            <div class="p-3"><h3 class="text-[11px] font-bold truncate">{{ m.title }}</h3><p class="text-[9px] text-blue-400 uppercase font-black">{{ m.category }}</p></div>
        </a>
        {% endfor %}
    </div>
    <div class="mt-10 flex justify-center items-center gap-4">
        {% if page > 1 %}<a href="/?page={{ page-1 }}" class="glass px-5 py-2 rounded-xl text-xs">⬅️ Preview</a>{% endif %}
        <span class="text-blue-400 font-bold text-sm">🔢 Page {{ page }}</span>
        <a href="/?page={{ page+1 }}" class="glass px-5 py-2 rounded-xl text-xs">Next ➡️</a>
    </div>
    {% endblock %}""" + USER_FOOTER, act='home', config=c, movies=movies, page=page, user=u)

@app.route('/movie/<id>')
def movie_details(id):
    u = get_user()
    if not u: return redirect('/login')
    try: m = movies_col.find_one({"_id": ObjectId(id)})
    except: return redirect('/')
    if not m: return redirect('/')
    c = settings_col.find_one({"type":"site_config"})
    return render_template_string(USER_LAYOUT + """
    {% block content %}
    <div class="max-w-4xl mx-auto flex flex-col md:flex-row gap-8">
        <img src="{{ m.poster }}" class="w-full md:w-72 rounded-[35px] shadow-2xl border border-white/10">
        <div class="flex-1">
            <h1 class="text-4xl font-black mb-2 tracking-tighter">{{ m.title }}</h1>
            <span class="bg-blue-600 px-4 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest">{{ m.category }}</span>
            <div class="mt-12">
                <h4 class="text-gray-400 font-bold mb-6 border-l-4 border-blue-500 pl-3 uppercase text-[10px]">Episode List:</h4>
                <div class="grid grid-cols-3 md:grid-cols-6 gap-3">
                    {% for ep in m.episodes %}
                    <button onclick="play('{{ ep.link }}')" class="glass p-3 rounded-2xl text-[10px] font-bold border-b-4 border-blue-500 hover:bg-blue-600 transition">EP {{ loop.index }}</button>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    <script>
        async function play(l) {
            const r = await fetch('/api/check-access', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mobile:'{{ user.mobile }}'})});
            const d = await r.json();
            if(d.status === 'unlocked') { window.open(l, '_blank'); }
            else { 
                alert("⚠️ Ad Lock! বাটন আনলক করতে একটি এড দেখুন। (৩০ মিনিট আনলক থাকবে)"); 
                if(d.ad_config.active_type === 'direct') { window.open(d.ad_config.direct_link, '_blank'); unlock(); }
                else if(d.ad_config.active_type === 'monetag') {
                    if(typeof show_10351894 === 'function') {
                        show_10351894().then(() => { unlock(); window.open(l, '_blank'); });
                    } else { unlock(); window.open(l, '_blank'); }
                } else { window.open(l, '_blank'); }
            }
        }
        function unlock() { fetch('/api/unlock', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mobile:'{{ user.mobile }}'})}).then(()=>location.reload()); }
    </script>
    {% endblock %}""" + USER_FOOTER, act='home', config=c, m=m, user=u)

@app.route('/profile')
def profile():
    u = get_user()
    if not u: return redirect('/login')
    c = settings_col.find_one({"type":"site_config"})
    return render_template_string(USER_LAYOUT + """
    {% block content %}
    <div class="max-w-md mx-auto glass p-10 rounded-[40px] text-center shadow-2xl">
        <div class="w-24 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-3xl mx-auto flex items-center justify-center text-4xl font-black mb-6 shadow-xl">{{ (user.first_name or 'U')[0] }}</div>
        <h2 class="text-2xl font-black uppercase tracking-tighter">{{ user.first_name }} {{ user.last_name }}</h2>
        <p class="text-xs text-gray-500 mb-8 tracking-widest">📱 {{ user.mobile }}</p>
        <div class="grid grid-cols-2 gap-4 mb-10">
            <div class="bg-black/40 p-5 rounded-3xl"><p class="text-[9px] text-gray-500 uppercase font-bold">Balance</p><p class="text-xl font-black text-yellow-400">{{ user.get('balance', 0) }} 🪙</p></div>
            <div class="bg-black/40 p-5 rounded-3xl"><p class="text-[9px] text-gray-500 uppercase font-bold">Premium</p><p class="text-[11px] font-black {{ 'text-green-400' if user.is_premium else 'text-red-400' }}">{{ 'ACTIVE' if user.is_premium else 'INACTIVE' }}</p></div>
        </div>
        <form action="/api/update-profile" method="POST" class="space-y-4 text-left">
            <input type="hidden" name="mobile" value="{{ user.mobile }}">
            <input type="text" name="first_name" value="{{ user.first_name }}" placeholder="First Name">
            <input type="text" name="last_name" value="{{ user.last_name }}" placeholder="Last Name">
            <input type="password" name="password" placeholder="Change Password (Optional)">
            <button class="btn-blue mt-4 shadow-lg shadow-blue-500/20">UPDATE INFO</button>
        </form>
        <a href="/logout" class="block mt-10 text-red-500 text-[10px] font-black uppercase tracking-widest hover:opacity-70 transition">Logout Account</a>
    </div>
    {% endblock %}""" + USER_FOOTER, act='profile', config=c, user=u)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mob, pw = str(request.form.get('mobile')), str(request.form.get('password'))
        u = users_col.find_one({"mobile": mob, "password": pw})
        if u:
            r = make_response(redirect('/'))
            r.set_cookie('mobile', mob, max_age=30*24*60*60); return r
        return "ভুল মোবাইল/পাসওয়ার্ড! <a href='/login'>Try Again</a>"
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">"""+CSS+"""</head>
    <body class="flex items-center justify-center min-h-screen p-6"><div class="glass p-10 rounded-[45px] w-full max-w-sm text-center shadow-2xl">
        <h1 class="text-3xl font-black text-blue-400 mb-8 uppercase tracking-tighter">User Login</h1>
        <form method="POST" class="space-y-4"><input type="text" name="mobile" placeholder="Mobile Number" required><input type="password" name="password" placeholder="Password" required><button class="btn-blue shadow-lg shadow-blue-500/20">LOGIN NOW</button></form>
        <p class="mt-8 text-xs text-gray-500">Don't have an account? <a href="/register" class="text-blue-400 font-bold">Register</a></p>
        <p class="mt-2 text-[10px] text-gray-600"><a href="/forgot">Forgot Password?</a></p>
    </div></body></html>""")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        mob = str(request.form.get('mobile'))
        if users_col.find_one({"mobile": mob}): return "ইতিমধ্যে নিবন্ধিত!"
        users_col.insert_one({"first_name":request.form.get('first_name'),"last_name":request.form.get('last_name'),"mobile":mob,"telegram_id":str(request.form.get('telegram_id')),"password":str(request.form.get('password')),"balance":0,"is_premium":False, "premium_expiry": datetime.now()})
        return redirect('/login')
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">"""+CSS+"""</head>
    <body class="flex items-center justify-center min-h-screen p-6"><div class="glass p-10 rounded-[45px] w-full max-w-sm text-center shadow-2xl">
        <h1 class="text-3xl font-black text-green-500 mb-8 uppercase tracking-tighter">Register</h1>
        <form method="POST" class="space-y-4">
            <div class="flex gap-2"><input type="text" name="first_name" placeholder="First Name" required><input type="text" name="last_name" placeholder="Last Name" required></div>
            <input type="text" name="mobile" placeholder="Mobile Number" required>
            <input type="number" name="telegram_id" placeholder="Telegram ID (Get from bot)" required>
            <input type="password" name="password" placeholder="Set Password" required>
            <button class="btn-blue bg-green-600 shadow-lg shadow-green-500/20">CREATE ACCOUNT</button>
        </form>
        <p class="mt-8 text-xs text-gray-500">Already a member? <a href="/login" class="text-green-500 font-bold">Login</a></p>
    </div></body></html>""")

@app.route('/tasks')
def tasks():
    u = get_user()
    if not u: return redirect('/login')
    c = settings_col.find_one({"type":"site_config"})
    d_tasks = list(tasks_col.find())
    for t in d_tasks: t['_id'] = str(t['_id'])
    m_tasks = list(monetag_tasks_col.find())
    for t in m_tasks: t['_id'] = str(t['_id'])
    return render_template_string(USER_LAYOUT + """
    {% block content %}
    <h2 class="text-xl font-bold mb-6 text-green-400 uppercase tracking-tighter">💰 Daily Income Tasks</h2>
    <div class="space-y-4">
        {% for t in d_tasks %}
        <div class="glass p-5 rounded-3xl flex justify-between items-center">
            <div><p class="text-sm font-bold">Direct Task {{ loop.index }}</p><p class="text-[10px] text-yellow-400">+{{ t.coins }} Coins</p></div>
            <button onclick="window.open('{{ t.link }}', '_blank'); completeTask('{{ t._id }}', 'direct')" class="bg-green-600 px-6 py-2 rounded-xl text-[10px] font-black uppercase">GO</button>
        </div>
        {% endfor %}
        {% for m in m_tasks %}
        <div class="glass p-5 rounded-3xl flex justify-between items-center">
            <div><p class="text-sm font-bold">Watch Ad Task {{ loop.index }}</p><p class="text-[10px] text-yellow-400">+{{ m.coins }} Coins</p></div>
            <button onclick="completeTask('{{ m._id }}', 'monetag')" class="bg-blue-600 px-6 py-2 rounded-xl text-[10px] font-black uppercase">WATCH</button>
        </div>
        {% endfor %}
    </div>
    <script>
    async function completeTask(id, type) {
        const r = await fetch('/api/tasks/complete', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mobile:'{{ user.mobile }}', task_id:id, type:type})});
        const d = await r.json();
        if(d.status === 'success') { alert("Success! Coins Added."); location.reload(); }
        else { alert("Limit Reached or Error!"); }
    }
    </script>
    {% endblock %}""" + USER_FOOTER, act='task', config=c, user=u, d_tasks=d_tasks, m_tasks=m_tasks)

@app.route('/premium')
def premium_page():
    u = get_user()
    if not u: return redirect('/login')
    c = settings_col.find_one({"type":"site_config"})
    plans = list(plans_col.find())
    for p in plans: p['_id'] = str(p['_id'])
    return render_template_string(USER_LAYOUT + """
    {% block content %}
    <h2 class="text-xl font-bold mb-6 text-yellow-400 uppercase tracking-tighter">👑 Premium Member Plans</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        {% for p in plans %}
        <div class="glass p-8 rounded-[40px] text-center border-t-4 border-yellow-500 shadow-2xl relative overflow-hidden">
            <div class="absolute top-0 right-0 bg-yellow-500 text-black px-4 py-1 text-[8px] font-black uppercase rounded-bl-xl">Best Value</div>
            <h3 class="text-2xl font-black mb-2">{{ p.days }} DAYS</h3>
            <p class="text-gray-400 text-xs mb-6 italic">Full Access, No Ads</p>
            <p class="text-3xl font-black text-yellow-400 mb-8">{{ p.coins }} <span class="text-xs text-gray-500">Coins</span></p>
            <button onclick="buyPremium('{{ p._id }}')" class="btn-blue bg-yellow-600 shadow-lg shadow-yellow-500/20 uppercase tracking-widest text-[10px]">Buy Member</button>
        </div>
        {% endfor %}
    </div>
    <script>
    async function buyPremium(id) {
        if(!confirm("Are you sure you want to buy this plan?")) return;
        const r = await fetch('/api/premium/buy', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mobile:'{{ user.mobile }}', plan_id:id})});
        const d = await r.json();
        alert(d.message); if(d.status==='success') location.reload();
    }
    </script>
    {% endblock %}""" + USER_FOOTER, act='premium', config=c, user=u, plans=plans)

# ==========================================
# ৫. মেগা অ্যাডমিন ড্যাশবোর্ড (সব মেনুসহ)
# ==========================================

ADMIN_LAYOUT = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
""" + CSS + """</head><body class="flex flex-col md:flex-row min-h-screen">
<div class="w-full md:w-64 glass p-6 space-y-6 flex-shrink-0">
    <h1 class="text-xl font-black text-blue-400 text-center uppercase tracking-widest">Master Admin</h1>
    <nav class="flex flex-col gap-2 text-[11px] font-bold">
        <a href="/admin/dashboard" class="p-3 bg-white/5 rounded-xl hover:bg-blue-600/20"><i class="fas fa-home mr-3"></i> DASHBOARD</a>
        <a href="#movies" class="p-3 hover:bg-white/5 rounded-xl"><i class="fas fa-film mr-3"></i> MOVIE LIST</a>
        <a href="#ep_ads" class="p-3 hover:bg-red-500/10 rounded-xl text-red-400"><i class="fas fa-lock mr-3"></i> EPISODE AD LOCK</a>
        <a href="#tasks" class="p-3 hover:bg-green-500/10 rounded-xl text-green-400"><i class="fas fa-tasks mr-3"></i> DAILY TASKS</a>
        <a href="#monetag_ads" class="p-3 hover:bg-yellow-500/10 rounded-xl text-yellow-400"><i class="fas fa-ad mr-3"></i> MONETAG ADS</a>
        <a href="#plans" class="p-3 hover:bg-purple-500/10 rounded-xl text-purple-400"><i class="fas fa-crown mr-3"></i> PREMIUM PLANS</a>
        <a href="#settings" class="p-3 hover:bg-white/5 rounded-xl"><i class="fas fa-cog mr-3"></i> GLOBAL SETTINGS</a>
        <a href="/admin/logout" class="p-3 text-red-500 mt-12 bg-red-500/10 rounded-xl"><i class="fas fa-sign-out-alt mr-3"></i> LOGOUT ADMIN</a>
    </nav>
</div>
<div class="flex-1 p-6 space-y-12 overflow-y-auto">"""

ADMIN_FOOTER = """</div></body></html>"""

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD: session['admin']=True; return redirect('/admin/dashboard')
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">"""+CSS+"""</head>
    <body class="flex items-center justify-center min-h-screen p-6"><form method="POST" class="glass p-12 rounded-[45px] w-full max-w-sm text-center shadow-2xl">
        <h1 class="text-2xl font-black text-red-500 mb-8 uppercase tracking-widest">Admin Portal</h1>
        <input type="password" name="password" placeholder="Admin Password" class="mb-4" required>
        <button class="btn-blue bg-red-600 shadow-lg shadow-red-500/20">ENTER SYSTEM</button>
    </form></body></html>""")

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'): return redirect('/admin')
    c = settings_col.find_one({"type": "site_config"})
    ep_c = ep_ads_col.find_one({"type": "ep_ad_config"})
    m = list(movies_col.find().sort('_id', -1))
    for x in m: x['_id'] = str(x['_id'])
    plans = list(plans_col.find())
    for x in plans: x['_id'] = str(x['_id'])
    d_tasks = list(tasks_col.find())
    for x in d_tasks: x['_id'] = str(x['_id'])
    m_tasks = list(monetag_tasks_col.find())
    for x in m_tasks: x['_id'] = str(x['_id'])
    return render_template_string(ADMIN_LAYOUT + """
    {% block admin_content %}
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <div class="glass p-6 rounded-[30px] text-center border-b-4 border-blue-500 shadow-xl"><p class="text-[9px] text-gray-500 uppercase font-black">Users</p><p class="text-3xl font-black text-blue-400">{{ u_count }}</p></div>
        <div class="glass p-6 rounded-[30px] text-center border-b-4 border-green-500 shadow-xl"><p class="text-[9px] text-gray-500 uppercase font-black">Movies</p><p class="text-3xl font-black text-green-400">{{ m_count }}</p></div>
    </div>

    <!-- Movie Management -->
    <section id="movies" class="glass p-10 rounded-[40px] border border-blue-500/10">
        <h2 class="text-xl font-black mb-8 text-blue-400 border-b border-white/5 pb-3 uppercase tracking-tighter">Movie Management (Range Uploader)</h2>
        <form action="/admin/movie/add-range" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-10">
            <input type="text" name="title" placeholder="Movie Name" class="md:col-span-2" required>
            <input type="number" name="start_id" placeholder="Start Msg ID" required>
            <input type="number" name="end_id" placeholder="End Msg ID" required>
            <button class="btn-blue bg-indigo-600 md:col-span-4 uppercase tracking-widest font-black">UPLOAD TELEGRAM RANGE</button>
        </form>
        <div class="overflow-x-auto"><table class="w-full text-left text-[11px]">
            <thead class="text-gray-500 border-b border-white/5 uppercase"><tr><th class="p-4">TITLE</th><th class="p-4">EPISODES</th><th class="p-4 text-right">ACTION</th></tr></thead>
            <tbody>{% for x in movies %}<tr class="border-b border-white/5">
                <td class="p-4 font-bold">{{ x.title }}</td><td class="p-4"><span class="bg-blue-600/20 text-blue-400 px-3 py-1 rounded-full">{{ x.episodes|length if x.episodes else 0 }} EP</span></td>
                <td class="p-4 text-right"><a href="/admin/movie/delete/{{ x._id }}" class="text-red-500 font-black" onclick="return confirm('Delete Movie?')"><i class="fas fa-trash-alt"></i></a></td>
            </tr>{% endfor %}</tbody>
        </table></div>
    </section>

    <!-- Episode Ad Config -->
    <section id="ep_ads" class="glass p-10 rounded-[40px] border border-red-500/10">
        <h2 class="text-xl font-black mb-8 text-red-500 border-b border-white/5 pb-3 uppercase tracking-tighter">Episode Ad Lock Configuration</h2>
        <form action="/admin/update-ep-ads" method="POST" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input type="text" name="direct_link" value="{{ ep_c.direct_link }}" placeholder="Direct Ad Link (Optional)">
                <input type="text" name="monetag_id" value="{{ ep_c.monetag_id }}" placeholder="Monetag Zone ID (Optional)">
            </div>
            <div class="grid grid-cols-2 gap-4">
                <input type="number" name="unlock_minutes" value="{{ ep_c.unlock_minutes }}" placeholder="Unlock Minutes (e.g. 30)">
                <select name="active_type">
                    <option value="direct" {{ 'selected' if ep_c.active_type=='direct' }}>USE DIRECT LINK</option>
                    <option value="monetag" {{ 'selected' if ep_c.active_type=='monetag' }}>USE MONETAG SCRIPT</option>
                    <option value="off" {{ 'selected' if ep_c.active_type=='off' }}>OFF (FREE ACCESS)</option>
                </select>
            </div>
            <button class="btn-blue bg-red-600 shadow-xl shadow-red-500/20 uppercase tracking-widest font-black">UPDATE LOCK SYSTEM</button>
        </form>
    </section>

    <!-- Direct Tasks -->
    <section id="tasks" class="glass p-10 rounded-[40px] border border-green-500/10">
        <h2 class="text-xl font-black mb-8 text-green-500 border-b border-white/5 pb-3 uppercase">Direct Link Income Tasks</h2>
        <form action="/admin/task/add" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <input type="text" name="link" placeholder="Direct Ad/Task Link" class="md:col-span-2" required>
            <input type="number" name="coins" placeholder="Coins" required>
            <input type="number" name="limit" placeholder="Limit" required>
            <button class="btn-blue bg-green-600 md:col-span-4 font-black">ADD DIRECT TASK</button>
        </form>
        <div class="space-y-2">{% for t in d_tasks %}<div class="bg-black/30 p-3 rounded-xl flex justify-between text-xs"><span>{{ t.link[:40] }}.. (+{{ t.coins }} C)</span><a href="/admin/task/delete/{{ t._id }}" class="text-red-500"><i class="fas fa-trash-alt"></i></a></div>{% endfor %}</div>
    </section>

    <!-- Monetag Ad Tasks -->
    <section id="monetag_ads" class="glass p-10 rounded-[40px] border border-yellow-500/10">
        <h2 class="text-xl font-black mb-8 text-yellow-500 border-b border-white/5 pb-3 uppercase">Monetag Watch Ad Tasks</h2>
        <form action="/admin/monetag/add" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <input type="text" name="zone_id" placeholder="Monetag Zone ID" class="md:col-span-2" required>
            <input type="number" name="coins" placeholder="Coins" required>
            <input type="number" name="limit" placeholder="Limit" required>
            <button class="btn-blue bg-yellow-600 md:col-span-4 font-black text-black">ADD WATCH AD TASK</button>
        </form>
        <div class="space-y-2">{% for mt in m_tasks %}<div class="bg-black/30 p-3 rounded-xl flex justify-between text-xs"><span>Zone: {{ mt.zone_id }} (+{{ mt.coins }} C)</span><a href="/admin/monetag/delete/{{ mt._id }}" class="text-red-500"><i class="fas fa-trash-alt"></i></a></div>{% endfor %}</div>
    </section>

    <!-- Premium Plans -->
    <section id="plans" class="glass p-10 rounded-[40px] border border-purple-500/10">
        <h2 class="text-xl font-black mb-8 text-purple-400 border-b border-white/5 pb-3 uppercase">Premium Member Plans</h2>
        <form action="/admin/add-plan" method="POST" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
            <input type="number" name="days" placeholder="Days" required><input type="number" name="coins" placeholder="Coins" required><button class="btn-blue bg-purple-600 font-black">ADD PLAN</button>
        </form>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-3">{% for p in plans %}<div class="bg-black/30 p-4 rounded-[25px] flex justify-between items-center text-xs"><span>{{ p.days }} Days / {{ p.coins }} C</span><a href="/admin/plan/delete/{{ p._id }}" class="text-red-500"><i class="fas fa-trash-alt"></i></a></div>{% endfor %}</div>
    </section>

    <!-- Global Settings -->
    <section id="settings" class="glass p-10 rounded-[40px]">
        <h2 class="text-xl font-black mb-8 text-white border-b border-white/5 pb-3 uppercase">Global Site Settings</h2>
        <form action="/admin/update-settings" method="POST" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input type="text" name="site_name" value="{{ config.site_name }}" placeholder="Site Name">
                <input type="text" name="site_logo" value="{{ config.site_logo }}" placeholder="Logo Link">
            </div>
            <textarea name="header_notice" class="h-32" placeholder="Header Notice">{{ config.header_notice }}</textarea>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <input type="number" name="movies_per_page" value="{{ config.movies_per_page }}" placeholder="Movies Per Page">
                <button class="btn-blue bg-blue-600 font-black">SAVE ALL CONFIGURATION</button>
            </div>
        </form>
    </section>
    {% endblock %}""" + ADMIN_FOOTER, config=c, ep_c=ep_c, movies=m, u_count=users_col.count_documents({}), m_count=len(m), plans=plans, d_tasks=d_tasks, m_tasks=m_tasks)

# ==========================================
# ৬. টেলিগ্রাম বট ও লজিক (OTP, `/movie`, চ্যানেল ফরওয়ার্ড)
# ==========================================

@bot.message_handler(commands=['start'])
def bot_start(message):
    bot.reply_to(message, f"👋 স্বাগতম!\nআপনার টেলিগ্রাম আইডি: `{message.from_user.id}`\nএটি পাসওয়ার্ড রিসেট করতে ওয়েবসাইট এ লাগবে।")

@bot.message_handler(commands=['movie'])
def bot_movie_start(message):
    if message.from_user.id not in ADMIN_IDS: return bot.reply_to(message, "❌ আপনি অনুমতিপ্রাপ্ত নন।")
    msg = bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন:")
    bot.register_next_step_handler(msg, bot_get_cat)

def bot_get_cat(m):
    title = m.text
    msg = bot.send_message(m.chat.id, "📂 মুভির ক্যাটাগরি:")
    bot.register_next_step_handler(msg, lambda m: bot_get_poster(m, title))

def bot_get_poster(m, title):
    cat = m.text
    msg = bot.send_message(m.chat.id, "🖼 মুভির পোস্টার ডিরেক্ট লিংক (Image Link) দিন:")
    bot.register_next_step_handler(msg, lambda m: bot_get_files(m, title, cat))

def bot_get_files(m, title, cat):
    poster = m.text
    msg = bot.send_message(m.chat.id, "📥 ভিডিও/ডকুমেন্ট ফাইল একে একে পাঠান। শেষ হলে /done লিখুন।")
    bot.register_next_step_handler(msg, lambda m: bot_collect_files(m, title, cat, poster, []))

def bot_collect_files(m, title, cat, poster, eps):
    if m.text == "/done":
        movies_col.insert_one({"title": title, "category": cat, "poster": poster, "episodes": eps, "date": datetime.now()})
        return bot.send_message(m.chat.id, f"✅ মুভি সফলভাবে যোগ হয়েছে: {title}")
    if m.content_type in ['video', 'document']:
        sent = bot.forward_message(FILE_CHANNEL_ID, m.chat.id, m.message_id)
        cid = str(FILE_CHANNEL_ID).replace("-100", "")
        # মুভির নাম অনুযায়ী ইপিসোড নেমিং (ফাইল নেম বাদ)
        ep_name = f"{title} - Episode {len(eps)+1}"
        eps.append({"name": ep_name, "link": f"https://t.me/c/{cid}/{sent.message_id}"})
        bot.send_message(m.chat.id, f"📥 {ep_name} যোগ হয়েছে। আরও ফাইল থাকলে দিন নতুবা /done লিখুন।")
    bot.register_next_step_handler(m, lambda m: bot_collect_files(m, title, cat, poster, eps))

# ==========================================
# ৭. পাসওয়ার্ড রিসেট (OTP System)
# ==========================================

@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        mob, tid = str(request.form.get('mobile')), int(request.form.get('telegram_id'))
        u = users_col.find_one({"mobile": mob, "telegram_id": str(tid)})
        if u:
            otp = ''.join(random.choices(string.digits, k=6))
            otp_col.update_one({"mobile": mob}, {"$set": {"otp": otp}}, upsert=True)
            try:
                bot.send_message(tid, f"🔐 আপনার পাসওয়ার্ড রিসেট ওটিপি: {otp}\nএটি কারো সাথে শেয়ার করবেন না।")
                return render_template_string("""
                <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">"""+CSS+"""</head>
                <body class="flex items-center justify-center min-h-screen p-6"><div class="glass p-10 rounded-[45px] w-full max-w-sm text-center shadow-2xl">
                    <h1 class="text-3xl font-black text-blue-400 mb-8 uppercase tracking-tighter">Enter OTP</h1>
                    <form action="/reset" method="POST" class="space-y-4">
                        <input type="hidden" name="mobile" value="{{ mob }}">
                        <input type="text" name="otp" placeholder="6-Digit OTP" required>
                        <input type="password" name="password" placeholder="Set New Password" required>
                        <button class="btn-blue">RESET NOW</button>
                    </form>
                </div></body></html>""", mob=mob)
            except: return "বট স্টার্ট করেননি! বটের প্রোফাইলে গিয়ে /start দিন।"
        return "তথ্য মেলেনি!"
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">"""+CSS+"""</head>
    <body class="flex items-center justify-center min-h-screen p-6"><div class="glass p-10 rounded-[45px] w-full max-w-sm text-center shadow-2xl">
        <h1 class="text-2xl font-black text-blue-400 mb-8 uppercase tracking-tighter">Forgot Password</h1>
        <form method="POST" class="space-y-4"><input type="text" name="mobile" placeholder="Registered Mobile" required><input type="number" name="telegram_id" placeholder="Telegram ID" required><button class="btn-blue">GET OTP ON BOT</button></form>
    </div></body></html>""")

@app.route('/reset', methods=['POST'])
def reset_password_final():
    mob, otp, pw = str(request.form.get('mobile')), str(request.form.get('otp')), str(request.form.get('password'))
    res = otp_col.find_one({"mobile": mob, "otp": otp})
    if res:
        users_col.update_one({"mobile": mob}, {"$set": {"password": pw}})
        otp_col.delete_one({"mobile": mob}); return redirect('/login')
    return "ভুল ওটিপি!"

# ==========================================
# ৮. অ্যাডমিন ব্যাকএন্ড লজিক ও API (মুভি অ্যাড, ডিলিট, সেটিংস)
# ==========================================

@app.route('/admin/movie/add-range', methods=['POST'])
def admin_add_movie_range():
    if not session.get('admin'): return redirect('/admin')
    title, start, end = request.form.get('title'), int(request.form.get('start_id')), int(request.form.get('end_id'))
    cid = str(FILE_CHANNEL_ID).replace("-100", "")
    eps = [{"name": f"{title} - Episode {idx+1}", "link": f"https://t.me/c/{cid}/{i}"} for idx, i in enumerate(range(start, end + 1))]
    movies_col.insert_one({"title": title, "category": "Action", "poster": "https://via.placeholder.com/300", "episodes": eps, "date": datetime.now()})
    return redirect('/admin/dashboard')

@app.route('/admin/movie/delete/<id>')
def admin_del_movie(id):
    if not session.get('admin'): return redirect('/admin')
    try: movies_col.delete_one({"_id": ObjectId(id)})
    except: pass
    return redirect('/admin/dashboard')

@app.route('/admin/task/add', methods=['POST'])
def admin_add_task():
    tasks_col.insert_one(request.form.to_dict()); return redirect('/admin/dashboard')

@app.route('/admin/task/delete/<id>')
def admin_del_task(id):
    try: tasks_col.delete_one({"_id": ObjectId(id)})
    except: pass
    return redirect('/admin/dashboard')

@app.route('/admin/monetag/add', methods=['POST'])
def admin_add_monetag():
    monetag_tasks_col.insert_one(request.form.to_dict()); return redirect('/admin/dashboard')

@app.route('/admin/monetag/delete/<id>')
def admin_del_monetag(id):
    try: monetag_tasks_col.delete_one({"_id": ObjectId(id)})
    except: pass
    return redirect('/admin/dashboard')

@app.route('/admin/add-plan', methods=['POST'])
def admin_add_plan():
    plans_col.insert_one(request.form.to_dict()); return redirect('/admin/dashboard')

@app.route('/admin/plan/delete/<id>')
def admin_del_plan(id):
    try: plans_col.delete_one({"_id": ObjectId(id)})
    except: pass
    return redirect('/admin/dashboard')

@app.route('/admin/update-settings', methods=['POST'])
def admin_save_settings():
    d = request.form.to_dict()
    settings_col.update_one({"type":"site_config"}, {"$set": {"site_name":d['site_name'],"site_logo":d['site_logo'],"header_notice":d['header_notice'],"movies_per_page":int(d['movies_per_page'])}})
    return redirect('/admin/dashboard')

@app.route('/admin/update-ep-ads', methods=['POST'])
def admin_save_ep_ads():
    ep_ads_col.update_one({"type":"ep_ad_config"}, {"$set": {"direct_link":request.form.get('direct_link'),"monetag_id":request.form.get('monetag_id'),"unlock_minutes":int(request.form.get('unlock_minutes')),"active_type":request.form.get('active_type')}})
    return redirect('/admin/dashboard')

# ==========================================
# ৯. ইউজার সাপোর্ট এপিআই (Task & Unlock)
# ==========================================

@app.route('/api/tasks/complete', methods=['POST'])
def api_task_done():
    d = request.json
    today = datetime.now().strftime("%Y-%m-%d")
    h = user_tasks_history.find_one({"mobile": d['mobile'], "task_id": d['task_id'], "date": today})
    if h and h.get('count', 0) >= 5: return jsonify({"status": "limit"})
    col = monetag_tasks_col if d['type'] == 'monetag' else tasks_col
    t = col.find_one({"_id": ObjectId(d['task_id'])})
    users_col.update_one({"mobile": str(d['mobile'])}, {"$inc": {"balance": int(t['coins'])}})
    user_tasks_history.update_one({"mobile": d['mobile'], "task_id": d['task_id'], "date": today}, {"$inc": {"count": 1}}, upsert=True)
    return jsonify({"status": "success"})

@app.route('/api/premium/buy', methods=['POST'])
def api_buy_prem():
    d = request.json
    p = plans_col.find_one({"_id": ObjectId(d['plan_id'])})
    u = users_col.find_one({"mobile": d['mobile']})
    if not u or u.get('balance', 0) < int(p.get('coins', 0)): return jsonify({"status": "low", "message": "Low coins!"})
    current_expiry = u.get('premium_expiry')
    base_time = current_expiry if isinstance(current_expiry, datetime) and current_expiry > datetime.now() else datetime.now()
    exp = base_time + timedelta(days=int(p['days']))
    users_col.update_one({"mobile": d['mobile']}, {"$inc": {"balance": -int(p['coins'])}, "$set": {"is_premium": True, "premium_expiry": exp}})
    return jsonify({"status": "success", "message": "Activated!"})

@app.route('/api/check-access', methods=['POST'])
def api_check_ep():
    u = users_col.find_one({"mobile": str(request.json.get('mobile'))})
    if not u: return jsonify({"status": "locked"})
    if u.get('is_premium'): return jsonify({"status": "unlocked"})
    un = ep_unlock_col.find_one({"mobile": str(u['mobile'])})
    if un and datetime.now() < un.get('expiry', datetime.now()): return jsonify({"status": "unlocked"})
    ad_conf = ep_ads_col.find_one({"type":"ep_ad_config"})
    ad_conf['_id'] = str(ad_conf['_id']) # JSON serializable fixed
    return jsonify({"status": "locked", "ad_config": ad_conf})

@app.route('/api/unlock', methods=['POST'])
def api_unlock_final():
    mob, c = str(request.json.get('mobile')), ep_ads_col.find_one({"type":"ep_ad_config"})
    ep_unlock_col.update_one({"mobile": mob}, {"$set": {"expiry": datetime.now() + timedelta(minutes=int(c.get('unlock_minutes', 30)))}}, upsert=True)
    return jsonify({"status": "success"})

@app.route('/api/update-profile', methods=['POST'])
def api_up_profile():
    users_col.update_one({"mobile": str(request.form.get('mobile'))}, {"$set": {"first_name": request.form.get('first_name'), "last_name": request.form.get('last_name'), "password": request.form.get('password')}})
    return redirect('/profile')

@app.route('/logout')
def logout():
    r = make_response(redirect('/login'))
    r.set_cookie('mobile', '', expires=0); return r

@app.route('/admin/logout')
def ad_logout():
    session.pop('admin', None); return redirect('/admin')

# ==========================================
# ১০. মেগা ওয়েবহুক ও রান সিস্টেম
# ==========================================

@app.route('/api/webhook', methods=['POST'])
def webhook_handler():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update]); return ''
    return 'Forbidden', 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
