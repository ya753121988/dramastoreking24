import os
import telebot
import random
import string
import time
from pymongo import MongoClient
from flask import Flask, jsonify, request, render_template_string, redirect, url_for
from flask_cors import CORS
from bson.objectid import ObjectId
from datetime import datetime, timedelta

# ==========================================
# ১. কনফিগারেশন ও ডাটাবেস সেটআপ
# ==========================================
BOT_TOKEN = "8655043839:AAGMxkYoZXR-nUzlcapZZfVwci09Z6x0-UE"
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0"
FILE_CHANNEL_ID = -1003985353441 
ADMIN_IDS = [7120801813]

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

# ডিফল্ট সেটিংস ইনিশিয়ালাইজেশন
def init_db_settings():
    if not settings_col.find_one({"type": "site_config"}):
        settings_col.insert_one({
            "type": "site_config", "site_name": "Premium Movies", 
            "site_logo": "https://via.placeholder.com/200x60",
            "header_notice": "আমাদের সাইটে স্বাগতম! 🍿", "movies_per_page": 12
        })
    if not ep_ads_col.find_one({"type": "ep_ad_config"}):
        ep_ads_col.insert_one({
            "type": "ep_ad_config", "direct_link": "", "monetag_id": "",
            "unlock_minutes": 30, "active_type": "off", "daily_limit": 10
        })

init_db_settings()

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
CORS(app)

# ==========================================
# ২. ইউজার অথেনটিকেশন ও প্রোফাইল API
# ==========================================

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.json
    mobile = data.get('mobile')
    if users_col.find_one({"mobile": mobile}):
        return jsonify({"status": "error", "message": "এই নাম্বারটি ইতিমধ্যে নিবন্ধিত!"}), 400
    
    users_col.insert_one({
        "first_name": data.get('first_name'),
        "last_name": data.get('last_name'),
        "mobile": mobile,
        "telegram_id": int(data.get('telegram_id')),
        "password": data.get('password'),
        "balance": 0,
        "is_premium": False,
        "premium_expiry": None,
        "joined_at": datetime.now()
    })
    return jsonify({"status": "success", "message": "নিবন্ধন সফল!"})

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    user = users_col.find_one({"mobile": data.get('mobile'), "password": data.get('password')})
    if user:
        user['_id'] = str(user['_id'])
        # প্রিমিয়াম এক্সপায়ার চেক
        if user.get('is_premium') and user.get('premium_expiry'):
            if datetime.now() > user['premium_expiry']:
                users_col.update_one({"mobile": user['mobile']}, {"$set": {"is_premium": False}})
                user['is_premium'] = False
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "error", "message": "মোবাইল বা পাসওয়ার্ড ভুল!"}), 401

@app.route('/api/user/update', methods=['POST'])
def api_update_user():
    data = request.json
    mobile = data.get('mobile')
    users_col.update_one({"mobile": mobile}, {"$set": {
        "first_name": data.get('first_name'),
        "last_name": data.get('last_name'),
        "password": data.get('password')
    }})
    return jsonify({"status": "success", "message": "প্রোফাইল আপডেট হয়েছে!"})

@app.route('/api/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    data = request.json
    mobile = data.get('mobile')
    telegram_id = int(data.get('telegram_id'))
    user = users_col.find_one({"mobile": mobile, "telegram_id": telegram_id})
    if not user: return jsonify({"status": "error", "message": "তথ্য মেলেনি!"}), 404
    
    otp = ''.join(random.choices(string.digits, k=6))
    otp_col.update_one({"mobile": mobile}, {"$set": {"otp": otp, "created_at": datetime.now()}}, upsert=True)
    try:
        bot.send_message(telegram_id, f"🔐 আপনার পাসওয়ার্ড রিসেট ওটিপি কোড: {otp}")
        return jsonify({"status": "success", "message": "টেলিগ্রামে ওটিপি পাঠানো হয়েছে!"})
    except:
        return jsonify({"status": "error", "message": "বটকে মেসেজ পাঠানো যাচ্ছে না। বট স্টার্ট করুন!"}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
def api_reset_password():
    data = request.json
    res = otp_col.find_one({"mobile": data.get('mobile'), "otp": data.get('otp')})
    if res:
        users_col.update_one({"mobile": data.get('mobile')}, {"$set": {"password": data.get('password')}})
        otp_col.delete_one({"mobile": data.get('mobile')})
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "ভুল ওটিপি!"}), 400

