import os
import telebot
from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# --- কনফিগারেশন (আপনার তথ্য এখানে দিন) ---
TOKEN = "8655043839:AAFTUxq56taWUPU9uXRKuL7iyKLXRvk-WqM"  # টেলিগ্রাম বট টোকেন
BOT_USERNAME = "dramastorkingsbot"  # বটের ইউজারনেম (@ ছাড়া)
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0"
BASE_URL = "https://dramastoreking24.vercel.app"

app = Flask(__name__)
app.secret_key = "premium_movie_system_key_99"
app.config["MONGO_URI"] = MONGO_URI
mongo = PyMongo(app)
bot = telebot.TeleBot(TOKEN)

# ইউজার স্টেট ট্র্যাকিং (মুভি এড করার জন্য)
user_states = {}

# --- প্রিমিয়াম ডার্ক থিম CSS স্টাইল ---
PREMIUM_STYLE = """
<style>
    :root { --primary: #e50914; --bg: #0a0a0a; --card-bg: #141414; --text: #ffffff; --gray: #808080; }
    * { box-sizing: border-box; }
    body { background: var(--bg); color: var(--text); font-family: 'Roboto', sans-serif; margin: 0; padding-bottom: 70px; }
    a { text-decoration: none; color: inherit; }
    
    /* Loader */
    #loader { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 10000; text-align: center; padding-top: 50vh; }
    .spinner { width: 50px; height: 50px; border: 5px solid #333; border-top: 5px solid var(--primary); border-radius: 50%; animation: spin 1s linear infinite; margin: auto; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

    /* Notice Bar */
    .notice-bar { background: var(--primary); color: #fff; padding: 10px; text-align: center; font-weight: bold; font-size: 14px; position: sticky; top: 0; z-index: 1000; }
    
    /* Navbar */
    .navbar { display: flex; justify-content: space-around; background: #000; padding: 15px 0; border-bottom: 1px solid #222; }
    .navbar a { font-size: 14px; color: var(--gray); transition: 0.3s; }
    .navbar a:hover, .navbar a.active { color: var(--primary); }

    .container { padding: 15px; max-width: 1200px; margin: auto; }
    .section-title { font-size: 18px; font-weight: bold; margin: 20px 0 10px; padding-left: 10px; border-left: 4px solid var(--primary); }

    /* Slider Style */
    .slider { display: flex; overflow-x: auto; gap: 15px; padding-bottom: 10px; scrollbar-width: none; }
    .slider::-webkit-scrollbar { display: none; }
    .slider-item { min-width: 260px; height: 150px; border-radius: 8px; position: relative; overflow: hidden; }
    .slider-item img { width: 100%; height: 100%; object-fit: cover; opacity: 0.6; }
    .slider-info { position: absolute; bottom: 10px; left: 10px; font-weight: bold; text-shadow: 2px 2px 5px #000; }

    /* Movie Grid */
    .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
    .movie-card { background: var(--card-bg); border-radius: 10px; overflow: hidden; position: relative; border: 1px solid #222; transition: 0.3s; }
    .movie-card:hover { transform: translateY(-5px); border-color: var(--primary); }
    .movie-card img { width: 100%; height: 210px; object-fit: cover; }
    .badge-cat { position: absolute; top: 8px; left: 8px; background: var(--primary); padding: 3px 7px; font-size: 10px; border-radius: 4px; font-weight: bold; }
    .badge-views { position: absolute; bottom: 45px; right: 8px; background: rgba(0,0,0,0.7); padding: 3px 7px; font-size: 10px; border-radius: 4px; }
    .movie-title { padding: 8px; font-size: 13px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    /* Pagination */
    .pagination { display: flex; justify-content: center; gap: 10px; margin: 30px 0; }
    .page-link { padding: 10px 15px; background: #222; border-radius: 5px; color: #fff; font-size: 14px; }
    .page-link.active { background: var(--primary); }

    /* Forms */
    .card { background: var(--card-bg); padding: 20px; border-radius: 12px; max-width: 450px; margin: 20px auto; }
    input { width: 100%; padding: 12px; margin: 10px 0; background: #222; border: 1px solid #333; color: #fff; border-radius: 6px; }
    .btn { width: 100%; padding: 12px; background: var(--primary); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; display: block; text-align: center; }
    .back-btn { display: inline-block; margin-bottom: 15px; color: var(--gray); font-size: 14px; }

    /* Episode Buttons */
    .ep-btn { background: #222; border: 1px solid #333; padding: 15px; display: block; margin-bottom: 10px; border-radius: 8px; border-left: 4px solid var(--primary); transition: 0.3s; }
    .ep-btn:hover { background: #282828; }
</style>
"""

