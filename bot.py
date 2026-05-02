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
# ১. কনফিগারেশন ও ডাটাবেস
# ==========================================
BOT_TOKEN = "8655043839:AAGMxkYoZXR-nUzlcapZZfVwci09Z6x0-UE"
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0"
FILE_CHANNEL_ID = -1003985353441 
ADMIN_IDS = [7120801813]
ADMIN_PASSWORD = "admin" # অ্যাডমিন প্যানেলের পাসওয়ার্ড

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
app.secret_key = "secret_key_123"
CORS(app)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# ডিফল্ট সেটিংস অটো-সেটআপ
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
            "type": "ep_ad_config", "direct_link": "", "monetag_id": "",
            "unlock_minutes": 30, "active_type": "off"
        })

init_db()

# ==========================================
# ২. সিএসএস ও ডিজাইন (Responsive Mobile & Desktop)
# ==========================================
CSS = """
<style>
    :root { --primary: #3b82f6; --bg: #0b0f19; --glass: rgba(30, 41, 59, 0.7); }
    body { background: var(--bg); color: white; font-family: 'Inter', sans-serif; margin:0; padding:0; overflow-x: hidden; }
    .glass { background: var(--glass); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); }
    .btn-blue { background: var(--primary); color: white; border-radius: 12px; font-weight: bold; padding: 12px; border:none; cursor:pointer; }
    .movie-card img { transition: 0.3s; width:100%; height:250px; object-fit:cover; border-radius: 15px; }
    .movie-card:hover img { transform: scale(1.05); }
    .marquee { background: rgba(59, 130, 246, 0.1); py: 8px; border-bottom: 1px solid rgba(59, 130, 246, 0.2); overflow: hidden; white-space: nowrap; }
    .marquee p { display: inline-block; animation: marquee 20s linear infinite; font-size: 13px; color: #fbbf24; }
    @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
    .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; display: flex; justify-content: space-around; padding: 10px; z-index: 100; border-top: 1px solid rgba(255,255,255,0.05); }
    .bottom-nav a { text-decoration: none; color: #94a3b8; font-size: 10px; text-align: center; font-weight: bold; }
    .bottom-nav a.active { color: #3b82f6; }
    input, textarea, select { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); color: white; padding: 12px; border-radius: 10px; outline: none; }
</style>
"""

# ==========================================
# ৩. ইউজার প্যানেল HTML (Home, Movie, Profile, Task, Premium)
# ==========================================

BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config.site_name }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    """ + CSS + """
</head>
<body class="pb-24">
    <!-- Header -->
    <header class="glass sticky top-0 z-50 p-4 flex justify-between items-center shadow-xl">
        <img src="{{ config.site_logo }}" class="h-8 md:h-10">
        <div class="text-right">
            <span class="text-blue-400 font-bold block">{{ config.site_name }}</span>
            <span class="text-[9px] text-gray-500 uppercase tracking-tighter">Premium Entertainment</span>
        </div>
    </header>

    <!-- Notice -->
    <div class="marquee"><p>📢 {{ config.header_notice }}</p></div>

    <main class="p-4 container mx-auto">
        {% block content %}{% endblock %}
    </main>

    <!-- Bottom Nav -->
    <nav class="glass bottom-nav">
        <a href="/" class="{{ 'active' if active == 'home' }}"><i class="fas fa-home text-lg"></i><br>HOME</a>
        <a href="/tasks" class="{{ 'active' if active == 'task' }}"><i class="fas fa-tasks text-lg"></i><br>TASK</a>
        <a href="/premium" class="{{ 'active' if active == 'premium' }}"><i class="fas fa-crown text-lg"></i><br>PREMIUM</a>
        <a href="/profile" class="{{ 'active' if active == 'profile' }}"><i class="fas fa-user text-lg"></i><br>PROFILE</a>
    </nav>