# ==========================================
# ৩. মুভি, টাস্ক ও প্রিমিয়াম API
# ==========================================

@app.route('/api/movies', methods=['GET'])
def api_get_movies():
    page = int(request.args.get('page', 1))
    conf = settings_col.find_one({"type": "site_config"})
    limit = conf.get('movies_per_page', 12)
    skip = (page - 1) * limit
    total = movies_col.count_documents({})
    movies = list(movies_col.find().sort('_id', -1).skip(skip).limit(limit))
    for m in movies: m['_id'] = str(m['_id'])
    return jsonify({"movies": movies, "total": total, "current_page": page})

@app.route('/api/tasks/complete', methods=['POST'])
def api_complete_task():
    data = request.json
    task_id = data.get('task_id')
    task_type = data.get('type') # 'direct' or 'monetag'
    col = monetag_tasks_col if task_type == 'monetag' else tasks_col
    task = col.find_one({"_id": ObjectId(task_id)})
    today = datetime.now().strftime("%Y-%m-%d")
    
    history = user_tasks_history.find_one({"mobile": data.get('mobile'), "task_id": task_id, "date": today})
    if history and history['count'] >= int(task['daily_limit']):
        return jsonify({"status": "error", "message": "লিমিট শেষ!"}), 400
    
    users_col.update_one({"mobile": data.get('mobile')}, {"$inc": {"balance": int(task['coins'])}})
    user_tasks_history.update_one({"mobile": data.get('mobile'), "task_id": task_id, "date": today}, {"$inc": {"count": 1}}, upsert=True)
    return jsonify({"status": "success"})

@app.route('/api/premium/buy', methods=['POST'])
def api_buy_premium():
    data = request.json
    plan = plans_col.find_one({"_id": ObjectId(data.get('plan_id'))})
    user = users_col.find_one({"mobile": data.get('mobile')})
    if user['balance'] < int(plan['coins']): return jsonify({"status": "error", "message": "কয়েন নেই!"}), 400
    
    expiry = (user['premium_expiry'] if user.get('is_premium') and user['premium_expiry'] > datetime.now() else datetime.now()) + timedelta(days=int(plan['days']))
    users_col.update_one({"mobile": data.get('mobile')}, {"$inc": {"balance": -int(plan['coins'])}, "$set": {"is_premium": True, "premium_expiry": expiry}})
    return jsonify({"status": "success"})

@app.route('/api/episode/check-access', methods=['POST'])
def api_check_access():
    user = users_col.find_one({"mobile": request.json.get('mobile')})
    if user.get('is_premium'): return jsonify({"status": "unlocked"})
    unlock = ep_unlock_col.find_one({"mobile": user['mobile']})
    if unlock and datetime.now() < unlock['expiry']: return jsonify({"status": "unlocked"})
    return jsonify({"status": "locked", "ad_config": ep_ads_col.find_one({"type": "ep_ad_config"})})

@app.route('/api/episode/unlock', methods=['POST'])
def api_unlock_ep():
    config = ep_ads_col.find_one({"type": "ep_ad_config"})
    expiry = datetime.now() + timedelta(minutes=int(config['unlock_minutes']))
    ep_unlock_col.update_one({"mobile": request.json.get('mobile')}, {"$set": {"expiry": expiry}}, upsert=True)
    return jsonify({"status": "success"})

