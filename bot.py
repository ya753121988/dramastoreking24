import os
import telebot
import random
import string
from pymongo import MongoClient
from flask import Flask, jsonify, request, render_template_string, redirect
from flask_cors import CORS
from bson.objectid import ObjectId
from datetime import datetime, timedelta

# --- ১. কনফিগারেশন ও ডাটাবেস (আপনার দেওয়া তথ্য অনুযায়ী) ---
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

# ডিফল্ট সেটিংস চেক (ডাটাবেস খালি থাকলে এগুলো সেট হবে)
def init_database():
    if not settings_col.find_one({"type": "site_config"}):
        settings_col.insert_one({
            "type": "site_config", "site_name": "Premium Movies", 
            "site_logo": "https://via.placeholder.com/200x60",
            "header_notice": "আমাদের সাইটে স্বাগতম! একাউন্ট খুলে মুভি দেখুন। 🍿",
            "movies_per_page": 12
        })
    if not ep_ads_col.find_one({"type": "ep_ad_config"}):
        ep_ads_col.insert_one({
            "type": "ep_ad_config", "direct_link": "", "monetag_id": "",
            "unlock_minutes": 30, "active_type": "off"
        })

init_database()

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------
# ২. ইউজার অথেনটিকেশন ও প্রোফাইল API (লাইন বাই লাইন লজিক)
# ---------------------------------------------------------

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.json
    if users_col.find_one({"mobile": data.get('mobile')}):
        return jsonify({"status": "error", "message": "এই মোবাইল নাম্বারটি ইতিমধ্যে নিবন্ধিত!"}), 400
    
    users_col.insert_one({
        "first_name": data.get('first_name'),
        "last_name": data.get('last_name'),
        "mobile": data.get('mobile'),
        "telegram_id": int(data.get('telegram_id')),
        "password": data.get('password'),
        "balance": 0,
        "is_premium": False,
        "premium_expiry": None,
        "joined_at": datetime.now()
    })
    return jsonify({"status": "success", "message": "নিবন্ধন সফল!"})

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
    return jsonify({"status": "error", "message": "নাম্বার অথবা পাসওয়ার্ড ভুল!"}), 401

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    user = users_col.find_one({"mobile": data.get('mobile'), "telegram_id": int(data.get('telegram_id'))})
    if not user: return jsonify({"status": "error", "message": "তথ্য সঠিক নয়!"}), 404
    
    otp = ''.join(random.choices(string.digits, k=6))
    otp_col.update_one({"mobile": user['mobile']}, {"$set": {"otp": otp}}, upsert=True)
    try:
        bot.send_message(user['telegram_id'], f"🔐 আপনার ওটিপি কোড: {otp}")
        return jsonify({"status": "success"})
    except:
        return jsonify({"status": "error", "message": "বট স্টার্ট করুন!"}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    res = otp_col.find_one({"mobile": data.get('mobile'), "otp": data.get('otp')})
    if res:
        users_col.update_one({"mobile": data.get('mobile')}, {"$set": {"password": data.get('password')}})
        otp_col.delete_one({"mobile": data.get('mobile')})
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "ভুল ওটিপি!"}), 400

# ---------------------------------------------------------
# ৩. টাস্ক, প্রিমিয়াম ও এপিসোড অ্যাড সিস্টেম API
# ---------------------------------------------------------

@app.route('/api/tasks/all', methods=['GET'])
def get_all_tasks():
    d_tasks = list(tasks_col.find())
    m_tasks = list(monetag_tasks_col.find())
    for t in d_tasks + m_tasks: t['_id'] = str(t['_id'])
    return jsonify({"direct": d_tasks, "monetag": m_tasks})

@app.route('/api/tasks/complete', methods=['POST'])
def complete_task():
    data = request.json
    col = monetag_tasks_col if data.get('type') == 'monetag' else tasks_col
    task = col.find_one({"_id": ObjectId(data.get('task_id'))})
    today = datetime.now().strftime("%Y-%m-%d")
    
    history = user_tasks_history.find_one({"mobile": data.get('mobile'), "task_id": data.get('task_id'), "date": today})
    if history and history['count'] >= int(task['daily_limit']):
        return jsonify({"status": "limit_reached"}), 400
    
    users_col.update_one({"mobile": data.get('mobile')}, {"$inc": {"balance": int(task['coins'])}})
    user_tasks_history.update_one({"mobile": data.get('mobile'), "task_id": data.get('task_id'), "date": today}, {"$inc": {"count": 1}}, upsert=True)
    return jsonify({"status": "success"})

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
# ৪. প্রিমিয়াম অ্যাডমিন ড্যাশবোর্ড UI (সম্পূর্ণ প্রফেশনাল)
# ---------------------------------------------------------

