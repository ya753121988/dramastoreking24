import os
import telebot
import random
import string
from pymongo import MongoClient
from flask import Flask, jsonify, request, render_template_string, redirect, url_for
from threading import Thread
from flask_cors import CORS
from bson.objectid import ObjectId
from datetime import datetime, timedelta

# --- ১. কনফিগারেশন ও ডাটাবেস সেটআপ ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
FILE_CHANNEL_ID = os.getenv("FILE_CHANNEL_ID")

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

# ডিফল্ট সেটিংস ডাটাবেসে না থাকলে তৈরি করা
if not settings_col.find_one({"type": "site_config"}):
    settings_col.insert_one({
        "type": "site_config", "site_name": "Premium Movies",
        "site_logo": "https://via.placeholder.com/200x60",
        "header_notice": "আমাদের সাইটে স্বাগতম! টাস্ক করে প্রিমিয়াম নিন। 👑",
        "movies_per_page": 12
    })
if not ep_ads_col.find_one({"type": "ep_ad_config"}):
    ep_ads_col.insert_one({
        "type": "ep_ad_config", "direct_link": "", "monetag_id": "",
        "daily_limit": 5, "unlock_minutes": 30, "active_type": "off"
    })

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app)
user_states = {}

# ---------------------------------------------------------
# ২. ইউজার অথেনটিকেশন ও প্রোফাইল API
# ---------------------------------------------------------

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.json
    mobile = data.get('mobile')
    if users_col.find_one({"mobile": mobile}):
        return jsonify({"status": "error", "message": "এই নাম্বারটি ইতিমধ্যে নিবন্ধিত!"}), 400
    
    users_col.insert_one({
        "first_name": data.get('first_name'), "last_name": data.get('last_name'),
        "mobile": mobile, "telegram_id": data.get('telegram_id'),
        "password": data.get('password'), "balance": 0, "is_premium": False,
        "premium_expiry": None, "joined_at": datetime.now()
    })
    return jsonify({"status": "success", "message": "নিবন্ধন সফল হয়েছে!"})

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.json
    user = users_col.find_one({"mobile": data.get('mobile'), "password": data.get('password')})
    if user:
        user['_id'] = str(user['_id'])
        # প্রিমিয়াম এক্সপায়ার চেক
        if user.get('is_premium') and user.get('premium_expiry') and datetime.now() > user['premium_expiry']:
            users_col.update_one({"mobile": user['mobile']}, {"$set": {"is_premium": False}})
            user['is_premium'] = False
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "error", "message": "নাম্বার বা পাসওয়ার্ড ভুল!"}), 401

@app.route('/api/user/profile/<mobile>', methods=['GET'])
def get_user_profile(mobile):
    user = users_col.find_one({"mobile": mobile}, {"_id": 0, "password": 0})
    return jsonify(user)

