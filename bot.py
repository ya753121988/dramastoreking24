import os
import telebot
import math
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId
from telebot import types

# ==========================================
# [FEATURE #1] কনফিগারেশন
# ==========================================
TOKEN = '8655043839:AAGmoyWwzJFAi9hOovKNeySOp6UzrHBPibQ' 
MONGO_URI = 'mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0' 
ADMIN_ID = 7120801813 # আপনার টেলিগ্রাম আইডি

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)
app.secret_key = "movie_ultra_king_99"

client = MongoClient(MONGO_URI)
db = client['movie_final_v20']
movies_col = db['movies']
settings_col = db['settings']
tasks_col = db['tasks']
users_col = db['users']
packages_col = db['packages']

# ডিফল্ট সেটিংস চেক
if not settings_col.find_one({"type": "config"}):
    settings_col.insert_one({"type": "config", "terazone_id": "8888", "ad_link": "https://example.com/ad"})

# ==========================================
# [WEBHOOK] ভার্সেল এর জন্য প্রয়োজনীয় রুট
# ==========================================
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else: return 'Forbidden', 403

# ==========================================
# [BOT ADMIN LOGIC]
# ==========================================
user_states = {}

def is_admin(message):
    return message.from_user.id == ADMIN_ID

@bot.message_handler(commands=['start', 'admin'])
def admin_menu(message):
    if not is_admin(message): 
        bot.reply_to(message, "আপনি অ্যাডমিন নন!")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Add Movie 🎬", "Add Task 📝")
    markup.add("Add Package 🎁", "Ad Settings ⚙️")
    markup.add("Delete Task ❌", "Delete Package 🗑️")
    bot.send_message(message.chat.id, "অ্যাডমিন প্যানেল:", reply_markup=markup)

# [MOVIE UPLOAD SYSTEM]
@bot.message_handler(func=lambda m: m.text == "Add Movie 🎬")
def movie_start(message):
    if not is_admin(message): return
    user_states[message.chat.id] = {'step': 'name', 'data': {'episodes': []}}
    bot.send_message(message.chat.id, "মুভির নাম লিখুন:")

@bot.message_handler(func=lambda m: m.chat.id in user_states, content_types=['text', 'photo', 'document'])
def movie_flow(message):
    state = user_states[message.chat.id]
    
    if state['step'] == 'name' and message.text:
        state['data']['name'] = message.text
        state['step'] = 'poster'
        bot.send_message(message.chat.id, "মুভির পোস্টার (ছবি) পাঠান:")
        
    elif state['step'] == 'poster' and message.content_type == 'photo':
        fid = message.photo[-1].file_id
        finfo = bot.get_file(fid)
        # পোস্টার ইউআরএল জেনারেট (মংোডিবিতে সেভ হবে)
        state['data']['poster'] = f"https://api.telegram.org/file/bot{TOKEN}/{finfo.file_path}"
        state['step'] = 'episodes'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True).add("Done ✅")
        bot.send_message(message.chat.id, "এখন মুভির ফাইলগুলো (Episodes) একটা পর একটা পাঠান। শেষ হলে 'Done ✅' দিন।", reply_markup=markup)
        
    elif state['step'] == 'episodes':
        if message.text == "Done ✅":
            if state['data']['episodes']:
                movies_col.insert_one(state['data'])
                bot.send_message(message.chat.id, "মুভি সাইটে সফলভাবে সেভ হয়েছে!", reply_markup=types.ReplyKeyboardRemove())
            else:
                bot.send_message(message.chat.id, "কোনো ফাইল অ্যাড করা হয়নি! মুভি সেভ হয়নি।")
            del user_states[message.chat.id]
        elif message.document:
            state['data']['episodes'].append({'name': message.document.file_name, 'file_id': message.document.file_id})
            bot.send_message(message.chat.id, f"সংযুক্ত: {message.document.file_name}\nআরো থাকলে পাঠান অথবা Done দিন।")

# [TASK & PACKAGE SYSTEM]
@bot.message_handler(func=lambda m: m.text == "Add Task 📝")
def add_task_req(message):
    if not is_admin(message): return
    msg = bot.send_message(message.chat.id, "টাস্ক ডাটা দিন:\nType(direct/monetag) | Title | Content(Link/Script) | Coins")
    bot.register_next_step_handler(msg, save_task)

def save_task(message):
    try:
        p = message.text.split('|')
        tasks_col.insert_one({"type": p[0].strip(), "title": p[1].strip(), "content": p[2].strip(), "coins": int(p[3].strip())})
        bot.reply_to(message, "টাস্ক সেভ হয়েছে!")
    except: bot.reply_to(message, "ভুল ফরম্যাট! Example: direct | Title | https://link.com | 5")

