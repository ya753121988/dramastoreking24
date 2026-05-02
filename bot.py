import os
import telebot
import math
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId
from threading import Thread

# ==========================================
# [FEATURE #1] কনফিগারেশন এবং ডাটাবেস কানেকশন
# ==========================================
TOKEN = '8655043839:AAGmoyWwzJFAi9hOovKNeySOp6UzrHBPibQ' 
MONGO_URI = 'mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0' 
ADMIN_ID = 7120801813 # আপনার টেলিগ্রাম আইডি

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
app.secret_key = "movie_ultra_secure_99"

client = MongoClient(MONGO_URI)
db = client['movie_final_v20']
movies_col = db['movies']
settings_col = db['settings']
tasks_col = db['tasks']
users_col = db['users']
packages_col = db['packages']

# সেটিংস চেক এবং ডিফল্ট ডাটা ইনসার্ট
if not settings_col.find_one({"type": "config"}):
    settings_col.insert_one({"type": "config", "terazone_id": "8888", "ad_link": "https://example.com/ad"})

# ==========================================
# [FEATURE #3] অ্যাডমিন সিকিউরিটি
# ==========================================
user_states = {}

def is_admin(message):
    return message.from_user.id == ADMIN_ID

@bot.message_handler(commands=['admin'])
def admin_menu(message):
    if not is_admin(message): return
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Add Movie 🎬", "Add Task 📝")
    markup.add("Add Package 🎁", "Ad Settings ⚙️")
    markup.add("Delete Task ❌", "Delete Package 🗑️")
    bot.send_message(message.chat.id, "অ্যাডমিন মেনু:", reply_markup=markup)

# ==========================================
# [FEATURE #4-8] মুভি অ্যাড সিস্টেম
# ==========================================
@bot.message_handler(commands=['movie'])
@bot.message_handler(func=lambda m: m.text == "Add Movie 🎬")
def movie_start(message):
    if not is_admin(message): return
    user_states[message.chat.id] = {'step': 'name', 'data': {}}
    bot.send_message(message.chat.id, "মুভির নাম লিখুন:")

# এখানে 'message' এর বদলে 'm' ব্যবহার করা হয়েছে (FIXED)
@bot.message_handler(func=lambda m: m.chat.id in user_states, content_types=['text', 'photo', 'document'])
def movie_flow(message):
    state = user_states[message.chat.id]
    if state['step'] == 'name':
        state['data']['name'] = message.text
        state['step'] = 'poster'
        bot.send_message(message.chat.id, "মুভির পোস্টার (ছবি) পাঠান:")
    elif state['step'] == 'poster' and message.content_type == 'photo':
        fid = message.photo[-1].file_id
        finfo = bot.get_file(fid)
        state['data']['poster'] = f"https://api.telegram.org/file/bot{TOKEN}/{finfo.file_path}"
        state['step'] = 'episodes'
        state['data']['episodes'] = []
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True).add("Done ✅")
        bot.send_message(message.chat.id, "এখন একটির পর একটি ফাইল পাঠান। শেষ হলে 'Done ✅' দিন।", reply_markup=markup)
    elif state['step'] == 'episodes':
        if message.text == "Done ✅":
            movies_col.insert_one(state['data'])
            bot.send_message(message.chat.id, "মুভি সাইটে সফলভাবে আপলোড হয়েছে!", reply_markup=telebot.types.ReplyKeyboardRemove())
            del user_states[message.chat.id]
        elif message.document:
            state['data']['episodes'].append({'name': message.document.file_name, 'file_id': message.document.file_id})
            bot.send_message(message.chat.id, f"সংযুক্ত হয়েছে: {message.document.file_name}")

# ==========================================
# [FEATURE #9] অ্যাড সেটিংস
# ==========================================
@bot.message_handler(func=lambda m: m.text == "Ad Settings ⚙️")
def change_ads(message):
    if not is_admin(message): return
    msg = bot.send_message(message.chat.id, "Terazone ID এবং Ad Link দিন (স্পেস দিয়ে আলাদা করুন):")
    bot.register_next_step_handler(msg, save_ads)

def save_ads(message):
    try:
        tid, alink = message.text.split(' ')
        settings_col.update_one({"type": "config"}, {"$set": {"terazone_id": tid, "ad_link": alink}})
        bot.reply_to(message, "সেটিংস আপডেট হয়েছে!")
    except: bot.reply_to(message, "ভুল ফরম্যাট! Example: 1234 https://link.com")

# ==========================================
# [FEATURE #10-13] টাস্ক এবং প্যাকেজ ম্যানেজমেন্ট
# ==========================================
@bot.message_handler(func=lambda m: m.text == "Add Task 📝")
def add_task(message):
    if not is_admin(message): return
    msg = bot.send_message(message.chat.id, "টাস্ক ডাটা দিন: Type(direct/monetag) | Title | Content | Coins")
    bot.register_next_step_handler(msg, lambda m: save_item(m, tasks_col))