</body>
</html>
"""

# ==========================================
# ৪. রাউটস (Auth, User, API)
# ==========================================

def get_user():
    mobile = request.cookies.get('mobile')
    if not mobile: return None
    return users_col.find_one({"mobile": str(mobile)})

@app.route('/')
def home():
    user = get_user()
    if not user: return redirect('/login')
    config = settings_col.find_one({"type": "site_config"})
    page = int(request.args.get('page', 1))
    limit = config['movies_per_page']
    skip = (page - 1) * limit
    movies = list(movies_col.find().sort('_id', -1).skip(skip).limit(limit))
    return render_template_string(BASE_LAYOUT, active='home', config=config, movies=movies, user=user, page=page)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        user = users_col.find_one({"mobile": str(mobile), "password": str(password)})
        if user:
            resp = make_response(redirect('/'))
            resp.set_cookie('mobile', str(mobile), max_age=30*24*60*60)
            return resp
        return "ভুল মোবাইল অথবা পাসওয়ার্ড! <a href='/login'>Try Again</a>"
    config = settings_col.find_one({"type": "site_config"})
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">""" + CSS + """</head>
    <body class="flex items-center justify-center min-h-screen p-6">
        <div class="glass w-full max-w-sm p-8 rounded-3xl text-center">
            <h1 class="text-2xl font-bold text-blue-400 mb-6 uppercase">User Login</h1>
            <form method="POST" class="flex flex-col gap-4">
                <input type="text" name="mobile" placeholder="Mobile Number" required>
                <input type="password" name="password" placeholder="Password" required>
                <button class="btn-blue mt-4">LOGIN</button>
            </form>
            <p class="mt-6 text-sm text-gray-400">নতুন ইউজার? <a href="/register" class="text-blue-400">রেজিস্টার করুন</a></p>
            <p class="mt-2 text-xs text-gray-500"><a href="/forgot">পাসওয়ার্ড ভুলে গেছেন?</a></p>
        </div>
    </body></html>""", config=config)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        if users_col.find_one({"mobile": str(mobile)}): return "নাম্বারটি আগে থেকেই আছে!"
        users_col.insert_one({
            "first_name": request.form.get('first_name'),
            "last_name": request.form.get('last_name'),
            "mobile": str(mobile),
            "telegram_id": str(request.form.get('telegram_id')),
            "password": str(request.form.get('password')),
            "balance": 0, "is_premium": False, "premium_expiry": None
        })
        return redirect('/login')
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">""" + CSS + """</head>
    <body class="flex items-center justify-center min-h-screen p-6">
        <div class="glass w-full max-w-sm p-8 rounded-3xl text-center">
            <h1 class="text-2xl font-bold text-green-400 mb-6 uppercase">Register</h1>
            <form method="POST" class="flex flex-col gap-4">
                <div class="flex gap-2">
                    <input type="text" name="first_name" placeholder="First Name" required class="w-1/2">
                    <input type="text" name="last_name" placeholder="Last Name" required class="w-1/2">
                </div>
                <input type="text" name="mobile" placeholder="Mobile Number" required>
                <input type="number" name="telegram_id" placeholder="Telegram ID (Bot থেকে নিন)" required>
                <input type="password" name="password" placeholder="Set Password" required>
                <button class="btn-blue bg-green-600 mt-4">CREATE ACCOUNT</button>
            </form>
            <p class="mt-6 text-sm text-gray-400">ইতিমধ্যে একাউন্ট আছে? <a href="/login" class="text-blue-400">লগইন করুন</a></p>
        </div>
    </body></html>""")

@app.route('/movie/<id>')
def movie_details(id):
    user = get_user()
    if not user: return redirect('/login')
    movie = movies_col.find_one({"_id": ObjectId(id)})
    config = settings_col.find_one({"type": "site_config"})
    return render_template_string(BASE_LAYOUT + """
    {% block content %}
    <div class="max-w-4xl mx-auto flex flex-col md:flex-row gap-8">
        <img src="{{ movie.poster }}" class="w-full md:w-64 rounded-3xl shadow-2xl border border-white/10">
        <div class="flex-1">
            <h1 class="text-3xl font-black mb-2">{{ movie.title }}</h1>
            <span class="bg-blue-600 px-3 py-1 rounded-full text-[10px] font-bold">{{ movie.category }}</span>
            <div class="mt-10">
                <h3 class="text-gray-400 font-bold mb-4 border-l-4 border-blue-500 pl-2">এপিসোড তালিকা:</h3>
                <div class="grid grid-cols-3 md:grid-cols-6 gap-3">
                    {% for ep in movie.episodes %}
                    <button onclick="play('{{ ep.link }}')" class="glass p-3 rounded-xl text-xs font-bold border-b-2 border-blue-500 hover:bg-blue-600 transition">
                        EP {{ loop.index }}
                    </button>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    <script>
        async function play(link) {
            const res = await fetch('/api/check-access', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mobile:'{{ user.mobile }}'})});
            const data = await res.json();
            if(data.status === 'unlocked') { window.open(link, '_blank'); }
            else { 
                alert("⚠️ Ad Lock! বাটন আনলক করতে একটি এড দেখুন।"); 
                if(data.ad_config.active_type === 'direct') { window.open(data.ad_config.direct_link, '_blank'); unlock(); }
            }
        }
        function unlock() { fetch('/api/unlock', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mobile:'{{ user.mobile }}'})}).then(()=>location.reload()); }
    </script>
    {% endblock %}""", movie=movie, user=user, active='home', config=config)

