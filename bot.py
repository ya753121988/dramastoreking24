import os
import telebot
import random
import string
from pymongo import MongoClient
from flask import Flask, jsonify, request, render_template_string, redirect, make_response
from flask_cors import CORS
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from threading import Thread

# ==========================================
# ১. কনফিগারেশন ও ডাটাবেস (বিন্দু পরিমাণ ভুল নেই)
# ==========================================
BOT_TOKEN = "8655043839:AAGMxkYoZXR-nUzlcapZZfVwci09Z6x0-UE"
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0"
FILE_CHANNEL_ID = -1003985353441 
ADMIN_IDS = [7120801813]
ADMIN_PASS = "admin7120" # অ্যাডমিন প্যানেলে ঢোকার পাসওয়ার্ড

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

# ডিফল্ট সেটিংস অটো জেনারেট
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

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)
CORS(app)

# ==========================================
# ২. ইউজার প্যানেল ও ওয়েবসাইট ডিজাইন (Responsive UI)
# ==========================================

USER_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config.site_name }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: #0b0f19; color: white; font-family: 'Inter', sans-serif; overflow-x: hidden; }
        .glass { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); }
        .movie-card:hover img { transform: scale(1.05); }
        .loading-screen { position: fixed; inset: 0; background: #0b0f19; z-index: 100; display: flex; align-items: center; justify-content: center; transition: opacity 0.5s; }
        ::-webkit-scrollbar { width: 5px; } ::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 10px; }
    </style>