# ==========================================
# ৪. মেগা অ্যাডমিন প্যানেল (সব মেনুসহ)
# ==========================================

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Admin Panel</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>body{background:#0b0f19;color:white;}.glass{background:rgba(30,41,59,0.7);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.1);}</style>
</head>
<body class="flex flex-col md:flex-row min-h-screen">
    <!-- Sidebar -->
    <div class="w-full md:w-64 glass p-6 space-y-6">
        <h1 class="text-xl font-bold text-blue-400 text-center uppercase tracking-widest">Master Admin</h1>
        <nav class="space-y-1 text-sm">
            <a href="/admin" class="flex items-center p-3 hover:bg-white/10 rounded-xl transition"><i class="fas fa-chart-line mr-3"></i> Dashboard</a>
            <a href="#movies" class="flex items-center p-3 hover:bg-white/10 rounded-xl transition"><i class="fas fa-film mr-3"></i> Movie Database</a>
            <a href="#ep_ads" class="flex items-center p-3 hover:bg-red-500/10 rounded-xl transition text-red-400 font-bold"><i class="fas fa-shield-alt mr-3"></i> Episode Ad Lock</a>
            <a href="#tasks" class="flex items-center p-3 hover:bg-green-500/10 rounded-xl transition text-green-400"><i class="fas fa-link mr-3"></i> Direct Tasks</a>
            <a href="#monetag" class="flex items-center p-3 hover:bg-yellow-500/10 rounded-xl transition text-yellow-400"><i class="fas fa-ad mr-3"></i> Monetag Ads</a>
            <a href="#plans" class="flex items-center p-3 hover:bg-purple-500/10 rounded-xl transition text-purple-400 font-bold"><i class="fas fa-crown mr-3"></i> Premium Plans</a>
            <a href="#settings" class="flex items-center p-3 hover:bg-white/10 rounded-xl transition"><i class="fas fa-cog mr-3"></i> Global Settings</a>
        </nav>
    </div>

    <!-- Main Content -->
    <div class="flex-1 p-6 space-y-10 overflow-y-auto">
        
        <!-- Stats -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400">USERS</p><p class="text-2xl font-bold text-blue-400">{{u_count}}</p></div>
            <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400">MOVIES</p><p class="text-2xl font-bold text-green-400">{{m_count}}</p></div>
        </div>

        <!-- 1. Episode Ad Lock Menu -->
        <div id="ep_ads" class="glass p-8 rounded-3xl border-red-500/20 border">
            <h2 class="text-xl font-bold mb-6 text-red-400 border-b border-white/5 pb-2">Episode Button Ad Lock</h2>
            <form action="/admin/update-ep-ads" method="POST" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input type="text" name="direct_link" value="{{ep_c.direct_link}}" placeholder="Direct Ad Link" class="bg-black/30 p-3 rounded-xl border border-white/10">
                    <input type="text" name="monetag_id" value="{{ep_c.monetag_id}}" placeholder="Monetag Zone ID" class="bg-black/30 p-3 rounded-xl border border-white/10">
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <input type="number" name="unlock_minutes" value="{{ep_c.unlock_minutes}}" placeholder="Unlock Minutes" class="bg-black/30 p-3 rounded-xl border border-white/10">
                    <input type="number" name="daily_limit" value="{{ep_c.daily_limit}}" placeholder="Daily Limit" class="bg-black/30 p-3 rounded-xl border border-white/10">
                    <select name="active_type" class="bg-black/30 p-3 rounded-xl border border-white/10">
                        <option value="direct" {% if ep_c.active_type == 'direct' %}selected{% endif %}>Use Direct Link</option>
                        <option value="monetag" {% if ep_c.active_type == 'monetag' %}selected{% endif %}>Use Monetag Script</option>
                        <option value="off" {% if ep_c.active_type == 'off' %}selected{% endif %}>OFF (No Ads)</option>
                    </select>
                </div>
                <div class="flex gap-4">
                    <button class="flex-1 bg-red-600 p-3 rounded-xl font-bold">Update Ad System</button>
                    <a href="/admin/ep-ad/delete" class="bg-gray-800 p-3 rounded-xl font-bold">Delete/Reset</a>
                </div>
            </form>
        </div>

        <!-- 2. Premium Plans Menu -->
        <div id="plans" class="glass p-8 rounded-3xl border-purple-500/20 border">
            <h2 class="text-xl font-bold mb-6 text-purple-400 border-b border-white/5 pb-2">Premium Member Packages</h2>
            <form action="/admin/add-plan" method="POST" class="flex gap-4 mb-6">
                <input type="number" name="days" placeholder="Days" class="bg-black/20 p-3 rounded-xl border border-white/10 w-full" required>
                <input type="number" name="coins" placeholder="Coins Required" class="bg-black/20 p-3 rounded-xl border border-white/10 w-full" required>
                <button class="bg-purple-600 px-10 rounded-xl font-bold">Add New Plan</button>
            </form>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                {% for p in plans %}<div class="flex justify-between bg-white/5 p-4 rounded-xl border border-white/5"><span>{{p.days}} Days - {{p.coins}} Coins</span><a href="/admin/plan/delete/{{p._id}}" class="text-red-500"><i class="fas fa-trash"></i></a></div>{% endfor %}
            </div>
        </div>

        <!-- 3. Direct Tasks Menu -->
        <div id="tasks" class="glass p-8 rounded-3xl border-green-500/20 border">
            <h2 class="text-xl font-bold mb-6 text-green-400 border-b border-white/5 pb-2">Direct Link Tasks</h2>
            <form action="/admin/task/add" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <input type="text" name="link" placeholder="Task Link" class="bg-black/20 p-3 rounded-xl border border-white/10 md:col-span-2" required>
                <input type="number" name="coins" placeholder="Coins" class="bg-black/20 p-3 rounded-xl border border-white/10" required>
                <input type="number" name="limit" placeholder="Limit" class="bg-black/20 p-3 rounded-xl border border-white/10" required>
                <button class="bg-green-600 p-3 rounded-xl font-bold">Add Task</button>
            </form>
            <div class="space-y-2">
                {% for t in d_tasks %}<div class="flex justify-between bg-black/40 p-3 rounded-xl"><span>{{t.link[:50]}}.. ({{t.coins}} Coins)</span><a href="/admin/task/delete/{{t._id}}" class="text-red-500">X</a></div>{% endfor %}
            </div>
        </div>

        <!-- 4. Site Settings Menu -->
        <div id="settings" class="glass p-8 rounded-3xl">
            <h2 class="text-xl font-bold mb-6 text-blue-400">Global Site Config</h2>
            <form action="/admin/update-settings" method="POST" class="space-y-4">
                <input type="text" name="site_name" value="{{config.site_name}}" class="w-full bg-black/20 p-3 rounded-xl border border-white/10">
                <input type="text" name="site_logo" value="{{config.site_logo}}" class="w-full bg-black/20 p-3 rounded-xl border border-white/10">
                <textarea name="header_notice" class="w-full bg-black/20 p-3 rounded-xl border border-white/10 h-24">{{config.header_notice}}</textarea>
                <input type="number" name="movies_per_page" value="{{config.movies_per_page}}" class="w-full bg-black/20 p-3 rounded-xl border border-white/10">
                <button class="w-full bg-blue-600 p-3 rounded-xl font-bold">Update Everything</button>
            </form>
        </div>

        <!-- 5. Movie List Menu -->
        <div id="movies" class="glass p-8 rounded-3xl">
            <h2 class="text-xl font-bold mb-6 text-blue-400">Movie Management</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead><tr class="text-gray-500 uppercase text-xs"><th class="p-4">Title</th><th class="p-4 text-right">Action</th></tr></thead>
                    <tbody>
                        {% for m in movies %}<tr class="border-b border-white/5 hover:bg-white/5">
                            <td class="p-4 font-bold">{{m.title}}</td>
                            <td class="p-4 text-right"><a href="/admin/movie/delete/{{m._id}}" class="text-red-500" onclick="return confirm('Delete?')">Delete</a></td>
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
    return render_template_string(ADMIN_HTML, 
    config=settings_col.find_one({"type":"site_config"}),
    ep_c=ep_ads_col.find_one({"type":"ep_ad_config"}),
    u_count=users_col.count_documents({}),
    m_count=movies_col.count_documents({}),
    movies=list(movies_col.find().sort('_id', -1)),
    plans=list(plans_col.find()),
    d_tasks=list(tasks_col.find()),
    m_tasks=list(monetag_tasks_col.find()))

@app.route('/admin/update-ep-ads', methods=['POST'])
def admin_update_ep():
    ep_ads_col.update_one({"type": "ep_ad_config"}, {"$set": {
        "direct_link": request.form.get('direct_link'), "monetag_id": request.form.get('monetag_id'),
        "unlock_minutes": int(request.form.get('unlock_minutes')), 
        "daily_limit": int(request.form.get('daily_limit')), "active_type": request.form.get('active_type')
    }}, upsert=True)
    return redirect('/admin')

@app.route('/admin/ep-ad/delete')
def admin_del_ep_ad():
    ep_ads_col.update_one({"type": "ep_ad_config"}, {"$set": {"direct_link": "", "monetag_id": "", "active_type": "off"}})
    return redirect('/admin')

@app.route('/admin/add-plan', methods=['POST'])
def admin_add_plan():
    plans_col.insert_one({"days": request.form.get('days'), "coins": request.form.get('coins')})
    return redirect('/admin')

@app.route('/admin/plan/delete/<id>')
def admin_del_plan(id):
    plans_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin')

@app.route('/admin/task/add', methods=['POST'])
def admin_add_task():
    tasks_col.insert_one({"link": request.form.get('link'), "coins": request.form.get('coins'), "daily_limit": request.form.get('limit'), "type": "direct"})
    return redirect('/admin')

@app.route('/admin/task/delete/<id>')
def admin_del_task(id):
    tasks_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin')

@app.route('/admin/update-settings', methods=['POST'])
def admin_update_set():
    settings_col.update_one({"type": "site_config"}, {"$set": {
        "site_name": request.form.get('site_name'), "site_logo": request.form.get('site_logo'),
        "header_notice": request.form.get('header_notice'), "movies_per_page": int(request.form.get('movies_per_page'))
    }})
    return redirect('/admin')

@app.route('/admin/movie/delete/<id>')
def admin_del_movie(id):
    movies_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin')

# ==========================================
# ৫. টেলিগ্রাম বট লজিক (অ্যাডমিন আইডি ফিল্টারসহ)
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
def bot_start(message):
    bot.reply_to(message, f"👋 স্বাগতম!\nআপনার টেলিগ্রাম আইডি: `{message.from_user.id}`\nএটি একাউন্ট সাইনআপ এবং পাসওয়ার্ড রিসেট ওটিপি পেতে লাগবে।")

@bot.message_handler(commands=['movie'])
def bot_add_movie(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ আপনি এই বটের অ্যাডমিন নন!")
    msg = bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন:")
    bot.register_next_step_handler(msg, step_get_title)

def step_get_title(message):
    title = message.text
    msg = bot.send_message(message.chat.id, "📂 মুভির ক্যাটাগরি:")
    bot.register_next_step_handler(msg, lambda m: step_get_cat(m, title))

def step_get_cat(message, title):
    cat = message.text
    msg = bot.send_message(message.chat.id, "🖼 মুভির পোস্টার ইউআরএল দিন:")
    bot.register_next_step_handler(msg, lambda m: step_get_files(m, title, cat))

def step_get_files(message, title, cat):
    poster = message.text
    msg = bot.send_message(message.chat.id, "📥 ভিডিও/ডকুমেন্ট ফাইল পাঠান। সব পাঠানো শেষ হলে /done লিখুন।")
    bot.register_next_step_handler(msg, lambda m: step_collect_eps(m, title, cat, poster, []))

def step_collect_eps(message, title, cat, poster, eps):
    if message.text == "/done":
        movies_col.insert_one({"title": title, "category": cat, "poster": poster, "episodes": eps, "added_at": datetime.now()})
        return bot.send_message(message.chat.id, f"✅ মুভি সফলভাবে যোগ হয়েছে!\n🎬 {title}\n📂 {len(eps)} টি এপিসোড।")
    
    if message.content_type in ['video', 'document']:
        sent = bot.forward_message(FILE_CHANNEL_ID, message.chat.id, message.message_id)
        chan_id = str(FILE_CHANNEL_ID).replace("-100", "")
        ep_name = f"{title} - Episode {len(eps)+1}"
        eps.append({"name": ep_name, "link": f"https://t.me/c/{chan_id}/{sent.message_id}"})
        bot.send_message(message.chat.id, f"📥 {ep_name} যোগ হয়েছে। আরও দিন বা /done লিখুন।")
    
    bot.register_next_step_handler(message, lambda m: step_collect_eps(m, title, cat, poster, eps))

# ==========================================
# ৬. রান ও রুট
# ==========================================

@app.route('/')
def index(): return "Movie API is Running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