# ==========================================
# ৫. এডমিন প্যানেল (Full Features + Dashboard)
# ==========================================

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin/dashboard')
    if session.get('admin'): return redirect('/admin/dashboard')
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">""" + CSS + """</head>
    <body class="flex items-center justify-center min-h-screen p-6">
        <form method="POST" class="glass p-8 rounded-3xl w-full max-w-sm text-center">
            <h1 class="text-2xl font-bold text-red-500 mb-6">ADMIN LOGIN</h1>
            <input type="password" name="password" placeholder="Admin Password" required class="w-full mb-4">
            <button class="btn-blue bg-red-600 w-full font-bold">ENTER DASHBOARD</button>
        </form>
    </body></html>""")

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'): return redirect('/admin')
    config = settings_col.find_one({"type": "site_config"})
    ep_c = ep_ads_col.find_one({"type": "ep_ad_config"})
    movies = list(movies_col.find().sort('_id', -1))
    plans = list(plans_col.find())
    tasks = list(tasks_col.find())
    u_count = users_col.count_documents({})
    
    return render_template_string("""
    <!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script><link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    """ + CSS + """</head>
    <body class="flex flex-col md:flex-row min-h-screen">
        <div class="w-full md:w-64 glass p-6 space-y-6">
            <h1 class="text-xl font-bold text-blue-400 text-center">ADMIN PANEL</h1>
            <nav class="flex flex-col gap-2">
                <a href="/admin/dashboard" class="p-3 bg-white/5 rounded-xl"><i class="fas fa-home mr-3"></i> Dashboard</a>
                <a href="#movies" class="p-3 hover:bg-white/5 rounded-xl"><i class="fas fa-film mr-3"></i> Movies</a>
                <a href="#tasks" class="p-3 hover:bg-white/5 rounded-xl"><i class="fas fa-link mr-3"></i> Tasks</a>
                <a href="#ep_ads" class="p-3 hover:bg-white/5 rounded-xl text-red-400"><i class="fas fa-lock mr-3"></i> Ep Ad Lock</a>
                <a href="#plans" class="p-3 hover:bg-white/5 rounded-xl text-purple-400"><i class="fas fa-crown mr-3"></i> Premium Plans</a>
                <a href="/admin/logout" class="p-3 text-red-500"><i class="fas fa-sign-out-alt mr-3"></i> Logout</a>
            </nav>
        </div>
        <div class="flex-1 p-6 space-y-8 overflow-y-auto">
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400">USERS</p><p class="text-2xl font-bold">{{ u_count }}</p></div>
                <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400">MOVIES</p><p class="text-2xl font-bold">{{ m_count }}</p></div>
            </div>

            <section id="ep_ads" class="glass p-6 rounded-3xl">
                <h2 class="text-lg font-bold mb-4 text-red-400 border-b border-white/5 pb-2">Episode Ad Config</h2>
                <form action="/admin/update-ep-ads" method="POST" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input type="text" name="direct_link" value="{{ ep_c.direct_link }}" placeholder="Direct Ad Link">
                    <input type="text" name="monetag_id" value="{{ ep_c.monetag_id }}" placeholder="Monetag Zone ID">
                    <input type="number" name="unlock_minutes" value="{{ ep_c.unlock_minutes }}" placeholder="Minutes">
                    <select name="active_type">
                        <option value="direct" {% if ep_c.active_type=='direct' %}selected{% endif %}>Direct Link</option>
                        <option value="off" {% if ep_c.active_type=='off' %}selected{% endif %}>OFF</option>
                    </select>
                    <button class="btn-blue bg-red-600 md:col-span-2">UPDATE AD LOCK</button>
                </form>
            </section>

            <section id="movies" class="glass p-6 rounded-3xl">
                <h2 class="text-lg font-bold mb-4 text-blue-400 border-b border-white/5 pb-2">Movies</h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead><tr class="text-gray-500 text-xs"><th>TITLE</th><th>EPISODES</th><th>ACTION</th></tr></thead>
                        <tbody>
                            {% for m in movies %}
                            <tr class="border-b border-white/5">
                                <td class="p-3">{{ m.title }}</td>
                                <td class="p-3">{{ m.episodes|length }}</td>
                                <td class="p-3"><a href="/admin/movie/delete/{{ m._id }}" class="text-red-500">Delete</a></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </section>

            <section id="settings" class="glass p-6 rounded-3xl">
                <h2 class="text-lg font-bold mb-4 border-b border-white/5 pb-2">Site Settings</h2>
                <form action="/admin/update-settings" method="POST" class="space-y-4">
                    <input type="text" name="site_name" value="{{ config.site_name }}" class="w-full">
                    <input type="text" name="site_logo" value="{{ config.site_logo }}" class="w-full">
                    <textarea name="header_notice" class="w-full">{{ config.header_notice }}</textarea>
                    <button class="btn-blue w-full">SAVE ALL SETTINGS</button>
                </form>
            </section>
        </div>
    </body></html>""", config=config, ep_c=ep_c, movies=movies, u_count=u_count, m_count=len(movies), plans=plans, tasks=tasks)