</head>
<body class="pb-20">
    <div id="loader" class="loading-screen"><div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div></div>

    <!-- Header -->
    <header class="glass sticky top-0 z-50 p-4 shadow-2xl">
        <div class="container mx-auto flex justify-between items-center">
            <img src="{{ config.site_logo }}" class="h-8 md:h-10 object-contain">
            <div class="text-right">
                <h1 class="text-sm md:text-lg font-bold text-blue-400">{{ config.site_name }}</h1>
                <p class="text-[10px] text-gray-400">Premium Streaming</p>
            </div>
        </div>
    </header>

    <!-- Scrolling Notice -->
    <div class="bg-blue-600/20 py-2 border-y border-blue-500/20 overflow-hidden">
        <p class="whitespace-nowrap animate-marquee text-xs md:text-sm font-medium">
            <span class="mx-4 text-yellow-400">📢 {{ config.header_notice }}</span>
        </p>
    </div>
    <style>@keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } } .animate-marquee { display: inline-block; animation: marquee 20s linear infinite; }</style>

    <main class="container mx-auto px-4 py-6 min-h-screen">
        {% if page == 'home' %}
            <!-- Movie Grid -->
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 md:gap-6">
                {% for m in movies %}
                <a href="/movie/{{ m._id }}" class="movie-card group glass rounded-2xl overflow-hidden block">
                    <div class="relative overflow-hidden aspect-[2/3]">
                        <img src="{{ m.poster }}" class="w-full h-full object-cover transition duration-500">
                        <div class="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-80"></div>
                        <div class="absolute bottom-2 left-2 right-2">
                            <h3 class="text-[10px] md:text-xs font-bold truncate">{{ m.title }}</h3>
                            <p class="text-[8px] text-blue-400">{{ m.category }}</p>
                        </div>
                    </div>
                </a>
                {% endfor %}
            </div>

            <!-- Pagination -->
            <div class="mt-10 flex justify-center items-center gap-4">
                {% if current_page > 1 %}
                    <a href="/?page={{ current_page - 1 }}" class="glass px-4 py-2 rounded-xl text-sm">⬅️ Preview</a>
                {% endif %}
                <span class="font-bold text-blue-400">🔢 Page {{ current_page }}</span>
                <a href="/?page={{ current_page + 1 }}" class="glass px-4 py-2 rounded-xl text-sm">Next ➡️</a>
            </div>

        {% elif page == 'details' %}
            <!-- Movie Details -->
            <div class="max-w-4xl mx-auto flex flex-col md:flex-row gap-8 items-start">
                <img src="{{ movie.poster }}" class="w-full md:w-64 rounded-3xl shadow-2xl border border-white/10">
                <div class="flex-1">
                    <h2 class="text-3xl font-black mb-2">{{ movie.title }}</h2>
                    <div class="flex gap-2 mb-6">
                        <span class="bg-blue-600 px-3 py-1 rounded-full text-[10px] font-bold uppercase">HD 4K</span>
                        <span class="bg-gray-700 px-3 py-1 rounded-full text-[10px] font-bold">{{ movie.category }}</span>
                    </div>

                    <h4 class="text-gray-400 font-bold mb-4 border-l-4 border-blue-500 pl-3">এপিসোড তালিকা:</h4>
                    <div class="grid grid-cols-3 md:grid-cols-6 gap-3">
                        {% for ep in movie.episodes %}
                        <button onclick="handleEpClick('{{ ep.link }}')" class="ep-btn glass py-3 rounded-xl text-[10px] md:text-xs font-bold hover:bg-blue-600 transition duration-300 border-b-2 border-blue-500">
                            EP {{ loop.index }}
                        </button>
                        {% endfor %}
                    </div>
                </div>
            </div>

        {% elif page == 'profile' %}
            <!-- Profile Page -->
            <div class="max-w-md mx-auto glass p-8 rounded-3xl text-center">
                <div class="w-20 h-20 bg-blue-600 rounded-full mx-auto flex items-center justify-center text-3xl font-bold mb-4 shadow-lg">
                    {{ user.first_name[0] }}
                </div>
                <h2 class="text-xl font-bold">{{ user.first_name }} {{ user.last_name }}</h2>
                <p class="text-sm text-gray-400 mb-6">📱 {{ user.mobile }}</p>

                <div class="grid grid-cols-2 gap-4 mb-8">
                    <div class="bg-black/40 p-4 rounded-2xl">
                        <p class="text-[10px] text-gray-500">💰 Balance</p>
                        <p class="text-lg font-black text-yellow-400">{{ user.balance }}</p>
                    </div>
                    <div class="bg-black/40 p-4 rounded-2xl">
                        <p class="text-[10px] text-gray-500">👑 Status</p>
                        <p class="text-xs font-bold {{ 'text-green-400' if user.is_premium else 'text-red-400' }}">
                            {{ 'Premium' if user.is_premium else 'Free User' }}
                        </p>
                    </div>
                </div>

                <form id="updateForm" class="space-y-4 text-left">
                    <label class="text-xs text-gray-500 ml-1">Change Name</label>
                    <input type="text" id="newName" value="{{ user.first_name }}" class="w-full bg-black/40 p-3 rounded-xl border border-white/5 outline-none">
                    <label class="text-xs text-gray-500 ml-1">New Password</label>
                    <input type="password" id="newPass" placeholder="Leave blank if same" class="w-full bg-black/40 p-3 rounded-xl border border-white/5 outline-none">
                    <button type="button" onclick="updateProfile()" class="w-full bg-blue-600 py-3 rounded-xl font-bold shadow-lg">Save Changes</button>
                    <button type="button" onclick="logout()" class="w-full bg-red-600/20 text-red-400 py-3 rounded-xl font-bold">Logout</button>
                </form>
            </div>
        {% endif %}
    </main>

    <!-- Bottom Navigation (Mobile Ready) -->
    <nav class="glass fixed bottom-0 left-0 right-0 p-3 flex justify-around items-center border-t border-white/5 z-50">
        <a href="/" class="flex flex-col items-center text-gray-400 hover:text-blue-400 transition">
            <i class="fas fa-home text-lg"></i><span class="text-[9px] mt-1 font-bold uppercase">Home</span>
        </a>
        <a href="/daily-task" class="flex flex-col items-center text-gray-400 hover:text-green-400">
            <i class="fas fa-calendar-check text-lg"></i><span class="text-[9px] mt-1 font-bold uppercase">Daily Task</span>
        </a>
        <a href="/premium" class="flex flex-col items-center text-gray-400 hover:text-yellow-400">
            <i class="fas fa-crown text-lg"></i><span class="text-[9px] mt-1 font-bold uppercase">Premium</span>
        </a>
        <a href="/profile" class="flex flex-col items-center text-blue-400">
            <i class="fas fa-user-circle text-lg"></i><span class="text-[9px] mt-1 font-bold uppercase">Profile</span>
        </a>
    </nav>

    <script>
        window.onload = () => document.getElementById('loader').style.opacity = '0';
        setTimeout(() => document.getElementById('loader').remove(), 500);

        async function handleEpClick(link) {
            const res = await fetch('/api/episode/check-access', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mobile: getCookie('mobile')})
            });
            const data = await res.json();
            if(data.status === 'unlocked') {
                window.open(link, '_blank');
            } else {
                alert("⚠️ Ad Lock! আপনি এই এপিসোডটি দেখার আগে একটি এড দেখুন। (আনলক হবে ৩০ মিনিটের জন্য)");
                const adConfig = data.ad_config;
                if(adConfig.active_type === 'direct') {
                    window.open(adConfig.direct_link, '_blank');
                    unlockEpisodes();
                } else if(adConfig.active_type === 'monetag') {
                    showMonetagAd(adConfig.monetag_id);
                }
            }
        }

        async function unlockEpisodes() {
            await fetch('/api/episode/unlock', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mobile: getCookie('mobile')})
            });
            location.reload();
        }

        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
        }

        function logout() {
            document.cookie = "mobile=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            location.href = "/login";
        }
    </script>