@bot.message_handler(func=lambda m: m.text == "Add Package 🎁")
def add_pkg_req(message):
    if not is_admin(message): return
    msg = bot.send_message(message.chat.id, "প্যাকেজ ডাটা দিন:\nName | Days | Coins")
    bot.register_next_step_handler(msg, save_pkg)

def save_pkg(message):
    try:
        p = message.text.split('|')
        packages_col.insert_one({"name": p[0].strip(), "days": int(p[1].strip()), "price": int(p[2].strip())})
        bot.reply_to(message, "প্যাকেজ সেভ হয়েছে!")
    except: bot.reply_to(message, "ভুল ফরম্যাট!")

# [SETTINGS]
@bot.message_handler(func=lambda m: m.text == "Ad Settings ⚙️")
def ad_set(message):
    if not is_admin(message): return
    msg = bot.send_message(message.chat.id, "Terazone_ID [Space] Ad_Link দিন:")
    bot.register_next_step_handler(msg, update_ads)

def update_ads(message):
    try:
        tid, alink = message.text.split(' ')
        settings_col.update_one({"type": "config"}, {"$set": {"terazone_id": tid, "ad_link": alink}})
        bot.reply_to(message, "সেটিংস আপডেট হয়েছে!")
    except: bot.reply_to(message, "ভুল ফরম্যাট!")

