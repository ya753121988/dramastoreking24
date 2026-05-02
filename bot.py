import os
import telebot
import random
import string
from pymongo import MongoClient
from flask import Flask, jsonify, request, render_template_string, redirect
from flask_cors import CORS
from bson.objectid import ObjectId
from datetime import datetime, timedelta

# --- ১. কনফিগারেশন ---
BOT_TOKEN = "8655043839:AAGMxkYoZXR-nUzlcapZZfVwci09Z6x0-UE"
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0"
FILE_CHANNEL_ID = -1003985353441 
ADMIN_IDS = [7120801813]

# ডাটাবেস কানেকশন
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

# ডিফল্ট কনফিগারেশন
def init_db():
    if not settings_col.find_one({"type": "site_config"}):
        settings_col.insert_one({"type": "site_config", "site_name": "Premium Movies", "site_logo": "", "header_notice": "স্বাগতম!", "movies_per_page": 12})
    if not ep_ads_col.find_one({"type": "ep_ad_config"}):
        ep_ads_col.insert_one({"type": "ep_ad_config", "direct_link": "", "monetag_id": "", "unlock_minutes": 30, "active_type": "off"})

init_db()

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------
# ২. বট ওয়েব হুক (Vercel এর জন্য জরুরি)
# ---------------------------------------------------------

@app.route('/api/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Forbidden', 403

@bot.message_handler(commands=['start'])
def bot_start(message):
    bot.reply_to(message, f"👋 স্বাগতম!\nআপনার টেলিগ্রাম আইডি: `{message.chat.id}`\nএটি পাসওয়ার্ড রিসেট করতে লাগবে।")

@bot.message_handler(commands=['movie'])
def bot_movie(message):
    if message.chat.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ আপনি এডমিন নন।")
    msg = bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন:")
    bot.register_next_step_handler(msg, get_title)

def get_title(message):
    title = message.text
    msg = bot.send_message(message.chat.id, "📂 ক্যাটাগরি লিখুন:")
    bot.register_next_step_handler(msg, lambda m: get_cat(m, title))

def get_cat(message, title):
    cat = message.text
    msg = bot.send_message(message.chat.id, "🖼 পোস্টার লিংক দিন:")
    bot.register_next_step_handler(msg, lambda m: get_poster(m, title, cat))

def get_poster(message, title, cat):
    poster = message.text
    msg = bot.send_message(message.chat.id, "📥 ফাইল পাঠান (ভিডিও/ডকুমেন্ট)। শেষ হলে /done লিখুন।")
    episodes = []
    bot.register_next_step_handler(msg, lambda m: collect_files(m, title, cat, poster, episodes))

def collect_files(message, title, cat, poster, episodes):
    if message.text == "/done":
        movies_col.insert_one({"title": title, "category": cat, "poster": poster, "episodes": episodes})
        return bot.send_message(message.chat.id, "✅ মুভি সফলভাবে যোগ হয়েছে!")
    
    if message.content_type in ['video', 'document']:
        sent = bot.forward_message(FILE_CHANNEL_ID, message.chat.id, message.message_id)
        chan_id = str(FILE_CHANNEL_ID).replace("-100", "")
        ep_name = f"{title} - Episode {len(episodes)+1}"
        episodes.append({"name": ep_name, "link": f"https://t.me/c/{chan_id}/{sent.message_id}"})
        bot.send_message(message.chat.id, f"📥 {ep_name} যোগ হয়েছে। আরও দিন বা /done লিখুন।")
    
    bot.register_next_step_handler(message, lambda m: collect_files(m, title, cat, poster, episodes))

# ---------------------------------------------------------
# ৩. ইউজার ও অথেনটিকেশন API
# ---------------------------------------------------------

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    if users_col.find_one({"mobile": data.get('mobile')}): return jsonify({"status": "error"}), 400
    users_col.insert_one({"first_name": data.get('first_name'), "last_name": data.get('last_name'), "mobile": data.get('mobile'), "telegram_id": int(data.get('telegram_id')), "password": data.get('password'), "balance": 0, "is_premium": False})
    return jsonify({"status": "success"})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    user = users_col.find_one({"mobile": data.get('mobile'), "password": data.get('password')})
    if user:
        user['_id'] = str(user['_id'])
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "error"}), 401

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot():
    data = request.json
    user = users_col.find_one({"mobile": data.get('mobile'), "telegram_id": int(data.get('telegram_id'))})
    if not user: return jsonify({"status": "error"}), 404
    otp = ''.join(random.choices(string.digits, k=6))
    otp_col.update_one({"mobile": user['mobile']}, {"$set": {"otp": otp}}, upsert=True)
    bot.send_message(user['telegram_id'], f"🔐 ওটিপি কোড: {otp}")
    return jsonify({"status": "success"})