# --- মেইন লেআউট ---
LAYOUT = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{{{{ settings.site_name }}}}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    {PREMIUM_STYLE}
</head>
<body>
    <div id="loader"><div class="spinner"></div><br>লোড হচ্ছে...</div>
    <div class="notice-bar">{{{{ settings.notice }}}}</div>
    
    <div class="navbar">
        <a href="/" class="{{'active' if request.endpoint == 'index'}}"><i class="fas fa-home"></i> হোম</a>
        <a href="/profile" class="{{'active' if request.endpoint == 'profile'}}"><i class="fas fa-user"></i> প্রোফাইল</a>
        {{% if session.role == 'admin' %}}
        <a href="/admin" class="{{'active' if request.endpoint == 'admin'}}"><i class="fas fa-user-shield"></i> এডমিন</a>
        {{% endif %}}
    </div>

    <div class="container">
        {{% with messages = get_flashed_messages() %}}
          {{% if messages %}}
            {{% for message in messages %}}
              <p style="background:var(--primary); padding:10px; text-align:center; border-radius:5px;">{{{{ message }}}}</p>
            {{% endfor %}}
          {{% endif %}}
        {{% endwith %}}
        
        {{% block content %}}{{% endblock %}}
    </div>

    <script>
        function showLoader() {{ document.getElementById('loader').style.display = 'block'; }}
        window.addEventListener('pageshow', function() {{ document.getElementById('loader').style.display = 'none'; }});
    </script>
