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

# ডিফল্ট সেটিংস ইনিশিয়াল
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

# --- ২. ইউজার অথেনটিকেশন ও প্রোফাইল API ---

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.json
    if users_col.find_one({"mobile": data.get('mobile')}):
        return jsonify({"status": "error", "message": "এই নাম্বারটি ইতিমধ্যে নিবন্ধিত!"}), 400
    users_col.insert_one({
        "first_name": data.get('first_name'), "last_name": data.get('last_name'),
        "mobile": data.get('mobile'), "telegram_id": data.get('telegram_id'),
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
        if user.get('is_premium') and user.get('premium_expiry') and datetime.now() > user['premium_expiry']:
            users_col.update_one({"mobile": user['mobile']}, {"$set": {"is_premium": False}})
            user['is_premium'] = False
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "error", "message": "নাম্বার বা পাসওয়ার্ড ভুল!"}), 401

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
    if not user: return jsonify({"status": "error", "message": "তথ্য মেলেনি!"}), 404
    otp = ''.join(random.choices(string.digits, k=6))
    otp_col.update_one({"mobile": user['mobile']}, {"$set": {"otp": otp}}, upsert=True)
    try:
        bot.send_message(user['telegram_id'], f"🔐 পাসওয়ার্ড রিসেট কোড: {otp}")
        return jsonify({"status": "success", "message": "টেলিগ্রামে ওটিপি পাঠানো হয়েছে!"})
    except: return jsonify({"status": "error", "message": "বট স্টার্ট করুন!"}), 500

# --- ৩. টাস্ক, প্রিমিয়াম ও এপিসোড লক API ---

@app.route('/api/tasks/complete', methods=['POST'])
def complete_task():
    data = request.json
    task_type = data.get('type') # 'direct' or 'monetag'
    col = monetag_tasks_col if task_type == 'monetag' else tasks_col
    task = col.find_one({"_id": ObjectId(data.get('task_id'))})
    today = datetime.now().strftime("%Y-%m-%d")
    
    history = user_tasks_history.find_one({"mobile": data.get('mobile'), "task_id": data.get('task_id'), "date": today})
    if history and history['count'] >= int(task['daily_limit']):
        return jsonify({"status": "error", "message": "লিমিট শেষ!"}), 400
    
    users_col.update_one({"mobile": data.get('mobile')}, {"$inc": {"balance": int(task['coins'])}})
    user_tasks_history.update_one({"mobile": data.get('mobile'), "task_id": data.get('task_id'), "date": today}, {"$inc": {"count": 1}}, upsert=True)
    return jsonify({"status": "success", "message": "কয়েন যোগ হয়েছে!"})

@app.route('/api/premium/buy', methods=['POST'])
def buy_premium():
    data = request.json
    plan = plans_col.find_one({"_id": ObjectId(data.get('plan_id'))})
    user = users_col.find_one({"mobile": data.get('mobile')})
    if user['balance'] < int(plan['coins']): return jsonify({"status": "error", "message": "কয়েন নেই!"}), 400
    expiry = (user['premium_expiry'] if user.get('is_premium') and user['premium_expiry'] > datetime.now() else datetime.now()) + timedelta(days=int(plan['days']))
    users_col.update_one({"mobile": data.get('mobile')}, {"$inc": {"balance": -int(plan['coins'])}, "$set": {"is_premium": True, "premium_expiry": expiry}})
    return jsonify({"status": "success", "message": "প্রিমিয়াম এক্টিভ হয়েছে!"})

@app.route('/api/episode/check-access', methods=['POST'])
def check_ep_access():
    user = users_col.find_one({"mobile": request.json.get('mobile')})
    if user.get('is_premium'): return jsonify({"status": "unlocked"})
    unlock = ep_unlock_col.find_one({"mobile": user['mobile']})
    if unlock and datetime.now() < unlock['expiry']: return jsonify({"status": "unlocked"})
    return jsonify({"status": "locked", "ad_config": ep_ads_col.find_one({"type": "ep_ad_config"})})

@app.route('/api/episode/unlock', methods=['POST'])
def unlock_ep():
    config = ep_ads_col.find_one({"type": "ep_ad_config"})
    expiry = datetime.now() + timedelta(minutes=int(config['unlock_minutes']))
    ep_unlock_col.update_one({"mobile": request.json.get('mobile')}, {"$set": {"expiry": expiry}}, upsert=True)
    return jsonify({"status": "success"})