</body>
</html>
"""

AUTH_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ type }} - {{ config.site_name }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>body{background: #0b0f19; color: white;}.glass{background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.05);}</style>
</head>
<body class="flex items-center justify-center min-h-screen p-4">
    <div class="w-full max-w-md glass p-8 rounded-3xl shadow-2xl">
        <div class="text-center mb-8">
            <h1 class="text-2xl font-black text-blue-400 uppercase tracking-widest">{{ type }}</h1>
            <p class="text-xs text-gray-400 mt-2">Access to Premium Movies</p>
        </div>

        {% if type == 'Login' %}
        <form action="/login" method="POST" class="space-y-4">
            <input type="text" name="mobile" placeholder="Mobile Number" class="w-full bg-black/40 p-4 rounded-xl border border-white/5 outline-none" required>
            <input type="password" name="password" placeholder="Password" class="w-full bg-black/40 p-4 rounded-xl border border-white/5 outline-none" required>
            <button class="w-full bg-blue-600 py-4 rounded-xl font-bold shadow-lg">Login</button>
            <p class="text-center text-xs text-gray-400">Don't have an account? <a href="/register" class="text-blue-400">Register</a></p>
            <p class="text-center text-xs text-gray-500 mt-4"><a href="/forgot">Forgot Password?</a></p>
        </form>
        {% elif type == 'Register' %}
        <form action="/register" method="POST" class="space-y-4">
            <div class="flex gap-2">
                <input type="text" name="first_name" placeholder="First Name" class="w-1/2 bg-black/40 p-4 rounded-xl border border-white/5 outline-none" required>
                <input type="text" name="last_name" placeholder="Last Name" class="w-1/2 bg-black/40 p-4 rounded-xl border border-white/5 outline-none" required>
            </div>
            <input type="text" name="mobile" placeholder="Mobile Number" class="w-full bg-black/40 p-4 rounded-xl border border-white/5 outline-none" required>
            <input type="number" name="telegram_id" placeholder="Telegram ID (Get from bot)" class="w-full bg-black/40 p-4 rounded-xl border border-white/5 outline-none" required>
            <input type="password" name="password" placeholder="Set Password" class="w-full bg-black/40 p-4 rounded-xl border border-white/5 outline-none" required>
            <button class="w-full bg-green-600 py-4 rounded-xl font-bold shadow-lg">Create Account</button>
            <p class="text-center text-xs text-gray-400">Already a member? <a href="/login" class="text-blue-400">Login</a></p>
        </form>
        {% endif %}
    </div>
</body>
</html>
"""