@bot.message_handler(func=lambda m: m.text == "Add Package 🎁")
def add_pkg(message):
    if not is_admin(message): return
    msg = bot.send_message(message.chat.id, "প্যাকেজ ডাটা দিন: Name | Days | Coins")
    bot.register_next_step_handler(msg, lambda m: save_item(m, packages_col))

def save_item(message, col):
    try:
        p = message.text.split('|')
        if col == tasks_col:
            col.insert_one({"type": p[0].strip(), "title": p[1].strip(), "content": p[2].strip(), "coins": int(p[3].strip())})
        else:
            col.insert_one({"name": p[0].strip(), "days": int(p[1].strip()), "price": int(p[2].strip())})
        bot.reply_to(message, "সফলভাবে সেভ হয়েছে!")
    except: bot.reply_to(message, "ভুল ফরম্যাট!")

@bot.message_handler(func=lambda m: m.text in ["Delete Task ❌", "Delete Package 🗑️"])
def delete_list(message):
    if not is_admin(message): return
    col = tasks_col if "Task" in message.text else packages_col
    for item in col.find():
        btn = telebot.types.InlineKeyboardMarkup().add(telebot.types.InlineKeyboardButton("Delete", callback_data=f"del_{'t' if col==tasks_col else 'p'}_{item['_id']}"))
        bot.send_message(message.chat.id, f"Item: {item.get('title') or item.get('name')}", reply_markup=btn)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def handle_del(call):
    _, type, oid = call.data.split('_')
    (tasks_col if type=='t' else packages_col).delete_one({"_id": ObjectId(oid)})
    bot.answer_callback_query(call.id, "Deleted!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ==========================================
# [FEATURE #14-15] সাইনআপ এবং লগইন
# ==========================================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        if users_col.find_one({"mobile": request.form['mobile']}): return "Mobile already registered!"
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
        return "Invalid credentials!"
    return render_template('login.html')

# ==========================================
# [FEATURE #16-17] হোম পেজ ও পেজিনেশন
# ==========================================
@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    page = int(request.args.get('page', 1))
    limit = 30
    skip = (page - 1) * limit
    total = movies_col.count_documents({})
    movies = movies_col.find().sort('_id', DESCENDING).skip(skip).limit(limit)
    return render_template('index.html', movies=movies, page=page, total_pages=max(1, math.ceil(total/limit)))

# ==========================================
# [FEATURE #18] প্রোফাইল
# ==========================================
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    u = users_col.find_one({"_id": ObjectId(session['user_id'])})
    if request.method == 'POST':
        users_col.update_one({"_id": u['_id']}, {"$set": {"fname": request.form['fname'], "password": request.form['password']}})
        return redirect(url_for('profile'))
    return render_template('profile.html', user=u)

# ==========================================
# [FEATURE #19] টাস্ক সিস্টেম
# ==========================================
@app.route('/tasks')
def tasks_page():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('tasks.html', tasks=tasks_col.find())

@app.route('/claim/<tid>')
def claim_coin(tid):
    if 'user_id' not in session: return redirect(url_for('login'))
    t = tasks_col.find_one({"_id": ObjectId(tid)})
    if t:
        users_col.update_one({"_id": ObjectId(session['user_id'])}, {"$inc": {"coins": t['coins']}})
    return redirect(url_for('tasks_page'))

# ==========================================
# [FEATURE #20] প্রিমিয়াম বাই
# ==========================================
@app.route('/premium')
def premium_store():
    if 'user_id' not in session: return redirect(url_for('login'))
    u = users_col.find_one({"_id": ObjectId(session['user_id'])})
    return render_template('premium.html', pkgs=packages_col.find(), user=u)

@app.route('/buy/<pid>')
def buy_pkg(pid):
    if 'user_id' not in session: return redirect(url_for('login'))
    p = packages_col.find_one({"_id": ObjectId(pid)})
    u = users_col.find_one({"_id": ObjectId(session['user_id'])})
    if u and p and u['coins'] >= p['price']:
        expiry = datetime.now() + timedelta(days=p['days'])
        users_col.update_one({"_id": u['_id']}, {"$inc": {"coins": -p['price']}, "$set": {"premium_until": expiry}})
        return redirect(url_for('profile'))
    return "Not enough coins!"

@app.route('/movie/<id>')
def movie_details(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    m = movies_col.find_one({"_id": ObjectId(id)})
    c = settings_col.find_one({"type": "config"})
    u = users_col.find_one({"_id": ObjectId(session['user_id'])})
    
    # FIXED: None টাইপ চেক (Internal Server Error ফিক্স)
    is_premium = False
    if u.get('premium_until'):
        if u['premium_until'] > datetime.now():
            is_premium = True
            
    return render_template('details.html', movie=m, config=c, is_premium=is_premium)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- টেমপ্লেট জেনারেটর (UI) ---
def create_templates():
    if not os.path.exists('templates'): os.makedirs('templates')
    css = "<style>body{background:#000;color:#fff;font-family:sans-serif;text-align:center;margin:0;padding-bottom:80px}.nav{background:#111;position:fixed;bottom:0;width:100%;display:flex;justify-content:space-around;padding:15px;border-top:1px solid gold}.nav a{color:gold;text-decoration:none;font-size:12px;font-weight:bold}.card{background:#1a1a1a;margin:10px;padding:10px;border-radius:10px;border:1px solid #333}.btn{display:block;background:gold;color:#000;padding:12px;margin:10px auto;text-decoration:none;border-radius:5px;width:85%;font-weight:bold;border:none}.inp{width:85%;padding:12px;margin:10px;border-radius:5px;border:none;background:#222;color:#fff}img{max-height:300px;object-fit:cover;border-radius:10px}</style>"
    nav = '<div class="nav"><a href="/">হোম</a><a href="/tasks">টাস্ক</a><a href="/premium">প্রিমিয়াম</a><a href="/profile">প্রোফাইল</a></div>'

    with open('templates/signup.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>রেজিস্ট্রেশন</h2><form method="POST"><input name="fname" placeholder="First Name" class="inp" required><input name="lname" placeholder="Last Name" class="inp" required><input name="mobile" placeholder="Mobile" class="inp" required><input name="password" type="password" placeholder="Password" class="inp" required><button class="btn">Register</button></form><a href="/login" style="color:white">Login</a></body></html>')
    
    with open('templates/login.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>লগইন</h2><form method="POST"><input name="mobile" placeholder="Mobile" class="inp" required><input name="password" type="password" placeholder="Password" class="inp" required><button class="btn">Login</button></form><a href="/signup" style="color:white">Signup</a></body></html>')

    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>Movies</h2><div style="display:grid;grid-template-columns:1fr 1fr">{"{% for m in movies %}"}<div class="card"><img src="{"{{m.poster}}"}" width="100%"><p>{"{{m.name}}"}</p><a href="/movie/{"{{m._id}}"}" class="btn">WATCH</a></div>{"{% endfor %}"}</div>' +
                '<div>{"{% if page > 1 %}"}<a href="/?page={"{{page-1}}"}" style="color:white">Prev</a>{"{% endif %}"} Page {"{{page}}"} {"{% if page < total_pages %}"}<a href="/?page={"{{page+1}}"}" style="color:white">Next</a>{"{% endif %}"}</div>' + nav + '</body></html>')

    with open('templates/details.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><img src="{"{{movie.poster}}"}" width="100%"><h2>{"{{movie.name}}"}</h2>' +
                '{"{% for ep in movie.episodes %}"}' +
                '{"{% if is_premium %}"}<a href="https://t.me/share/url?url=FILE_ID_{{"{{ep.file_id}}"}}" class="btn">{"{{ep.name}}"} (No Ads)</a>' +
                '{"{% else %}"}<a href="{{"{{config.ad_link}}"}}?zone={{"{{config.terazone_id}}"}}&file={{"{{ep.file_id}}"}}" class="btn">{"{{ep.name}}"} (Watch Ad)</a>{"{% endif %}"}' +
                '{"{% endfor %}"}' + nav + '</body></html>')

    with open('templates/profile.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>Profile</h2><div class="card"><p>Coins: {"{{user.coins}}"}</p><form method="POST"><input name="fname" value="{"{{user.fname}}"}" class="inp"><input name="password" value="{"{{user.password}}"}" class="inp"><button class="btn">Update</button></form><a href="/logout">Logout</a></div>' + nav + '</body></html>')
    
    with open('templates/tasks.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>Tasks</h2>{"{% for t in tasks %}"}<div class="card"><h4>{"{{t.title}}"}</h4>' +
                '{"{% if t.type == \'direct\' %}"}<a href="{{"{{t.content}}"}}" target="_blank" onclick="location.href=\'/claim/{{"{{t._id|string}}"}}\'" class="btn">Complete</a>' +
                '{"{% else %}"}<button onclick="eval(\'{{"{{t.content}}"}}\'); location.href=\'/claim/{{"{{t._id|string}}"}}\'" class="btn">Watch Ad</button>{"{% endif %}"}</div>{"{% endfor %}"}' + nav + '</body></html>')
    
    with open('templates/premium.html', 'w', encoding='utf-8') as f:
        f.write(f'<html>{css}<body><h2>Premium Store</h2><p>Balance: {"{{user.coins}}"}</p>{"{% for p in pkgs %}"}<div class="card"><h4>{"{{p.name}}"}</h4><p>{"{{p.days}}"} Days - {"{{p.price}}"} Coins</p><a href="/buy/{"{{p._id|string}}"}" class="btn">Buy Now</a></div>{"{% endfor %}"}' + nav + '</body></html>')

if __name__ == '__main__':
    create_templates()
    Thread(target=lambda: bot.polling(none_stop=True)).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
