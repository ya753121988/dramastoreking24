import os
import asyncio
import base64
import json
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events, Button
import uvicorn

# --- কনফিগারেশন (এগুলো আপনার নিজের তথ্য দিয়ে পরিবর্তন করুন) ---
API_ID = 29904834  # আপনার Telegram API ID
API_HASH = '8b4fd9ef578af114502feeafa2d31938' # আপনার Telegram API Hash
BOT_TOKEN = '8655043839:AAGmoyWwzJFAi9hOovKNeySOp6UzrHBPibQ' # আপনার Bot Token
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0" # মংগোডিবি ইউআরআই
ADMIN_ID = 7120801813 # আপনার টেলিগ্রাম ইউজার আইডি
ADMIN_PASSWORD = "admin" # এডমিন প্যানেল পাসওয়ার্ড
SECRET_KEY = "super-secret-key" # সেশন সিকিউরিটি

# --- অ্যাপ এবং ডাটাবেস সেটআপ ---
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
client = AsyncIOMotorClient(MONGO_URI)
db = client['MovieAppDB']

# টেলিগ্রাম ক্লায়েন্ট
tg_bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- বটের কাজ (Movie Upload System) ---
user_states = {}

@tg_bot.on(events.NewMessage(pattern='/movie'))
async def start_movie_upload(event):
    if event.sender_id != ADMIN_ID:
        return await event.reply("❌ আপনি এডমিন নন!")
    
    user_states[event.sender_id] = {'step': 'name', 'episodes': []}
    await event.reply("🎬 মুভির নাম লিখুন:")