@app.route('/admin/update-settings', methods=['POST'])
def admin_up_set():
    if not session.get('admin'): return redirect('/admin')
    settings_col.update_one({"type": "site_config"}, {"$set": request.form.to_dict()})
    return redirect('/admin/dashboard')

@app.route('/admin/update-ep-ads', methods=['POST'])
def admin_up_ep():
    if not session.get('admin'): return redirect('/admin')
    ep_ads_col.update_one({"type": "ep_ad_config"}, {"$set": request.form.to_dict()})
    return redirect('/admin/dashboard')

@app.route('/admin/movie/delete/<id>')
def admin_del_mov(id):
    if not session.get('admin'): return redirect('/admin')
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin/dashboard')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin')

# ==========================================
# ৬. API এন্ডপয়েন্টস (Access & Unlock)
# ==========================================

@app.route('/api/check-access', methods=['POST'])
def api_check():
    user = users_col.find_one({"mobile": str(request.json.get('mobile'))})
    if user.get('is_premium'): return jsonify({"status": "unlocked"})
    unlock = ep_unlock_col.find_one({"mobile": str(user['mobile'])})
    if unlock and datetime.now() < unlock['expiry']: return jsonify({"status": "unlocked"})
    return jsonify({"status": "locked", "ad_config": ep_ads_col.find_one({"type": "ep_ad_config"})})

@app.route('/api/unlock', methods=['POST'])
def api_unlock():
    mobile = str(request.json.get('mobile'))
    config = ep_ads_col.find_one({"type": "ep_ad_config"})
    expiry = datetime.now() + timedelta(minutes=int(config['unlock_minutes']))
    ep_unlock_col.update_one({"mobile": mobile}, {"$set": {"expiry": expiry}}, upsert=True)
    return jsonify({"status": "success"})

# ==========================================
# ৭. টেলিগ্রাম বট ও ওয়েব হুক
# ==========================================

@app.route('/api/webhook', methods=['POST'])
def webhook_handler():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return ''
    return 'Forbidden', 403

@bot.message_handler(commands=['start'])
def bot_welcome(message):
    bot.reply_to(message, f"👋 স্বাগতম!\nআপনার টেলিগ্রাম আইডি: `{message.from_user.id}`")

@bot.message_handler(commands=['movie'])
def bot_add_movie(message):
    if message.from_user.id not in ADMIN_IDS: return bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
    msg = bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন:")
    bot.register_next_step_handler(msg, step_title)

def step_title(message):
    title = message.text
    msg = bot.send_message(message.chat.id, "📂 ক্যাটাগরি:")
    bot.register_next_step_handler(msg, lambda m: step_cat(m, title))

def step_cat(message, title):
    cat = message.text
    msg = bot.send_message(message.chat.id, "🖼 পোস্টার লিংক দিন:")
    bot.register_next_step_handler(msg, lambda m: step_files(m, title, cat))

def step_files(message, title, cat):
    poster = message.text
    msg = bot.send_message(message.chat.id, "📥 ভিডিও/ডকুমেন্ট পাঠান। শেষ হলে /done লিখুন।")
    bot.register_next_step_handler(msg, lambda m: collect_eps(m, title, cat, poster, []))

def collect_eps(message, title, cat, poster, eps):
    if message.text == "/done":
        movies_col.insert_one({"title": title, "category": cat, "poster": poster, "episodes": eps})
        return bot.send_message(message.chat.id, f"✅ মুভি সফলভাবে যোগ হয়েছে: {title}")
    if message.content_type in ['video', 'document']:
        sent = bot.forward_message(FILE_CHANNEL_ID, message.chat.id, message.message_id)
        ep_name = f"{title} - Episode {len(eps)+1}"
        eps.append({"name": ep_name, "link": f"https://t.me/c/{str(FILE_CHANNEL_ID).replace('-100','')}/{sent.message_id}"})
        bot.send_message(message.chat.id, f"📥 {ep_name} যোগ হয়েছে।")
    bot.register_next_step_handler(message, lambda m: collect_eps(m, title, cat, poster, eps))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