@app.route('/api/user/update', methods=['POST'])
def update_profile():
    data = request.json
    users_col.update_one({"mobile": data.get('mobile')}, {"$set": {
        "first_name": data.get('first_name'), "last_name": data.get('last_name'), "password": data.get('password')
    }})
    return jsonify({"status": "success", "message": "প্রোফাইল আপডেট হয়েছে!"})

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    user = users_col.find_one({"mobile": data.get('mobile'), "telegram_id": data.get('telegram_id')})
    if not user: return jsonify({"status": "error", "message": "ইউজার খুঁজে পাওয়া যায়নি!"}), 404
    
    otp = ''.join(random.choices(string.digits, k=6))
    otp_col.update_one({"mobile": user['mobile']}, {"$set": {"otp": otp, "created_at": datetime.now()}}, upsert=True)
    try:
        bot.send_message(user['telegram_id'], f"🔐 আপনার পাসওয়ার্ড রিসেট ওটিপি কোড: {otp}")
        return jsonify({"status": "success", "message": "টেলিগ্রামে ওটিপি পাঠানো হয়েছে!"})
    except:
        return jsonify({"status": "error", "message": "বটকে মেসেজ পাঠানো যাচ্ছে না। বট স্টার্ট করুন!"}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    res = otp_col.find_one({"mobile": data.get('mobile'), "otp": data.get('otp')})
    if res:
        users_col.update_one({"mobile": data.get('mobile')}, {"$set": {"password": data.get('password')}})
        otp_col.delete_one({"mobile": data.get('mobile')})
        return jsonify({"status": "success", "message": "পাসওয়ার্ড রিসেট সফল!"})
    return jsonify({"status": "error", "message": "ভুল ওটিপি!"}), 400

# ---------------------------------------------------------
# ৩. টাস্ক, প্রিমিয়াম ও ইপিসোড লক API
# ---------------------------------------------------------

@app.route('/api/movies', methods=['GET'])
def get_site_movies():
    page = int(request.args.get('page', 1))
    conf = settings_col.find_one({"type": "site_config"})
    limit = conf.get('movies_per_page', 12)
    skip = (page - 1) * limit
    total = movies_col.count_documents({})
    movies = list(movies_col.find().sort('_id', -1).skip(skip).limit(limit))
    for m in movies: m['_id'] = str(m['_id'])
    return jsonify({"movies": movies, "total": total, "current_page": page, "per_page": limit})

@app.route('/api/settings', methods=['GET'])
def get_site_settings():
    return jsonify(settings_col.find_one({"type": "site_config"}, {"_id": 0}))

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    d_tasks = list(tasks_col.find())
    m_tasks = list(monetag_tasks_col.find())
    for t in d_tasks + m_tasks: t['_id'] = str(t['_id'])
    return jsonify({"direct": d_tasks, "monetag": m_tasks})

@app.route('/api/tasks/complete', methods=['POST'])
def complete_task_reward():
    data = request.json
    t_type = data.get('type')
    col = monetag_tasks_col if t_type == 'monetag' else tasks_col
    task = col.find_one({"_id": ObjectId(data.get('task_id'))})
    today = datetime.now().strftime("%Y-%m-%d")
    
    history = user_tasks_history.find_one({"mobile": data.get('mobile'), "task_id": data.get('task_id'), "date": today})
    if history and history['count'] >= int(task['daily_limit']):
        return jsonify({"status": "error", "message": "ডেইলি লিমিট শেষ!"}), 400
    
    users_col.update_one({"mobile": data.get('mobile')}, {"$inc": {"balance": int(task['coins'])}})
    user_tasks_history.update_one({"mobile": data.get('mobile'), "task_id": data.get('task_id'), "date": today}, {"$inc": {"count": 1}}, upsert=True)
    return jsonify({"status": "success", "message": f"{task['coins']} কয়েন যোগ হয়েছে!"})

@app.route('/api/premium/plans', methods=['GET'])
def get_plans():
    plans = list(plans_col.find())
    for p in plans: p['_id'] = str(p['_id'])
    return jsonify(plans)

@app.route('/api/premium/buy', methods=['POST'])
def buy_premium_member():
    data = request.json
    plan = plans_col.find_one({"_id": ObjectId(data.get('plan_id'))})
    user = users_col.find_one({"mobile": data.get('mobile')})
    
    if user['balance'] < int(plan['coins']):
        return jsonify({"status": "error", "message": "পর্যাপ্ত কয়েন নেই!"}), 400
    
    start_date = user['premium_expiry'] if user.get('is_premium') and user['premium_expiry'] > datetime.now() else datetime.now()
    new_expiry = start_date + timedelta(days=int(plan['days']))
    
    users_col.update_one({"mobile": data.get('mobile')}, {
        "$inc": {"balance": -int(plan['coins'])},
        "$set": {"is_premium": True, "premium_expiry": new_expiry}
    })
    return jsonify({"status": "success", "message": f"{plan['days']} দিনের প্রিমিয়াম মেম্বারশিপ সফল!"})

@app.route('/api/episode/check-access', methods=['POST'])
def check_ep_access():
    data = request.json
    user = users_col.find_one({"mobile": data.get('mobile')})
    if user.get('is_premium'): return jsonify({"status": "unlocked"})
    
    unlock = ep_unlock_col.find_one({"mobile": data.get('mobile')})
    if unlock and datetime.now() < unlock['expiry']:
        return jsonify({"status": "unlocked"})
    
    return jsonify({"status": "locked", "ad_config": ep_ads_col.find_one({"type": "ep_ad_config"})})

@app.route('/api/episode/unlock', methods=['POST'])
def unlock_ep_with_ad():
    config = ep_ads_col.find_one({"type": "ep_ad_config"})
    expiry = datetime.now() + timedelta(minutes=int(config['unlock_minutes']))
    ep_unlock_col.update_one({"mobile": request.json.get('mobile')}, {"$set": {"expiry": expiry}}, upsert=True)
    return jsonify({"status": "success"})

# ---------------------------------------------------------
# ৪. প্রিমিয়াম অ্যাডমিন প্যানেল UI
# ---------------------------------------------------------

ADMIN_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Admin Panel</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>body{background:#0b0f19;color:white;font-family:sans-serif;}.glass{background:rgba(30,41,59,0.7);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.1);}</style>
</head>
<body class="flex flex-col md:flex-row min-h-screen">
    <!-- Sidebar -->
    <div class="w-full md:w-64 glass p-6 space-y-6">
        <h1 class="text-xl font-bold text-blue-400 text-center">MASTER ADMIN</h1>
        <nav class="space-y-1 text-sm">
            <a href="/admin" class="flex items-center p-3 hover:bg-blue-500/10 rounded-xl transition"><i class="fas fa-home mr-3"></i> Dashboard</a>
            <a href="#movies" class="flex items-center p-3 hover:bg-blue-500/10 rounded-xl transition"><i class="fas fa-film mr-3"></i> Movies</a>
            <a href="#ep_ads" class="flex items-center p-3 hover:bg-red-500/10 rounded-xl transition text-red-400 font-bold"><i class="fas fa-lock mr-3"></i> Episode Ad Lock</a>
            <a href="#tasks" class="flex items-center p-3 hover:bg-green-500/10 rounded-xl transition text-green-400"><i class="fas fa-tasks mr-3"></i> Tasks (Direct/Ads)</a>
            <a href="#plans" class="flex items-center p-3 hover:bg-purple-500/10 rounded-xl transition text-purple-400 font-bold"><i class="fas fa-crown mr-3"></i> Premium Plans</a>
            <a href="#settings" class="flex items-center p-3 hover:bg-gray-500/10 rounded-xl transition text-gray-400"><i class="fas fa-cog mr-3"></i> Settings</a>
        </nav>
    </div>

    <!-- Main Content -->
    <div class="flex-1 p-6 space-y-8 overflow-y-auto">
        <!-- Stats -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400 uppercase">Users</p><p class="text-2xl font-bold text-blue-400">{{u_count}}</p></div>
            <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400 uppercase">Movies</p><p class="text-2xl font-bold text-green-400">{{m_count}}</p></div>
        </div>

        <!-- Episode Ad System -->
        <div id="ep_ads" class="glass p-6 rounded-3xl border-red-500/20 border">
            <h2 class="text-xl font-bold mb-6 text-red-400"><i class="fas fa-shield-alt mr-2"></i>Episode Ad Lock System</h2>
            <form action="/admin/update-ep-ads" method="POST" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input type="text" name="direct_link" value="{{ep_c.direct_link}}" placeholder="Direct Ad Link" class="bg-black/30 p-3 rounded-xl border border-white/10">
                    <input type="text" name="monetag_id" value="{{ep_c.monetag_id}}" placeholder="Monetag Zone ID" class="bg-black/30 p-3 rounded-xl border border-white/10">
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <input type="number" name="daily_limit" value="{{ep_c.daily_limit}}" placeholder="Daily Limit" class="bg-black/30 p-3 rounded-xl border border-white/10">
                    <input type="number" name="unlock_minutes" value="{{ep_c.unlock_minutes}}" placeholder="Unlock Minutes" class="bg-black/30 p-3 rounded-xl border border-white/10">
                    <select name="active_type" class="bg-black/30 p-3 rounded-xl border border-white/10">
                        <option value="direct" {% if ep_c.active_type == 'direct' %}selected{% endif %}>Direct Link</option>
                        <option value="monetag" {% if ep_c.active_type == 'monetag' %}selected{% endif %}>Monetag Script</option>
                        <option value="off" {% if ep_c.active_type == 'off' %}selected{% endif %}>Turn Off Ads</option>
                    </select>
                </div>
                <button class="w-full bg-red-600 p-3 rounded-xl font-bold">Save Episode Ad Config</button>
            </form>
        </div>

        <!-- Premium Plans -->
        <div id="plans" class="glass p-6 rounded-3xl">
            <h2 class="text-xl font-bold mb-6 text-purple-400"><i class="fas fa-gem mr-2"></i>Premium Member Plans</h2>
            <form action="/admin/add-plan" method="POST" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <input type="number" name="days" placeholder="Days" class="bg-black/20 p-3 rounded-xl border border-white/10" required>
                <input type="number" name="coins" placeholder="Coins" class="bg-black/20 p-3 rounded-xl border border-white/10" required>
                <button class="bg-purple-600 p-3 rounded-xl font-bold">Add Plan</button>
            </form>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {% for p in plans %}<div class="flex justify-between items-center bg-white/5 p-4 rounded-xl"><span>{{p.days}} Days - {{p.coins}} Coins</span><a href="/admin/plan/delete/{{p._id}}" class="text-red-500"><i class="fas fa-trash"></i></a></div>{% endfor %}
            </div>
        </div>

        <!-- Daily Tasks (Direct & Monetag) -->
        <div id="tasks" class="glass p-6 rounded-3xl">
            <h2 class="text-xl font-bold mb-6 text-green-400">Manage Income Tasks</h2>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <!-- Direct Link -->
                <div class="space-y-4">
                    <h3 class="font-bold border-b border-white/10 pb-2">Direct Link Tasks</h3>
                    <form action="/admin/task/add" method="POST" class="space-y-2">
                        <input type="text" name="link" placeholder="Link" class="w-full bg-black/20 p-2 rounded-lg text-sm border border-white/10" required>
                        <div class="flex gap-2">
                            <input type="number" name="coins" placeholder="Coins" class="w-1/2 bg-black/20 p-2 rounded-lg text-sm border border-white/10" required>
                            <input type="number" name="limit" placeholder="Limit" class="w-1/2 bg-black/20 p-2 rounded-lg text-sm border border-white/10" required>
                        </div>
                        <button class="w-full bg-green-700 p-2 rounded-lg text-xs font-bold">Add Link Task</button>
                    </form>
                    {% for t in tasks %}<div class="text-[10px] bg-black/30 p-2 rounded flex justify-between"><span>{{t.link[:30]}}..</span><a href="/admin/task/delete/{{t._id}}" class="text-red-400">X</a></div>{% endfor %}
                </div>
                <!-- Monetag Ads -->
                <div class="space-y-4">
                    <h3 class="font-bold border-b border-white/10 pb-2 text-yellow-400">Monetag Ad Tasks</h3>
                    <form action="/admin/monetag/add" method="POST" class="space-y-2">
                        <input type="text" name="zone_id" placeholder="Zone ID" class="w-full bg-black/20 p-2 rounded-lg text-sm border border-white/10" required>
                        <div class="flex gap-2">
                            <input type="number" name="coins" placeholder="Coins" class="w-1/2 bg-black/20 p-2 rounded-lg text-sm border border-white/10" required>
                            <input type="number" name="limit" placeholder="Limit" class="w-1/2 bg-black/20 p-2 rounded-lg text-sm border border-white/10" required>
                        </div>
                        <button class="w-full bg-yellow-600 p-2 rounded-lg text-xs font-bold text-black">Add Ad Task</button>
                    </form>
                    {% for mt in m_tasks %}<div class="text-[10px] bg-black/30 p-2 rounded flex justify-between"><span>Zone: {{mt.zone_id}}</span><a href="/admin/monetag/delete/{{mt._id}}" class="text-red-400">X</a></div>{% endfor %}
                </div>
            </div>
        </div>

        <!-- Site Settings -->
        <div id="settings" class="glass p-6 rounded-3xl">
            <h2 class="text-xl font-bold mb-4 text-blue-400">Site Configuration</h2>
            <form action="/admin/update-settings" method="POST" class="space-y-4">
                <input type="text" name="site_name" value="{{config.site_name}}" class="w-full bg-black/20 p-3 rounded-xl border border-white/10">
                <input type="text" name="site_logo" value="{{config.site_logo}}" class="w-full bg-black/20 p-3 rounded-xl border border-white/10">
                <textarea name="header_notice" class="w-full bg-black/20 p-3 rounded-xl border border-white/10 h-24">{{config.header_notice}}</textarea>
                <input type="number" name="movies_per_page" value="{{config.movies_per_page}}" class="w-full bg-black/20 p-3 rounded-xl border border-white/10">
                <button class="w-full bg-blue-600 p-3 rounded-xl font-bold transition">Update All Settings</button>
            </form>
        </div>

        <!-- Movie Management (Range Add) -->
        <div id="movies" class="glass p-6 rounded-3xl">
            <h2 class="text-xl font-bold mb-6 text-blue-400">Movie Management</h2>
            <form action="/admin/add-range" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <input type="text" name="title" placeholder="Movie Name" class="md:col-span-2 bg-black/20 p-3 rounded-xl border border-white/10" required>
                <input type="number" name="start_id" placeholder="Start Msg ID" class="bg-black/20 p-3 rounded-xl border border-white/10" required>
                <input type="number" name="end_id" placeholder="End Msg ID" class="bg-black/20 p-3 rounded-xl border border-white/10" required>
                <button class="md:col-span-4 bg-indigo-600 p-3 rounded-xl font-bold">Add Movie from Telegram Range</button>
            </form>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm">
                    <thead><tr class="text-gray-500 uppercase text-xs"><th class="p-3">Title</th><th>Action</th></tr></thead>
                    <tbody>
                        {% for m in movies %}<tr class="border-b border-white/5">
                            <td class="p-3">{{m.title}}</td>
                            <td class="p-3"><a href="/admin/delete/{{m._id}}" class="text-red-500" onclick="return confirm('Delete?')">Delete</a></td>
                        </tr>{% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_UI, 
    config=settings_col.find_one({"type":"site_config"}),
    ep_c=ep_ads_col.find_one({"type":"ep_ad_config"}),
    u_count=users_col.count_documents({}),
    m_count=movies_col.count_documents({}),
    movies=list(movies_col.find().sort('_id', -1)),
    plans=list(plans_col.find()),
    tasks=list(tasks_col.find()),
    m_tasks=list(monetag_tasks_col.find()))

@app.route('/admin/update-ep-ads', methods=['POST'])
def admin_update_ep_ads():
    ep_ads_col.update_one({"type": "ep_ad_config"}, {"$set": {
        "direct_link": request.form.get('direct_link'), "monetag_id": request.form.get('monetag_id'),
        "daily_limit": request.form.get('daily_limit'), "unlock_minutes": request.form.get('unlock_minutes'),
        "active_type": request.form.get('active_type')
    }}, upsert=True)
    return redirect('/admin')

@app.route('/admin/add-range', methods=['POST'])
def admin_add_movie_range():
    title = request.form.get('title')
    start = int(request.form.get('start_id'))
    end = int(request.form.get('end_id'))
    chan_id = str(FILE_CHANNEL_ID).replace("-100", "")
    episodes = [{"name": f"{title} - Episode {idx+1}", "link": f"https://t.me/c/{chan_id}/{i}"} for idx, i in enumerate(range(start, end + 1))]
    movies_col.insert_one({"title": title, "category": "Action", "poster": "https://via.placeholder.com/300x450", "episodes": episodes})
    return redirect('/admin')

@app.route('/admin/add-plan', methods=['POST'])
def admin_add_premium_plan():
    plans_col.insert_one({"days": request.form.get('days'), "coins": request.form.get('coins')})
    return redirect('/admin')

@app.route('/admin/plan/delete/<id>')
def admin_del_plan(id):
    plans_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin')

@app.route('/admin/task/add', methods=['POST'])
def admin_add_link_task():
    tasks_col.insert_one({"link": request.form.get('link'), "coins": request.form.get('coins'), "daily_limit": request.form.get('limit'), "type": "direct"})
    return redirect('/admin')

@app.route('/admin/monetag/add', methods=['POST'])
def admin_add_monetag_task():
    monetag_tasks_col.insert_one({"zone_id": request.form.get('zone_id'), "coins": request.form.get('coins'), "daily_limit": request.form.get('limit'), "type": "monetag"})
    return redirect('/admin')

@app.route('/admin/update-settings', methods=['POST'])
def admin_save_settings():
    settings_col.update_one({"type": "site_config"}, {"$set": {
        "site_name": request.form.get('site_name'), "site_logo": request.form.get('site_logo'),
        "header_notice": request.form.get('header_notice'), "movies_per_page": int(request.form.get('movies_per_page'))
    }})
    return redirect('/admin')

@app.route('/admin/delete/<id>')
def admin_del_movie(id):
    movies_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin')

# ---------------------------------------------------------
# ৫. টেলিগ্রাম বট ও মুভি এডিং লজিক
# ---------------------------------------------------------

@bot.message_handler(commands=['start'])
def bot_start(message):
    bot.reply_to(message, f"👋 স্বাগতম!\nআপনার টেলিগ্রাম আইডি: `{message.chat.id}`\nপাসওয়ার্ড রিসেট করতে এই আইডিটি ব্যবহার করুন।")

@bot.message_handler(commands=['movie'])
def bot_add_movie_interactive(message):
    user_states[message.chat.id] = {"episodes": []}
    bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন:")
    bot.register_next_step_handler(message, bot_get_movie_title)

def bot_get_movie_title(message):
    user_states[message.chat.id]['title'] = message.text
    bot.send_message(message.chat.id, "📂 ক্যাটাগরি লিখুন:")
    bot.register_next_step_handler(message, bot_get_movie_cat)

def bot_get_movie_cat(message):
    user_states[message.chat.id]['category'] = message.text
    bot.send_message(message.chat.id, "🖼 পোস্টার লিংক দিন:")
    bot.register_next_step_handler(message, bot_get_movie_files)

def bot_get_movie_files(message):
    chat_id = message.chat.id
    if message.text == "/done":
        movies_col.insert_one(user_states[chat_id])
        bot.send_message(chat_id, "✅ মুভি সফলভাবে যোগ হয়েছে!")
        del user_states[chat_id]; return
    
    if message.content_type in ['video', 'document']:
        sent = bot.forward_message(FILE_CHANNEL_ID, chat_id, message.message_id)
        chan_id = str(FILE_CHANNEL_ID).replace("-100", "")
        ep_name = f"{user_states[chat_id]['title']} - Episode {len(user_states[chat_id]['episodes'])+1}"
        user_states[chat_id]['episodes'].append({"name": ep_name, "link": f"https://t.me/c/{chan_id}/{sent.message_id}"})
        bot.send_message(chat_id, f"📥 যোগ হয়েছে: {ep_name}")
    
    bot.register_next_step_handler(message, bot_get_movie_files)

# ---------------------------------------------------------
# ৬. রান অ্যাপ্লিকেশন
# ---------------------------------------------------------

if __name__ == "__main__":
    t = Thread(target=lambda: app.run(host="0.0.0.0", port=8080))
    t.start()
    bot.infinity_polling()