@tg_bot.on(events.NewMessage)
async def handle_upload(event):
    state = user_states.get(event.sender_id)
    if not state: return

    if state['step'] == 'name':
        state['name'] = event.text
        state['step'] = 'poster'
        await event.reply("🖼 মুভির পোস্টার (Direct Photo) দিন:")
    
    elif state['step'] == 'poster':
        if event.photo:
            path = await event.download_media(display_progress=False)
            with open(path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            state['poster_url'] = f"data:image/jpeg;base64,{encoded_string}"
            os.remove(path)
            state['step'] = 'episodes'
            await event.reply("📎 এবার এক এক করে এপিসোড ফাইল দিন। সব দেয়া শেষ হলে নিচের 'DONE' বাটনে ক্লিক করুন।", 
                             buttons=[Button.inline("✅ DONE", b"done_upload")])
        else:
            await event.reply("পিকচার দিন!")

    elif state['step'] == 'episodes':
        if event.file:
            # এখানে টেলিগ্রাম ফাইল আইডি স্টোর করা হচ্ছে
            state['episodes'].append({
                "name": f"Episode {len(state['episodes']) + 1}",
                "file_id": event.file.id
            })
            await event.reply(f"✅ এপিসোড {len(state['episodes'])} যুক্ত হয়েছে। আরো দিন অথবা DONE চাপুন।")

@tg_bot.on(events.CallbackQuery(data=b"done_upload"))
async def finish_upload(event):
    state = user_states.get(event.sender_id)
    if state:
        movie_data = {
            "title": state['name'],
            "poster": state['poster_url'],
            "episodes": state['episodes'],
            "created_at": datetime.now()
        }
        await db.movies.insert_one(movie_data)
        del user_states[event.sender_id]
        await event.edit("🚀 মুভিটি সফলভাবে সাইটে আপলোড করা হয়েছে!")

# --- ওয়েবসাইট সেকশন ---

# কমন সিএসএস এবং ডিজাইন (Tailwind CSS)
def get_layout(content, user=None):
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Movie Stream</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{ background-color: #0f172a; color: white; }}
            .nav-link {{ padding: 10px; color: #cbd5e1; }}
            .card {{ background: #1e293b; border-radius: 10px; overflow: hidden; }}
        </style>
    </head>
    <body>
        <nav class="bg-gray-900 p-4 flex justify-around border-b border-gray-700">
            <a href="/home" class="nav-link">🏠 Home</a>
            <a href="/tasks" class="nav-link">💰 Tasks</a>
            <a href="/premium" class="nav-link">💎 Premium</a>
            <a href="/profile" class="nav-link">👤 Profile</a>
        </nav>
        <div class="container mx-auto p-4 mb-20">
            {content}
        </div>
    </body>
    </html>
    """

# --- রুটস ---

@app.get("/")
async def root(request: Request):
    if "user" in request.session: return RedirectResponse("/home")
    return HTMLResponse(content=f"""
    <div class="max-w-md mx-auto mt-20 bg-gray-800 p-8 rounded-lg">
        <h2 class="text-2xl font-bold mb-4 text-center">Login</h2>
        <form action="/login" method="post" class="space-y-4">
            <input name="mobile" placeholder="Mobile Number" class="w-full p-2 rounded bg-gray-700 border-none text-white" required>
            <input name="password" type="password" placeholder="Password" class="w-full p-2 rounded bg-gray-700 border-none text-white" required>
            <button class="w-full bg-blue-600 p-2 rounded font-bold">Login</button>
        </form>
        <p class="mt-4 text-center">Don't have an account? <a href="/register" class="text-blue-400">Register</a></p>
    </div>
    """, status_code=200)

@app.get("/register")
async def register_page():
    return HTMLResponse(content=f"""
    <div class="max-w-md mx-auto mt-20 bg-gray-800 p-8 rounded-lg">
        <h2 class="text-2xl font-bold mb-4 text-center">Create Account</h2>
        <form action="/register" method="post" class="space-y-4">
            <input name="fname" placeholder="First Name" class="w-full p-2 rounded bg-gray-700 text-white" required>
            <input name="lname" placeholder="Last Name" class="w-full p-2 rounded bg-gray-700 text-white" required>
            <input name="mobile" placeholder="Mobile Number" class="w-full p-2 rounded bg-gray-700 text-white" required>
            <input name="password" type="password" placeholder="Password" class="w-full p-2 rounded bg-gray-700 text-white" required>
            <button class="w-full bg-green-600 p-2 rounded font-bold">Register</button>
        </form>
    </div>
    """)

@app.post("/register")
async def register(fname:str=Form(...), lname:str=Form(...), mobile:str=Form(...), password:str=Form(...)):
    user = await db.users.find_one({"mobile": mobile})
    if user: return "Mobile already exists!"
    await db.users.insert_one({
        "name": f"{fname} {lname}", "mobile": mobile, "password": password,
        "coins": 0, "premium_until": None, "role": "user"
    })
    return RedirectResponse("/", status_code=303)

@app.post("/login")
async def login(request: Request, mobile:str=Form(...), password:str=Form(...)):
    user = await db.users.find_one({"mobile": mobile, "password": password})
    if user:
        request.session["user"] = mobile
        return RedirectResponse("/home", status_code=303)
    return "Invalid Credentials"

@app.get("/home")
async def home(request: Request, page: int = 1):
    if "user" not in request.session: return RedirectResponse("/")
    limit = 30
    skip = (page - 1) * limit
    movies_cursor = db.movies.find().sort("created_at", -1).skip(skip).limit(limit)
    movies = await movies_cursor.to_list(length=limit)
    
    movie_cards = ""
    for m in movies:
        movie_cards += f"""
        <div class="card shadow-lg">
            <img src="{m['poster']}" class="w-full h-64 object-cover">
            <div class="p-2">
                <h3 class="font-bold truncate">{m['title']}</h3>
                <a href="/movie/{m['_id']}" class="block mt-2 bg-blue-500 text-center py-1 rounded">Watch Now</a>
            </div>
        </div>
        """
    
    pagination = f"""
    <div class="flex justify-center space-x-4 mt-8">
        <a href="/home?page={max(1, page-1)}" class="bg-gray-700 px-4 py-2 rounded">Prev</a>
        <span class="py-2">Page {page}</span>
        <a href="/home?page={page+1}" class="bg-gray-700 px-4 py-2 rounded">Next</a>
    </div>
    """
    return HTMLResponse(get_layout(f"<div class='grid grid-cols-2 md:grid-cols-5 gap-4'>{movie_cards}</div>{pagination}"))

@app.get("/movie/{movie_id}")
async def movie_detail(request: Request, movie_id: str):
    if "user" not in request.session: return RedirectResponse("/")
    movie = await db.movies.find_one({"_id": ObjectId(movie_id)})
    user = await db.users.find_one({"mobile": request.session["user"]})
    settings = await db.settings.find_one({"type": "ads"}) or {"ads_id": "#", "zone_id": "#"}
    
    is_premium = user.get("premium_until") and user["premium_until"] > datetime.now()
    ad_url = f"https://{settings['ads_id']}.com/{settings['zone_id']}"
    
    ep_buttons = ""
    for i, ep in enumerate(movie['episodes']):
        link = f"/play/{movie_id}/{i}" if is_premium else ad_url
        target = "" if is_premium else 'target="_blank"'
        ep_buttons += f'<a href="{link}" {target} class="bg-gray-700 p-4 rounded-lg flex justify-between items-center hover:bg-gray-600 transition"><span>{ep["name"]}</span> <span>▶️</span></a>'

    content = f"""
    <div class="max-w-2xl mx-auto">
        <img src="{movie['poster']}" class="w-full rounded-xl shadow-2xl mb-6">
        <h1 class="text-3xl font-bold mb-4">{movie['title']}</h1>
        <div class="space-y-2">
            <h2 class="text-xl font-semibold mb-2">Episodes:</h2>
            <div class="grid grid-cols-1 gap-3">{ep_buttons}</div>
        </div>
    </div>
    """
    return HTMLResponse(get_layout(content))

# --- টাস্ক সিস্টেম ---
@app.get("/tasks")
async def tasks_page(request: Request):
    if "user" not in request.session: return RedirectResponse("/")
    tasks = await db.tasks.find().to_list(length=100)
    user = await db.users.find_one({"mobile": request.session["user"]})
    
    task_html = ""
    for t in tasks:
        btn_action = f"onclick=\"location.href='/complete-task/{t['_id']}'\""
        if t['type'] == 'monetag':
            btn_action = f"onclick=\"showMonetag('{t['script']}', '{t['_id']}')\""
            
        task_html += f"""
        <div class="bg-gray-800 p-4 rounded-lg flex justify-between items-center mb-3">
            <div>
                <p class="font-bold">{t['name']}</p>
                <p class="text-yellow-400 text-sm">{t['coins']} Coins</p>
            </div>
            <button {btn_action} class="bg-green-600 px-4 py-2 rounded">Complete</button>
        </div>
        """
    
    script = """
    <script>
    function showMonetag(scriptUrl, tid) {
        window.open(scriptUrl, '_blank');
        setTimeout(() => { location.href = '/complete-task/' + tid; }, 5000);
    }
    </script>
    """
    return HTMLResponse(get_layout(f"<h2 class='text-2xl mb-6'>Available Tasks</h2>{task_html}{script}"))

@app.get("/complete-task/{tid}")
async def complete_task(request: Request, tid: str):
    user_mobile = request.session.get("user")
    task = await db.tasks.find_one({"_id": ObjectId(tid)})
    if task:
        await db.users.update_one({"mobile": user_mobile}, {"$inc": {"coins": int(task['coins'])}})
    return RedirectResponse("/tasks")

# --- প্রোফাইল এবং প্রিমিয়াম ---
@app.get("/profile")
async def profile(request: Request):
    user = await db.users.find_one({"mobile": request.session["user"]})
    return HTMLResponse(get_layout(f"""
    <div class="max-w-md mx-auto bg-gray-800 p-6 rounded-lg">
        <h2 class="text-2xl font-bold mb-6 text-center">My Profile</h2>
        <form action="/update-profile" method="post" class="space-y-4">
            <div><label>Full Name</label><input name="name" value="{user['name']}" class="w-full p-2 bg-gray-700 rounded"></div>
            <div><label>Mobile</label><input value="{user['mobile']}" class="w-full p-2 bg-gray-900 rounded" disabled></div>
            <div><label>New Password</label><input name="password" type="password" placeholder="Leave blank to keep same" class="w-full p-2 bg-gray-700 rounded"></div>
            <div class="bg-blue-900 p-3 rounded">Current Balance: {user['coins']} Coins</div>
            <button class="w-full bg-orange-600 py-2 rounded">Update Profile</button>
        </form>
    </div>
    """))

@app.get("/premium")
async def premium_page(request: Request):
    user = await db.users.find_one({"mobile": request.session["user"]})
    packages = await db.packages.find().to_list(length=20)
    
    pkg_html = ""
    for p in packages:
        pkg_html += f"""
        <div class="bg-gray-800 p-6 rounded-xl border border-yellow-500 text-center">
            <h3 class="text-xl font-bold">{p['days']} Days</h3>
            <p class="text-3xl my-4">{p['price']} <span class="text-sm text-yellow-400">Coins</span></p>
            <a href="/buy-pkg/{p['_id']}" class="block bg-yellow-600 py-2 rounded-lg font-bold">Buy Now</a>
        </div>
        """
    return HTMLResponse(get_layout(f"<h2 class='text-2xl mb-6'>Premium Packages</h2><div class='grid grid-cols-1 md:grid-cols-3 gap-6'>{pkg_html}</div>"))

@app.get("/buy-pkg/{pid}")
async def buy_pkg(request: Request, pid: str):
    user = await db.users.find_one({"mobile": request.session["user"]})
    pkg = await db.packages.find_one({"_id": ObjectId(pid)})
    
    if user['coins'] >= int(pkg['price']):
        expiry = datetime.now() + timedelta(days=int(pkg['days']))
        await db.users.update_one({"mobile": user['mobile']}, {
            "$inc": {"coins": -int(pkg['price'])},
            "$set": {"premium_until": expiry}
        })
        return RedirectResponse("/profile")
    return "Insufficient Coins!"

# --- এডমিন প্যানেল ---
@app.get("/admin-login")
async def admin_login_page():
    return HTMLResponse(content="""
    <body class="bg-gray-900 text-white flex items-center justify-center h-screen">
        <form action="/admin-login" method="post" class="bg-gray-800 p-8 rounded shadow-lg">
            <h2 class="text-xl mb-4">Admin Access</h2>
            <input name="pass" type="password" placeholder="Admin Password" class="p-2 rounded bg-gray-700 block w-full mb-4">
            <button class="w-full bg-red-600 py-2 rounded">Login</button>
        </form>
    </body>""")

@app.post("/admin-login")
async def admin_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        request.session["admin"] = True
        return RedirectResponse("/admin/dashboard", status_code=303)
    return "Wrong Admin Password"

@app.get("/admin/dashboard")
async def admin_dashboard(request: Request):
    if not request.session.get("admin"): return RedirectResponse("/admin-login")
    
    # এডমিন প্যানেলের ডিজাইন ও মেনু
    return HTMLResponse(f"""
    {get_layout("<h1 class='text-3xl mb-8'>Admin Dashboard</h1>")}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 p-4">
        <div class="bg-gray-800 p-6 rounded">
            <h3 class="text-xl mb-4">Ads Settings</h3>
            <form action="/admin/save-ads" method="post">
                <input name="ads_id" placeholder="Monetag Ad ID" class="w-full p-2 mb-2 bg-gray-700">
                <input name="zone_id" placeholder="Zone ID" class="w-full p-2 mb-2 bg-gray-700">
                <button class="bg-blue-600 px-4 py-2 rounded">Save Changes</button>
            </form>
        </div>
        <div class="bg-gray-800 p-6 rounded">
            <h3 class="text-xl mb-4">Add Task</h3>
            <form action="/admin/add-task" method="post">
                <input name="name" placeholder="Task Name" class="w-full p-2 mb-2 bg-gray-700">
                <select name="type" class="w-full p-2 mb-2 bg-gray-700">
                    <option value="direct">Direct Link</option>
                    <option value="monetag">Monetag Task</option>
                </select>
                <input name="link" placeholder="Link or Script" class="w-full p-2 mb-2 bg-gray-700">
                <input name="coins" placeholder="Coin Reward" class="w-full p-2 mb-2 bg-gray-700">
                <button class="bg-green-600 px-4 py-2 rounded">Add Task</button>
            </form>
        </div>
        <div class="bg-gray-800 p-6 rounded">
            <h3 class="text-xl mb-4">Premium Packages</h3>
            <form action="/admin/add-pkg" method="post">
                <input name="days" placeholder="Validity (Days)" class="w-full p-2 mb-2 bg-gray-700">
                <input name="price" placeholder="Price (Coins)" class="w-full p-2 mb-2 bg-gray-700">
                <button class="bg-yellow-600 px-4 py-2 rounded text-black">Add Package</button>
            </form>
        </div>
    </div>
    """)

# এডমিন অ্যাকশন রুটস
@app.post("/admin/save-ads")
async def save_ads(ads_id: str = Form(...), zone_id: str = Form(...)):
    await db.settings.update_one({"type": "ads"}, {"$set": {"ads_id": ads_id, "zone_id": zone_id}}, upsert=True)
    return RedirectResponse("/admin/dashboard", status_code=303)

@app.post("/admin/add-task")
async def add_task(name:str=Form(...), type:str=Form(...), link:str=Form(...), coins:str=Form(...)):
    await db.tasks.insert_one({"name": name, "type": type, "script": link, "coins": coins})
    return RedirectResponse("/admin/dashboard", status_code=303)

@app.post("/admin/add-pkg")
async def add_pkg(days:str=Form(...), price:str=Form(...)):
    await db.packages.insert_one({"days": days, "price": price})
    return RedirectResponse("/admin/dashboard", status_code=303)

# --- সার্ভার রানার ---
if __name__ == "__main__":
    import threading
    # বট রান করার জন্য আলাদা থ্রেড
    def start_bot():
        tg_bot.run_until_disconnected()
    
    threading.Thread(target=start_bot, daemon=True).start()
    
    # উভি কর্ন সার্ভার
    uvicorn.run(app, host="0.0.0.0", port=8000)