</body>
</html>
"""

# --- হেল্পার ---
def get_site_settings():
    s = mongo.db.settings.find_one({"type": "config"})
    if not s:
        s = {"site_name": "PremiumMovie", "notice": "আমাদের সাইটে স্বাগতম!", "monetag_id": "10351894", "ad_limit": 2}
    return s

# --- ওয়েবসাইট রাউটস ---

@app.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('login'))
    settings = get_site_settings()
    
    # টপ ২০ ভিউ মুভি স্লাইডার
    sliders = list(mongo.db.movies.find().sort("views", -1).limit(20))
    
    # পেজিনেশন লজিক
    page = int(request.args.get('page', 1))
    per_page = 20 if page == 1 else 50
    skip = 0 if page == 1 else 20 + (page - 2) * 50
    recent_movies = list(mongo.db.movies.find().sort("_id", -1).skip(skip).limit(per_page))
    
    content = """
    <div class="section-title">টপ ট্রেন্ডিং</div>
    <div class="slider">
        {% for s in sliders %}
        <div class="slider-item" onclick="showLoader(); location.href='/movie/{{s._id}}'">
            <img src="{{s.poster}}">
            <div class="slider-info">{{s.title}}</div>
        </div>
        {% endfor %}
    </div>

    <div class="section-title">সদ্য আপলোড করা</div>
    <div class="movie-grid">
        {% for m in movies %}
        <div class="movie-card" onclick="showLoader(); location.href='/movie/{{m._id}}'">
            <span class="badge-cat">{{m.category}}</span>
            <img src="{{m.poster}}">
            <span class="badge-views"><i class="fas fa-eye"></i> {{m.views}}</span>
            <div class="movie-title">{{m.title}}</div>
        </div>
        {% endfor %}
    </div>

    <div class="pagination">
        {% if page > 1 %}
        <a href="/?page={{page-1}}" class="page-link">Previous</a>
        {% endif %}
        <a href="#" class="page-link active">{{page}}</a>
        <a href="/?page={{page+1}}" class="page-link">Next</a>
    </div>
    """
    return render_template_string(LAYOUT, settings=settings, sliders=sliders, movies=recent_movies, page=page, content=content)

@app.route('/movie/<m_id>')
def movie_detail(m_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    settings = get_site_settings()
    
    # ভিউ আপডেট
    movie = mongo.db.movies.find_one_and_update({"_id": ObjectId(m_id)}, {"$inc": {"views": 1}}, return_document=True)
    
    content = f"""
    <a href="javascript:history.back()" class="back-btn" onclick="showLoader()"><i class="fas fa-arrow-left"></i> ফিরে যান</a>
    <div style="text-align:center;">
        <img src="{movie['poster']}" style="width:100%; max-width:350px; border-radius:12px; box-shadow: 0 5px 15px rgba(0,0,0,0.5);">
        <h2 style="margin:20px 0 5px;">{movie['title']}</h2>
        <p style="color:var(--gray); margin-bottom:20px;">{movie['category']} • {movie['views']} Views</p>
        
        <div class="card" style="max-width:100%; text-align:left;">
            <h4 style="margin-top:0; border-bottom:1px solid #333; padding-bottom:10px;">এপিসোড ডাউনলোড লিঙ্ক:</h4>
            {% for i, fid in enumerate(movie['episodes']) %}
            <div class="ep-btn" onclick="handleAd('{fid}')">
                <i class="fas fa-play-circle" style="color:var(--primary)"></i> &nbsp; Episode {i+1:02d} - ডাউনলোড করুন
            </div>
            {% endfor %}
        </div>
    </div>

    <script src='//libtl.com/sdk.js' data-zone='{settings['monetag_id']}' data-sdk='show_{settings['monetag_id']}'></script>
    <script>
        function handleAd(fid) {{
            let adLimit = {settings['ad_limit']};
            let count = sessionStorage.getItem('ad_'+fid) || 0;
            if (count < adLimit) {{
                if (typeof show_{settings['monetag_id']} === 'function') {{ show_{settings['monetag_id']}(); }}
                count++;
                sessionStorage.setItem('ad_'+fid, count);
                alert("এড লোড হচ্ছে... আর " + (adLimit - count) + " বার এড দেখলে লিঙ্ক পাবেন।");
            }} else {{
                showLoader();
                window.location.href = "https://t.me/{BOT_USERNAME}?start=" + fid;
            }}
        }}
    </script>
    """
    return render_template_string(LAYOUT, settings=settings, movie=movie, enumerate=enumerate, content=content)

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    settings = get_site_settings()
    content = f"""
    <div class="card" style="text-align:center;">
        <i class="fas fa-user-circle fa-5x" style="color:var(--gray); margin-bottom:15px;"></i>
        <h2 style="margin:5px;">{user['fname']} {user['lname']}</h2>
        <p style="color:var(--gray);">{user['number']}</p>
        <div style="background:#222; padding:10px; border-radius:8px; margin:20px 0;">রোল: {user['role'].upper()}</div>
        <a href="/logout" class="btn" style="background:#333;">লগআউট করুন</a>
    </div>
    """
    return render_template_string(LAYOUT, settings=settings, content=content)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin': return "এক্সেস নেই", 403
    settings = get_site_settings()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'site':
            mongo.db.settings.update_one({"type": "config"}, {"$set": {"site_name": request.form.get('site_name'), "notice": request.form.get('notice')}}, upsert=True)
        elif action == 'ad':
            mongo.db.settings.update_one({"type": "config"}, {"$set": {"monetag_id": request.form.get('monetag_id'), "ad_limit": int(request.form.get('ad_limit'))}}, upsert=True)
        flash("সফলভাবে আপডেট হয়েছে!")
        return redirect('/admin')

    content = f"""
    <div class="card">
        <h3>সাইট সেটিংস</h3>
        <form method="POST">
            <input type="hidden" name="action" value="site">
            সাইটের নাম: <input name="site_name" value="{settings['site_name']}">
            নোটিশ টেক্সট: <input name="notice" value="{settings['notice']}">
            <button class="btn">সেভ করুন</button>
        </form>
    </div>
    <div class="card">
        <h3>মনিটেগ এড সেটিংস</h3>
        <form method="POST">
            <input type="hidden" name="action" value="ad">
            জোন আইডি (Zone ID): <input name="monetag_id" value="{settings['monetag_id']}">
            এড দেখার লিমিট: <input type="number" name="ad_limit" value="{settings['ad_limit']}">
            <button class="btn" style="background:green;">এড সেটিংস আপডেট</button>
        </form>
    </div>
    """
    return render_template_string(LAYOUT, settings=settings, content=content)

@app.route('/register', methods=['GET', 'POST'])
def register():
    settings = get_site_settings()
    if request.method == 'POST':
        fname, lname, number, password = request.form.get('fname'), request.form.get('lname'), request.form.get('number'), request.form.get('password')
        if mongo.db.users.find_one({"number": number}): flash("এই নাম্বারটি ইতিমধ্যে আছে!")
        else:
            mongo.db.users.insert_one({"fname": fname, "lname": lname, "number": number, "password": generate_password_hash(password), "role": "user"})
            return redirect('/login')
    content = """<div class="card"><h3>রেজিস্ট্রেশন</h3><form method="POST"><input name="fname" placeholder="ফাস্ট নাম" required><input name="lname" placeholder="লাস্ট নাম" required><input name="number" placeholder="নাম্বার" required><input type="password" name="password" placeholder="পাসওয়ার্ড" required><button class="btn">রেজিস্টার</button></form><br><center><a href="/login">লগিন করুন</a></center></div>"""
    return render_template_string(LAYOUT, settings=settings, content=content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    settings = get_site_settings()
    if request.method == 'POST':
        user = mongo.db.users.find_one({"number": request.form.get('number')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['user_id'], session['role'] = str(user['_id']), user.get('role', 'user')
            return redirect('/')
        flash("নাম্বার বা পাসওয়ার্ড ভুল!")
    content = """<div class="card"><h3>লগিন</h3><form method="POST"><input name="number" placeholder="নাম্বার" required><input type="password" name="password" placeholder="পাসওয়ার্ড" required><button class="btn">লগিন</button></form><br><center><a href="/register">নতুন অ্যাকাউন্ট খুলুন</a></center></div>"""
    return render_template_string(LAYOUT, settings=settings, content=content)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# --- টেলিগ্রাম বট লজিক ---

@bot.message_handler(commands=['movie'])
def bot_add_movie(message):
    try:
        data = message.text.split('/movie ')[1].split(',')
        name, cat = data[0].strip(), data[1].strip()
        user_states[message.chat.id] = {"title": name, "category": cat, "episodes": [], "views": 0, "poster": "https://via.placeholder.com/300x450?text=No+Poster"}
        bot.reply_to(message, f"🎬 মুভি: {name}\nএখন একের পর এক ফাইলগুলো পাঠান। শেষ হলে /Done লিখুন।")
    except:
        bot.reply_to(message, "ব্যবহার: /movie মুভির নাম, ক্যাটাগরি")

@bot.message_handler(content_types=['video', 'document'])
def bot_handle_files(message):
    if message.chat.id in user_states:
        fid = message.video.file_id if message.content_type == 'video' else message.document.file_id
        user_states[message.chat.id]['episodes'].append(fid)
        bot.reply_to(message, f"✅ Episode {len(user_states[message.chat.id]['episodes']):02d} যুক্ত হয়েছে।")

@bot.message_handler(commands=['Done'])
def bot_done(message):
    if message.chat.id in user_states:
        mongo.db.movies.insert_one(user_states[message.chat.id])
        del user_states[message.chat.id]
        bot.reply_to(message, "🚀 মুভিটি সাইটে পাবলিশ হয়েছে!")

@bot.message_handler(commands=['start'])
def bot_start(message):
    args = message.text.split()
    if len(args) > 1:
        bot.send_message(message.chat.id, "আপনার ফাইলটি নিচে দেওয়া হলো:")
        try: bot.send_document(message.chat.id, args[1])
        except: bot.send_video(message.chat.id, args[1])
    else:
        bot.reply_to(message, "আমি মুভি ফাইল স্টোর বট।")

# --- ওয়েব হুক ও রান ---
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('utf-8'))])
    return "!", 200

@app.route('/set_webhook')
def set_webhook():
    s = bot.set_webhook(url=BASE_URL + '/' + TOKEN)
    return "Success" if s else "Failed"

# একদম নিচের এই অংশটুকু পরিবর্তন করুন
if __name__ == '__main__':
    app.run(debug=True)

# ভার্সেলের জন্য এটি এক্সপোর্ট করুন 
handler = app
app = app