# ---------------------------------------------------------
# ৪. মুভি, টাস্ক ও প্রিমিয়াম API
# ---------------------------------------------------------

@app.route('/api/movies', methods=['GET'])
def get_movies():
    movies = list(movies_col.find().sort('_id', -1))
    for m in movies: m['_id'] = str(m['_id'])
    return jsonify(movies)

@app.route('/api/episode/check-access', methods=['POST'])
def check_access():
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

# ---------------------------------------------------------
# ৫. অ্যাডমিন প্যানেল UI
# ---------------------------------------------------------

ADMIN_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin</title><script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>body{background:#0b0f19;color:white;}.glass{background:rgba(30,41,59,0.7);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.1);}</style>
</head>
<body class="flex flex-col md:flex-row min-h-screen">
    <div class="w-full md:w-64 glass p-6 space-y-4">
        <h1 class="text-xl font-bold text-blue-400">ADMIN</h1>
        <nav class="space-y-2">
            <a href="/admin" class="block p-3 hover:bg-white/10 rounded-xl">Dashboard</a>
            <a href="#ep_ads" class="block p-3 text-red-400 font-bold">Episode Ad Lock</a>
            <a href="#tasks" class="block p-3 text-green-400">Tasks</a>
            <a href="#plans" class="block p-3 text-purple-400">Premium Plans</a>
            <a href="#settings" class="block p-3">Settings</a>
        </nav>
    </div>
    <div class="flex-1 p-6 space-y-8 overflow-y-auto">
        <div id="ep_ads" class="glass p-6 rounded-3xl border-red-500/30 border">
            <h2 class="text-lg font-bold mb-4 text-red-400">Episode Ad System</h2>
            <form action="/admin/update-ep-ads" method="POST" class="space-y-4">
                <input type="text" name="direct_link" value="{{ep_c.direct_link}}" placeholder="Direct Link" class="w-full bg-black/30 p-3 rounded-xl">
                <input type="text" name="monetag_id" value="{{ep_c.monetag_id}}" placeholder="Monetag ID" class="w-full bg-black/30 p-3 rounded-xl">
                <input type="number" name="unlock_minutes" value="{{ep_c.unlock_minutes}}" class="w-full bg-black/30 p-3 rounded-xl">
                <select name="active_type" class="w-full bg-black/30 p-3 rounded-xl">
                    <option value="direct" {% if ep_c.active_type == 'direct' %}selected{% endif %}>Direct Link</option>
                    <option value="monetag" {% if ep_c.active_type == 'monetag' %}selected{% endif %}>Monetag</option>
                    <option value="off" {% if ep_c.active_type == 'off' %}selected{% endif %}>OFF</option>
                </select>
                <button class="w-full bg-red-600 p-3 rounded-xl font-bold">Update</button>
            </form>
        </div>
        <div id="settings" class="glass p-6 rounded-3xl">
            <form action="/admin/update-settings" method="POST" class="space-y-4">
                <input type="text" name="site_name" value="{{config.site_name}}" class="w-full bg-black/30 p-3 rounded-xl">
                <textarea name="header_notice" class="w-full bg-black/30 p-3 rounded-xl">{{config.header_notice}}</textarea>
                <button class="w-full bg-blue-600 p-3 rounded-xl font-bold">Save All</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

@app.route('/admin')
def admin():
    return render_template_string(ADMIN_UI, config=settings_col.find_one({"type":"site_config"}), ep_c=ep_ads_col.find_one({"type":"ep_ad_config"}))

@app.route('/admin/update-ep-ads', methods=['POST'])
def update_ep():
    ep_ads_col.update_one({"type": "ep_ad_config"}, {"$set": request.form.to_dict()}, upsert=True)
    return redirect('/admin')

@app.route('/admin/update-settings', methods=['POST'])
def update_set():
    settings_col.update_one({"type": "site_config"}, {"$set": request.form.to_dict()}, upsert=True)
    return redirect('/admin')

@app.route('/')
def home(): return "API is running..."

# Vercel-এর জন্য এক্সপোর্ট
if __name__ == "__main__":
    app.run()