# --- ৪. এডমিন প্যানেল UI (সকল ফিচারের আলাদা মেনু) ---

ADMIN_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Admin</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>body{background:#0b0f19;color:white;font-family:sans-serif;}.glass{background:rgba(30,41,59,0.7);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.1);}</style>
</head>
<body class="flex flex-col md:flex-row min-h-screen">
    <div class="w-full md:w-64 glass p-6 space-y-6">
        <h1 class="text-xl font-bold text-blue-400 text-center">MASTER ADMIN</h1>
        <nav class="space-y-1 text-sm">
            <a href="/admin" class="flex items-center p-3 hover:bg-blue-500/10 rounded-xl"><i class="fas fa-home mr-3"></i> Dashboard</a>
            <a href="#movies" class="flex items-center p-3 hover:bg-blue-500/10 rounded-xl"><i class="fas fa-film mr-3"></i> Movies</a>
            <a href="#ep_ads" class="flex items-center p-3 hover:bg-red-500/10 rounded-xl text-red-400 font-bold"><i class="fas fa-lock mr-3"></i> Episode Ad Lock</a>
            <a href="#tasks" class="flex items-center p-3 hover:bg-green-500/10 rounded-xl text-green-400"><i class="fas fa-link mr-3"></i> Direct Tasks</a>
            <a href="#monetag" class="flex items-center p-3 hover:bg-yellow-500/10 rounded-xl text-yellow-400"><i class="fas fa-ad mr-3"></i> Monetag Ads</a>
            <a href="#plans" class="flex items-center p-3 hover:bg-purple-500/10 rounded-xl text-purple-400"><i class="fas fa-crown mr-3"></i> Premium Plans</a>
            <a href="#settings" class="flex items-center p-3 hover:bg-gray-500/10 rounded-xl"><i class="fas fa-cog mr-3"></i> Settings</a>
        </nav>
    </div>
    <div class="flex-1 p-6 space-y-8 overflow-y-auto">
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400">USERS</p><p class="text-2xl font-bold">{{u_count}}</p></div>
            <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400">MOVIES</p><p class="text-2xl font-bold">{{m_count}}</p></div>
        </div>

        <div id="ep_ads" class="glass p-6 rounded-3xl border-red-500/30 border">
            <h2 class="text-lg font-bold mb-4 text-red-400">Episode Ad Lock Config</h2>
            <form action="/admin/update-ep-ads" method="POST" class="space-y-4">
                <input type="text" name="direct_link" value="{{ep_c.direct_link}}" placeholder="Direct Ad Link" class="w-full bg-black/30 p-3 rounded-xl border border-white/10">
                <input type="text" name="monetag_id" value="{{ep_c.monetag_id}}" placeholder="Monetag Zone ID" class="w-full bg-black/30 p-3 rounded-xl border border-white/10">
                <div class="flex gap-4">
                    <input type="number" name="unlock_minutes" value="{{ep_c.unlock_minutes}}" placeholder="Minutes" class="w-1/2 bg-black/30 p-3 rounded-xl border border-white/10">
                    <select name="active_type" class="w-1/2 bg-black/30 p-3 rounded-xl border border-white/10">
                        <option value="direct" {% if ep_c.active_type == 'direct' %}selected{% endif %}>Direct Link</option>
                        <option value="monetag" {% if ep_c.active_type == 'monetag' %}selected{% endif %}>Monetag Script</option>
                        <option value="off" {% if ep_c.active_type == 'off' %}selected{% endif %}>Off</option>
                    </select>
                </div>
                <button class="w-full bg-red-600 p-3 rounded-xl font-bold">Update System</button>
            </form>
        </div>

        <div id="plans" class="glass p-6 rounded-3xl">
            <h2 class="text-lg font-bold mb-4 text-purple-400">Premium Plans</h2>
            <form action="/admin/add-plan" method="POST" class="flex gap-2 mb-4">
                <input type="number" name="days" placeholder="Days" class="w-full bg-black/20 p-3 rounded-xl border border-white/10" required>
                <input type="number" name="coins" placeholder="Coins" class="w-full bg-black/20 p-3 rounded-xl border border-white/10" required>
                <button class="bg-purple-600 px-6 rounded-xl font-bold">Add</button>
            </form>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
                {% for p in plans %}<div class="flex justify-between bg-white/5 p-2 rounded-lg text-xs"><span>{{p.days}}D-{{p.coins}}C</span><a href="/admin/plan/delete/{{p._id}}" class="text-red-500">X</a></div>{% endfor %}
            </div>
        </div>

        <div id="settings" class="glass p-6 rounded-3xl">
            <h2 class="text-lg font-bold mb-4">Settings</h2>
            <form action="/admin/update-settings" method="POST" class="space-y-4">
                <input type="text" name="site_name" value="{{config.site_name}}" class="w-full bg-black/20 p-3 rounded-xl border border-white/10">
                <textarea name="header_notice" class="w-full bg-black/20 p-3 rounded-xl border border-white/10 h-20">{{config.header_notice}}</textarea>
                <button class="w-full bg-blue-600 p-3 rounded-xl font-bold">Save All</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_UI, config=settings_col.find_one({"type":"site_config"}), 
    ep_c=ep_ads_col.find_one({"type":"ep_ad_config"}), u_count=users_col.count_documents({}),
    m_count=movies_col.count_documents({}), plans=list(plans_col.find()))