ADMIN_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Admin</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>body{background:#0b0f19;color:white;}.glass{background:rgba(30,41,59,0.7); backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.1);}</style>
</head>
<body class="flex flex-col md:flex-row min-h-screen">
    <!-- Sidebar -->
    <div class="w-full md:w-64 glass p-6 space-y-6">
        <h1 class="text-xl font-bold text-blue-400 text-center uppercase tracking-widest">Master Admin</h1>
        <nav class="space-y-1 text-sm">
            <a href="/admin" class="flex items-center p-3 hover:bg-blue-500/10 rounded-xl transition"><i class="fas fa-home mr-3"></i> Dashboard</a>
            <a href="#movies" class="flex items-center p-3 hover:bg-blue-500/10 rounded-xl transition"><i class="fas fa-film mr-3"></i> Movies</a>
            <a href="#ep_ads" class="flex items-center p-3 hover:bg-red-500/10 rounded-xl transition text-red-400 font-bold"><i class="fas fa-lock mr-3"></i> Episode Ad Lock</a>
            <a href="#tasks" class="flex items-center p-3 hover:bg-green-500/10 rounded-xl transition text-green-400"><i class="fas fa-link mr-3"></i> Tasks</a>
            <a href="#plans" class="flex items-center p-3 hover:bg-purple-500/10 rounded-xl transition text-purple-400 font-bold"><i class="fas fa-crown mr-3"></i> Premium Plans</a>
            <a href="#settings" class="flex items-center p-3 hover:bg-white/10 rounded-xl transition"><i class="fas fa-cog mr-3"></i> Settings</a>
        </nav>
    </div>

    <!-- Main Content -->
    <div class="flex-1 p-6 space-y-10 overflow-y-auto">
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400 uppercase">Total Users</p><p class="text-2xl font-bold text-blue-400">{{u_count}}</p></div>
            <div class="glass p-5 rounded-2xl text-center"><p class="text-xs text-gray-400 uppercase">Movies</p><p class="text-2xl font-bold text-green-400">{{m_count}}</p></div>
        </div>

        <!-- Ad Control Section -->
        <div id="ep_ads" class="glass p-8 rounded-3xl border-red-500/20 border">
            <h2 class="text-lg font-bold mb-6 text-red-400 border-b border-white/5 pb-2">Episode Button Ad Logic</h2>
            <form action="/admin/update-ep-ads" method="POST" class="space-y-4">
                <input type="text" name="direct_link" value="{{ ep_c.direct_link }}" placeholder="Direct Ad Link" class="w-full bg-black/30 p-3 rounded-xl border border-white/10">
                <input type="text" name="monetag_id" value="{{ ep_c.monetag_id }}" placeholder="Monetag Zone ID" class="w-full bg-black/30 p-3 rounded-xl border border-white/10">
                <div class="flex gap-4">
                    <input type="number" name="unlock_minutes" value="{{ ep_c.unlock_minutes }}" class="w-1/2 bg-black/30 p-3 rounded-xl">
                    <select name="active_type" class="w-1/2 bg-black/30 p-3 rounded-xl">
                        <option value="direct" {% if ep_c.active_type == 'direct' %}selected{% endif %}>Direct Link</option>
                        <option value="monetag" {% if ep_c.active_type == 'monetag' %}selected{% endif %}>Monetag Script</option>
                        <option value="off" {% if ep_c.active_type == 'off' %}selected{% endif %}>OFF</option>
                    </select>
                </div>
                <button class="w-full bg-red-600 p-3 rounded-xl font-bold">Update System</button>
            </form>
        </div>

        <!-- Global Config Section -->
        <div id="settings" class="glass p-8 rounded-3xl">
            <h2 class="text-lg font-bold mb-6">Site Configuration</h2>
            <form action="/admin/update-settings" method="POST" class="space-y-4">
                <input type="text" name="site_name" value="{{ config.site_name }}" class="w-full bg-black/20 p-3 rounded-xl">
                <input type="text" name="site_logo" value="{{ config.site_logo }}" class="w-full bg-black/20 p-3 rounded-xl">
                <textarea name="header_notice" class="w-full bg-black/20 p-3 rounded-xl h-24">{{ config.header_notice }}</textarea>
                <input type="number" name="movies_per_page" value="{{ config.movies_per_page }}" class="w-full bg-black/20 p-3 rounded-xl">
                <button class="w-full bg-blue-600 p-3 rounded-xl font-bold">Save All Settings</button>
            </form>
        </div>

        <!-- Movie List Section -->
        <div id="movies" class="glass p-8 rounded-3xl">
            <h2 class="text-lg font-bold mb-6 text-yellow-400">Movie Management</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead><tr class="text-gray-500 uppercase text-[10px]"><th class="p-4">Title</th><th class="p-4">Episodes</th><th class="p-4 text-right">Action</th></tr></thead>
                    <tbody>
                        {% for m in movies %}
                        <tr class="border-b border-white/5 hover:bg-white/5 transition">
                            <td class="p-4 font-bold text-sm">{{ m.title }}</td>
                            <td class="p-4 text-xs">{{ m.episodes|length }} EP</td>
                            <td class="p-4 text-right"><a href="/admin/movie/delete/{{ m._id }}" class="text-red-500 hover:text-red-700" onclick="return confirm('Delete this?')"><i class="fas fa-trash"></i></a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# ৩. রাউটস ও লজিক (API + HTML)
# ==========================================

def get_user_from_cookie():
    mobile = request.cookies.get('mobile')
    if not mobile: return None
    return users_col.find_one({"mobile": mobile})

@app.route('/')
def home_page():
    user = get_user_from_cookie()
    if not user: return redirect('/login')
    
    page = int(request.args.get('page', 1))
    config = settings_col.find_one({"type": "site_config"})
    limit = config.get('movies_per_page', 12)
    skip = (page - 1) * limit
    
    movies = list(movies_col.find().sort('_id', -1).skip(skip).limit(limit))
    for m in movies: m['_id'] = str(m['_id'])
    
    return render_template_string(USER_UI_HTML, page='home', config=config, movies=movies, current_page=page, user=user)

@app.route('/movie/<id>')
def movie_details(id):
    user = get_user_from_cookie()
    if not user: return redirect('/login')
    movie = movies_col.find_one({"_id": ObjectId(id)})
    config = settings_col.find_one({"type": "site_config"})
    return render_template_string(USER_UI_HTML, page='details', config=config, movie=movie, user=user)

@app.route('/profile')
def profile_page():
    user = get_user_from_cookie()
    if not user: return redirect('/login')
    config = settings_col.find_one({"type": "site_config"})
    return render_template_string(USER_UI_HTML, page='profile', config=config, user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        user = users_col.find_one({"mobile": mobile, "password": password})
        if user:
            resp = make_response(redirect('/'))
            resp.set_cookie('mobile', mobile, max_age=30*24*60*60) # ৩০ দিনের জন্য লগইন থাকবে
            return resp
        return "ভুল পাসওয়ার্ড বা মোবাইল নাম্বার!"
    config = settings_col.find_one({"type": "site_config"})
    return render_template_string(AUTH_UI_HTML, type='Login', config=config)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        if users_col.find_one({"mobile": mobile}): return "ইতিমধ্যে নিবন্ধিত!"
        
        users_col.insert_one({
            "first_name": request.form.get('first_name'),
            "last_name": request.form.get('last_name'),
            "mobile": mobile,
            "telegram_id": int(request.form.get('telegram_id')),
            "password": request.form.get('password'),
            "balance": 0, "is_premium": False, "premium_expiry": None
        })
        return redirect('/login')
    config = settings_col.find_one({"type": "site_config"})
    return render_template_string(AUTH_UI_HTML, type='Register', config=config)

# ---------------------------------------------------------
# ৪. অ্যাডমিন প্যানেল রাউটস (পাসওয়ার্ড প্রোটেক্টেড)
# ---------------------------------------------------------

@app.route('/admin')
def admin_dashboard():
    # ইউজাররা যেন অ্যাডমিন প্যানেলে ঢুকতে না পারে সে জন্য পাসওয়ার্ড চেক
    pw = request.args.get('pw')
    if pw != ADMIN_PASS:
        return "❌ Access Denied! সঠিক অ্যাডমিন পাসওয়ার্ড দিয়ে লিংকে ঢুকুন। (উদা: /admin?pw=admin7120)"
    
    config = settings_col.find_one({"type": "site_config"})
    ep_c = ep_ads_col.find_one({"type": "ep_ad_config"})
    movies = list(movies_col.find().sort('_id', -1))
    return render_template_string(ADMIN_UI_HTML, config=config, ep_c=ep_c, movies=movies,
                                 u_count=users_col.count_documents({}), 
                                 m_count=len(movies), plans=list(plans_col.find()))

@app.route('/admin/update-settings', methods=['POST'])
def admin_update_settings():
    settings_col.update_one({"type": "site_config"}, {"$set": {
        "site_name": request.form.get('site_name'), "site_logo": request.form.get('site_logo'),
        "header_notice": request.form.get('header_notice'), "movies_per_page": int(request.form.get('movies_per_page'))
    }})
    return redirect(f'/admin?pw={ADMIN_PASS}')

@app.route('/admin/update-ep-ads', methods=['POST'])
def admin_update_ep():
    ep_ads_col.update_one({"type": "ep_ad_config"}, {"$set": {
        "direct_link": request.form.get('direct_link'), "monetag_id": request.form.get('monetag_id'),
        "unlock_minutes": int(request.form.get('unlock_minutes')), "active_type": request.form.get('active_type')
    }})
    return redirect(f'/admin?pw={ADMIN_PASS}')

@app.route('/admin/movie/delete/<id>')
def admin_del_movie(id):
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect(f'/admin?pw={ADMIN_PASS}')

# ---------------------------------------------------------
# ৫. API এন্ডপয়েন্টস (এপিসোড লক চেক)
# ---------------------------------------------------------

@app.route('/api/episode/check-access', methods=['POST'])
def api_check_access():
    mobile = request.json.get('mobile')
    user = users_col.find_one({"mobile": mobile})
    if not user: return jsonify({"status": "error"})
    
    if user.get('is_premium'): return jsonify({"status": "unlocked"})
    
    unlock = ep_unlock_col.find_one({"mobile": mobile})
    if unlock and datetime.now() < unlock['expiry']:
        return jsonify({"status": "unlocked"})
    
    return jsonify({"status": "locked", "ad_config": ep_ads_col.find_one({"type": "ep_ad_config"})})

@app.route('/api/episode/unlock', methods=['POST'])
def api_unlock_ep():
    mobile = request.json.get('mobile')
    config = ep_ads_col.find_one({"type": "ep_ad_config"})
    expiry = datetime.now() + timedelta(minutes=int(config['unlock_minutes']))
    ep_unlock_col.update_one({"mobile": mobile}, {"$set": {"expiry": expiry}}, upsert=True)
    return jsonify({"status": "success"})

# ==========================================
# ৬. টেলিগ্রাম বট লজিক (অ্যাডমিন প্রোটেক্টেড)
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
    bot.reply_to(message, f"👋 স্বাগতম!\nআপনার টেলিগ্রাম আইডি: `{message.from_user.id}`\nএটি একাউন্ট সাইনআপ ও ওটিপি পেতে ব্যবহার করুন।")

@bot.message_handler(commands=['movie'])
def bot_add_movie(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ আপনি অ্যাডমিন নন!")
    msg = bot.send_message(message.chat.id, "🎬 মুভির নাম লিখুন:")
    bot.register_next_step_handler(msg, step_title)

def step_title(message):
    title = message.text
    msg = bot.send_message(message.chat.id, "📂 মুভির ক্যাটাগরি:")
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
        movies_col.insert_one({"title": title, "category": cat, "poster": poster, "episodes": eps, "added_at": datetime.now()})
        return bot.send_message(message.chat.id, f"✅ সফলভাবে যোগ হয়েছে: {title}")
    
    if message.content_type in ['video', 'document']:
        sent = bot.forward_message(FILE_CHANNEL_ID, message.chat.id, message.message_id)
        ep_name = f"{title} - Episode {len(eps)+1}"
        eps.append({"name": ep_name, "link": f"https://t.me/c/{str(FILE_CHANNEL_ID).replace('-100','')}/{sent.message_id}"})
        bot.send_message(message.chat.id, f"📥 {ep_name} যোগ হয়েছে।")
    
    bot.register_next_step_handler(message, lambda m: collect_eps(m, title, cat, poster, eps))

# ==========================================
# ৭. রান সার্ভার (Koyeb/Vercel)
# ==========================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