ADMIN_UI = """
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
    <div class="w-full md:w-64 glass p-6 space-y-6">
        <h1 class="text-xl font-bold text-blue-400 text-center">MOVIE ADMIN</h1>
        <nav class="space-y-1 text-sm">
            <a href="/admin" class="flex items-center p-3 hover:bg-white/10 rounded-xl transition"><i class="fas fa-home mr-3"></i> Dashboard</a>
            <a href="#movies" class="flex items-center p-3 hover:bg-white/10 rounded-xl transition"><i class="fas fa-film mr-3"></i> Movies</a>
            <a href="#ep_ads" class="flex items-center p-3 hover:bg-red-500/20 rounded-xl transition text-red-400 font-bold"><i class="fas fa-lock mr-3"></i> Episode Ad Lock</a>
            <a href="#tasks" class="flex items-center p-3 hover:bg-green-500/20 rounded-xl transition text-green-400"><i class="fas fa-link mr-3"></i> Direct Tasks</a>
            <a href="#monetag" class="flex items-center p-3 hover:bg-yellow-500/20 rounded-xl transition text-yellow-400"><i class="fas fa-ad mr-3"></i> Monetag Ads</a>
            <a href="#plans" class="flex items-center p-3 hover:bg-purple-500/20 rounded-xl transition text-purple-400"><i class="fas fa-crown mr-3"></i> Premium Plans</a>
            <a href="#settings" class="flex items-center p-3 hover:bg-white/10 rounded-xl transition"><i class="fas fa-cog mr-3"></i> Settings</a>
        </nav>
    </div>

    <div class="flex-1 p-6 space-y-8 overflow-y-auto">
        <!-- Episode Ad System -->
        <div id="ep_ads" class="glass p-6 rounded-3xl border-red-500/30 border">
            <h2 class="text-xl font-bold mb-6 text-red-400"><i class="fas fa-shield-alt mr-2"></i>Episode Button Ad Management</h2>
            <form action="/admin/update-ep-ads" method="POST" class="space-y-4">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <input type="text" name="direct_link" value="{{ep_c.direct_link}}" placeholder="Ad Direct Link" class="bg-black/30 p-3 rounded-xl border border-white/10">
                    <input type="text" name="monetag_id" value="{{ep_c.monetag_id}}" placeholder="Monetag Zone ID (e.g. 10351894)" class="bg-black/30 p-3 rounded-xl border border-white/10">
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <input type="number" name="unlock_minutes" value="{{ep_c.unlock_minutes}}" placeholder="Minutes to Unlock" class="bg-black/30 p-3 rounded-xl border border-white/10">
                    <select name="active_type" class="bg-black/30 p-3 rounded-xl border border-white/10">
                        <option value="direct" {% if ep_c.active_type == 'direct' %}selected{% endif %}>Use Direct Link</option>
                        <option value="monetag" {% if ep_c.active_type == 'monetag' %}selected{% endif %}>Use Monetag Script</option>
                        <option value="off" {% if ep_c.active_type == 'off' %}selected{% endif %}>OFF (No Ads)</option>
                    </select>
                </div>
                <button class="w-full bg-red-600 p-3 rounded-xl font-bold hover:bg-red-700 transition">Update Episode Ad Lock</button>
            </form>
        </div>

        <!-- Premium Plans -->
        <div id="plans" class="glass p-6 rounded-3xl">
            <h2 class="text-xl font-bold mb-4 text-purple-400">👑 Premium Membership Plans</h2>
            <form action="/admin/add-plan" method="POST" class="flex gap-4 mb-6">
                <input type="number" name="days" placeholder="Days" class="bg-black/20 p-3 rounded-xl border border-white/10 w-full" required>
                <input type="number" name="coins" placeholder="Coins Required" class="bg-black/20 p-3 rounded-xl border border-white/10 w-full" required>
                <button class="bg-purple-600 px-10 rounded-xl font-bold">Add Plan</button>
            </form>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                {% for p in plans %}<div class="flex justify-between bg-white/5 p-4 rounded-xl border border-white/5"><span>{{p.days}} Days - {{p.coins}} Coins</span><a href="/admin/plan/delete/{{p._id}}" class="text-red-500"><i class="fas fa-trash"></i></a></div>{% endfor %}
            </div>
        </div>

        <!-- Site Settings -->
        <div id="settings" class="glass p-6 rounded-3xl">
            <h2 class="text-xl font-bold mb-4 text-blue-400">⚙️ General Configuration</h2>
            <form action="/admin/update-settings" method="POST" class="space-y-4">
                <input type="text" name="site_name" value="{{config.site_name}}" class="w-full bg-black/20 p-3 rounded-xl border border-white/10">
                <textarea name="header_notice" class="w-full bg-black/20 p-3 rounded-xl border border-white/10 h-24">{{config.header_notice}}</textarea>
                <button class="w-full bg-blue-600 p-3 rounded-xl font-bold transition">Save Settings</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_UI, config=settings_col.find_one({"type":"site_config"}), 
    ep_c=ep_ads_col.find_one({"type":"ep_ad_config"}), plans=list(plans_col.find()),
    u_count=users_col.count_documents({}), m_count=movies_col.count_documents({}))

@app.route('/admin/update-ep-ads', methods=['POST'])
def update_ep_ads():
    ep_ads_col.update_one({"type": "ep_ad_config"}, {"$set": {
        "direct_link": request.form.get('direct_link'), "monetag_id": request.form.get('monetag_id'),
        "unlock_minutes": int(request.form.get('unlock_minutes')), "active_type": request.form.get('active_type')
    }}, upsert=True)
    return redirect('/admin')

@app.route('/admin/add-plan', methods=['POST'])
def add_premium_plan():
    plans_col.insert_one({"days": request.form.get('days'), "coins": request.form.get('coins')})
    return redirect('/admin')

@app.route('/admin/plan/delete/<id>')
def delete_plan(id):
    plans_col.delete_one({"_id": ObjectId(id)}); return redirect('/admin')

@app.route('/admin/update-settings', methods=['POST'])
def update_p_settings():
    settings_col.update_one({"type": "site_config"}, {"$set": {"site_name": request.form.get('site_name'), "header_notice": request.form.get('header_notice')}})
    return redirect('/admin')

# ---------------------------------------------------------
# ৫. টেলিগ্রাম বট লজিক (এডমিন মুভি এডিং ও ওটিপি)
# ---------------------------------------------------------

@bot.message_handler(commands=['start'])
def bot_start(message):
    bot.reply_to(message, f"👋 স্বাগতম!\nআপনার টেলিগ্রাম আইডি: `{message.chat.id}`\nএটি একাউন্ট ভেরিফিকেশন ও পাসওয়ার্ড রিসেটে লাগবে।")

@bot.message_handler(commands=['movie'])
def bot_movie_add(message):
    if message.chat.id not in ADMIN_IDS: return bot.reply_to(message, "❌ আপনি এডমিন নন।")
    msg = bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন:")
    bot.register_next_step_handler(msg, bot_step_title)

def bot_step_title(message):
    title = message.text
    msg = bot.send_message(message.chat.id, "📂 মুভির ক্যাটাগরি:")
    bot.register_next_step_handler(msg, lambda m: bot_step_cat(m, title))

def bot_step_cat(message, title):
    cat = message.text
    msg = bot.send_message(message.chat.id, "🖼 মুভির পোস্টার ইউআরএল দিন:")
    bot.register_next_step_handler(msg, lambda m: bot_step_files(m, title, cat))

def bot_step_files(message, title, cat):
    poster = message.text
    msg = bot.send_message(message.chat.id, "📥 ফাইল/এপিসোডগুলো পাঠান। শেষ হলে /done লিখুন।")
    eps = []
    bot.register_next_step_handler(msg, lambda m: bot_collect_eps(m, title, cat, poster, eps))

def bot_collect_eps(message, title, cat, poster, eps):
    if message.text == "/done":
        movies_col.insert_one({"title": title, "category": cat, "poster": poster, "episodes": eps})
        return bot.send_message(message.chat.id, "✅ মুভিটি সফলভাবে ডাটাবেসে যোগ হয়েছে!")
    
    if message.content_type in ['video', 'document']:
        sent = bot.forward_message(FILE_CHANNEL_ID, message.chat.id, message.message_id)
        ep_name = f"{title} - Episode {len(eps)+1}"
        eps.append({"name": ep_name, "link": f"https://t.me/c/{str(FILE_CHANNEL_ID).replace('-100', '')}/{sent.message_id}"})
        bot.send_message(message.chat.id, f"📥 {ep_name} যোগ হয়েছে। আরও দিন বা /done লিখুন।")
    
    bot.register_next_step_handler(message, lambda m: bot_collect_eps(m, title, cat, poster, eps))

# ---------------------------------------------------------
# ৬. ভার্সেল ওয়েব হুক ও রান
# ---------------------------------------------------------

@app.route('/api/webhook', methods=['POST'])
def webhook_handle():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return ''
    return 'Forbidden', 403

@app.route('/')
def api_home(): return "Server is Alive! Use /admin or API endpoints."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