@bot.message_handler(func=lambda m: m.text in ["Delete Task ❌", "Delete Package 🗑️"])
def delete_list(message):
    if not is_admin(message): return
    col = tasks_col if "Task" in message.text else packages_col
    for item in col.find():
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("Delete", callback_data=f"del_{'t' if col==tasks_col else 'p'}_{item['_id']}"))
        bot.send_message(message.chat.id, f"Item: {item.get('title') or item.get('name')}", reply_markup=btn)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def handle_del(call):
    _, t, oid = call.data.split('_')
    (tasks_col if t=='t' else packages_col).delete_one({"_id": ObjectId(oid)})
    bot.answer_callback_query(call.id, "Deleted!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==========================================
# [WEBSITE LOGIC - FLASK]
# ==========================================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if users_col.find_one({"mobile": request.form['mobile']}): return "Mobile already exists!"
        users_col.insert_one({
            "fname": request.form['fname'], "lname": request.form['lname'],
            "mobile": request.form['mobile'], "password": request.form['password'],
            "coins": 0, "premium_until": None
        })
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = users_col.find_one({"mobile": request.form['mobile'], "password": request.form['password']})
        if u:
            session['user_id'] = str(u['_id'])
            return redirect(url_for('home'))
        return "Invalid login!"
    return render_template('login.html')

@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    page = request.args.get('page', 1, type=int)
    limit = 30
    skip = (page - 1) * limit
    total = movies_col.count_documents({})
    movies = movies_col.find().sort('_id', DESCENDING).skip(skip).limit(limit)
    return render_template('index.html', movies=movies, page=page, total_pages=math.ceil(total/limit))

@app.route('/movie/<id>')
def details(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    m = movies_col.find_one({"_id": ObjectId(id)})
    c = settings_col.find_one({"type": "config"})
    u = users_col.find_one({"_id": ObjectId(session['user_id'])})
    is_premium = u.get('premium_until') and u['premium_until'] > datetime.now()
    return render_template('details.html', movie=m, config=c, is_premium=is_premium)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    u = users_col.find_one({"_id": ObjectId(session['user_id'])})
    if request.method == 'POST':
        users_col.update_one({"_id": u['_id']}, {"$set": {"fname": request.form['fname'], "password": request.form['password']}})
        return redirect(url_for('profile'))
    return render_template('profile.html', user=u)

@app.route('/tasks')
def tasks_page():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('tasks.html', tasks=tasks_col.find())

@app.route('/claim/<tid>')
def claim(tid):
    if 'user_id' not in session: return redirect(url_for('login'))
    t = tasks_col.find_one({"_id": ObjectId(tid)})
    users_col.update_one({"_id": ObjectId(session['user_id'])}, {"$inc": {"coins": t['coins']}})
    return redirect(url_for('tasks_page'))

@app.route('/premium')
def premium():
    if 'user_id' not in session: return redirect(url_for('login'))
    u = users_col.find_one({"_id": ObjectId(session['user_id'])})
    pkgs = packages_col.find()
    return render_template('premium.html', pkgs=pkgs, user=u)

@app.route('/buy/<pid>')
def buy(pid):
    p = packages_col.find_one({"_id": ObjectId(pid)})
    u = users_col.find_one({"_id": ObjectId(session['user_id'])})
    if u['coins'] >= p['price']:
        end_date = datetime.now() + timedelta(days=p['days'])
        users_col.update_one({"_id": u['_id']}, {"$inc": {"coins": -p['price']}, "$set": {"premium_until": end_date}})
        return redirect(url_for('profile'))
    return "Not enough coins!"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# [TEMPLATES GENERATOR]
# ==========================================
def create_templates():
    if not os.path.exists('templates'): os.makedirs('templates')
    css = "<style>body{background:#000;color:#fff;font-family:sans-serif;text-align:center;margin:0;padding-bottom:80px}.nav{background:#111;position:fixed;bottom:0;width:100%;display:flex;justify-content:space-around;padding:15px;border-top:1px solid gold;z-index:1000}.nav a{color:gold;text-decoration:none;font-size:12px;font-weight:bold}.card{background:#1a1a1a;margin:10px;padding:10px;border-radius:10px;border:1px solid #333}.btn{display:block;background:gold;color:#000;padding:12px;margin:10px auto;text-decoration:none;border-radius:5px;width:85%;font-weight:bold;border:none}.inp{width:85%;padding:12px;margin:10px;border-radius:5px;border:none;background:#222;color:#fff}img{max-width:100%;border-radius:10px}</style>"
    nav = '<div class="nav"><a href="/">HOME</a><a href="/tasks">TASKS</a><a href="/premium">PREMIUM</a><a href="/profile">PROFILE</a></div>'

    with open('templates/signup.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>SIGNUP</h2><form method="POST"><input name="fname" placeholder="First Name" class="inp" required><input name="lname" placeholder="Last Name" class="inp" required><input name="mobile" placeholder="Mobile Number" class="inp" required><input name="password" type="password" placeholder="Password" class="inp" required><button class="btn">REGISTER</button></form><a href="/login" style="color:white">Login here</a></body></html>')
    
    with open('templates/login.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>LOGIN</h2><form method="POST"><input name="mobile" placeholder="Mobile" class="inp" required><input name="password" type="password" placeholder="Password" class="inp" required><button class="btn">LOGIN</button></form><a href="/signup" style="color:white">Create Account</a></body></html>')

    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>MOVIES</h2><div style="display:grid;grid-template-columns:1fr 1fr">{"{% for m in movies %}"}<div class="card"><img src="{"{{m.poster}}"}" loading="lazy"><p>{"{{m.name}}"}</p><a href="/movie/{"{{m._id|string}}"}" class="btn">WATCH</a></div>{"{% endfor %}"}</div>' +
                '<div>{"{% if page > 1 %}"}<a href="/?page={"{{page-1}}"}" style="color:white">Prev</a>{"{% endif %}"} Page {"{{page}}"} {"{% if page < total_pages %}"}<a href="/?page={"{{page+1}}"}" style="color:white">Next</a>{"{% endif %}"}</div>' + nav + '</body></html>')

    with open('templates/details.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><img src="{"{{movie.poster}}"}"><h2>{"{{movie.name}}"}</h2>' +
                '{"{% for ep in movie.episodes %}"}' +
                '{"{% if is_premium %}"}<a href="https://t.me/share/url?url=FILE_{{"{{ep.file_id}}"}}" class="btn">{"{{ep.name}}"} (Premium Link)</a>' +
                '{"{% else %}"}<a href="{{"{{config.ad_link}}"}}?zone={{"{{config.terazone_id}}"}}&file={{"{{ep.file_id}}"}}" class="btn">{"{{ep.name}}"} (Watch Ad)</a>{"{% endif %}"}' +
                '{"{% endfor %}"}' + nav + '</body></html>')

    with open('templates/profile.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>PROFILE</h2><div class="card"><p>Balance: {"{{user.coins}}"} Coins</p><form method="POST"><input name="fname" value="{"{{user.fname}}"}" class="inp"><input name="password" value="{"{{user.password}}"}" class="inp"><button class="btn">Update Profile</button></form><a href="/logout" style="color:red">Logout</a></div>' + nav + '</body></html>')
    
    with open('templates/tasks.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>TASKS</h2>{"{% for t in tasks %}"}<div class="card"><h4>{"{{t.title}}"}</h4>' +
                '{"{% if t.type == \'direct\' %}"}<a href="{{"{{t.content}}"}}" target="_blank" onclick="location.href=\'/claim/{{"{{t._id|string}}"}}\'" class="btn">Complete ({"{{t.coins}}"} Coins)</a>' +
                '{"{% else %}"}<button onclick="eval(\'{{"{{t.content}}"}}\'); location.href=\'/claim/{{"{{t._id|string}}"}}\'" class="btn">Watch Ad ({"{{t.coins}}"} Coins)</button>{"{% endif %}"}</div>{"{% endfor %}"}' + nav + '</body></html>')
    
    with open('templates/premium.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>PREMIUM STORE</h2><p>Your Balance: {"{{user.coins}}"}</p>{"{% for p in pkgs %}"}<div class="card"><h4>{"{{p.name}}"}</h4><p>{"{{p.days}}"} Days - {"{{p.price}}"} Coins</p><a href="/buy/{"{{p._id|string}}"}" class="btn">Buy Now</a></div>{"{% endfor %}"}' + nav + '</body></html>')

if __name__ == '__main__':
    create_templates()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