@app.route('/admin/update-ep-ads', methods=['POST'])
def update_ep_ads():
    ep_ads_col.update_one({"type": "ep_ad_config"}, {"$set": request.form.to_dict()}, upsert=True)
    return redirect('/admin')

@app.route('/admin/add-plan', methods=['POST'])
def add_plan():
    plans_col.insert_one({"days": request.form.get('days'), "coins": request.form.get('coins')})
    return redirect('/admin')

@app.route('/admin/plan/delete/<id>')
def del_plan(id):
    plans_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin')

@app.route('/admin/update-settings', methods=['POST'])
def update_set():
    settings_col.update_one({"type": "site_config"}, {"$set": request.form.to_dict()}); return redirect('/admin')

# --- ৫. টেলিগ্রাম বট ও মুভি এডিং লজিক ---

@bot.message_handler(commands=['start'])
def bot_start(message):
    bot.reply_to(message, f"👋 স্বাগতম!\nআপনার টেলিগ্রাম আইডি: `{message.chat.id}`\nএটি পাসওয়ার্ড রিসেটে লাগবে।")

@bot.message_handler(commands=['movie'])
def bot_movie(message):
    user_states[message.chat.id] = {"episodes": []}
    bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন:")
    bot.register_next_step_handler(message, bot_get_title)

def bot_get_title(message):
    user_states[message.chat.id]['title'] = message.text
    bot.send_message(message.chat.id, "📂 ক্যাটাগরি:")
    bot.register_next_step_handler(message, bot_get_cat)

def bot_get_cat(message):
    user_states[message.chat.id]['category'] = message.text
    bot.send_message(message.chat.id, "🖼 পোস্টার লিংক দিন:")
    bot.register_next_step_handler(message, bot_get_files)

def bot_get_files(message):
    chat_id = message.chat.id
    if message.text == "/done":
        movies_col.insert_one(user_states[chat_id])
        bot.send_message(chat_id, "✅ মুভি অ্যাড হয়েছে!")
        del user_states[chat_id]; return
    if message.content_type in ['video', 'document']:
        sent = bot.forward_message(FILE_CHANNEL_ID, chat_id, message.message_id)
        chan_id = str(FILE_CHANNEL_ID).replace("-100", "")
        ep_name = f"{user_states[chat_id]['title']} - Episode {len(user_states[chat_id]['episodes'])+1}"
        user_states[chat_id]['episodes'].append({"name": ep_name, "link": f"https://t.me/c/{chan_id}/{sent.message_id}"})
        bot.send_message(chat_id, f"📥 যোগ হয়েছে: {ep_name}")
    bot.register_next_step_handler(message, bot_get_files)

# --- ৬. রান অ্যাপ্লিকেশন ---

if __name__ == "__main__":
    t = Thread(target=lambda: app.run(host="0.0.0.0", port=8080))
    t.start()
    bot.infinity_polling()
