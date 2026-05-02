import os
import asyncio
import base64
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events, Button
import uvicorn

# --- CONFIGURATION (আপনার দেওয়া ডাটা) ---
API_ID = 29904834
API_HASH = '8b4fd9ef578af114502feeafa2d31938'
BOT_TOKEN = '8655043839:AAGmoyWwzJFAi9hOovKNeySOp6UzrHBPibQ'
MONGO_URI = "mongodb+srv://drama:drama@cluster0.sa4kvgu.mongodb.net/?appName=Cluster0"
ADMIN_ID = 7120801813
ADMIN_WEB_PASS = "admin"
SECRET_KEY = "super-secret-key"

# --- APP & DB SETUP ---
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
client = AsyncIOMotorClient(MONGO_URI)
db = client['FinalMovieDB']
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- BOT LOGIC (MOVIE UPLOAD) ---
upload_states = {}

@bot.on(events.NewMessage(pattern='/movie'))
async def start_movie(event):
    if event.sender_id != ADMIN_ID:
        return await event.reply("❌ আপনি এডমিন নন!")
    upload_states[event.sender_id] = {"step": "name", "episodes": []}
    await event.reply("🎬 মুভির নাম লিখুন:")

@bot.on(events.NewMessage)
async def handle_inputs(event):
    uid = event.sender_id
    if uid not in upload_states: return
    state = upload_states[uid]

    if state["step"] == "name":
        state["name"] = event.text
        state["step"] = "poster"
        await event.reply("🖼 মুভির পোস্টার ফটোটি পাঠান (এটি অটো URL হয়ে যাবে):")
    
    elif state["step"] == "poster" and event.photo:
        path = await event.download_media()
        with open(path, "rb") as f:
            state["poster_url"] = f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
        os.remove(path)
        state["step"] = "episodes"
        await event.reply("📎 এবার এক এক করে এপিসোড ফাইল দিন। শেষ হলে 'Done' ক্লিক করুন।", 
                         buttons=[Button.inline("✅ Done", b"finish")])

    elif state["step"] == "episodes" and event.file:
        state["episodes"].append({"fid": event.file.id, "name": f"Episode {len(state['episodes'])+1}"})
        await event.reply(f"✅ {len(state['episodes'])} টি এপিসোড যুক্ত হয়েছে।")

@bot.on(events.CallbackQuery(data=b"finish"))
async def save_movie(event):
    uid = event.sender_id
    if uid in upload_states:
        data = upload_states[uid]
        await db.movies.insert_one({
            "title": data["name"], "poster": data["poster_url"], 
            "episodes": data["episodes"], "date": datetime.now()
        })
        del upload_states[uid]
        await event.edit("🚀 মুভিটি সফলভাবে সাইটে আপলোড হয়েছে!")

# --- WEB UI SYSTEM ---
def layout(content):
    return f"""
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-gray-900 text-white min-h-screen">
        <nav class="bg-gray-800 p-4 flex justify-around border-b border-gray-700 sticky top-0 z-50">
            <a href="/home">🏠 হোম</a> <a href="/tasks">💰 টাস্ক</a> <a href="/premium">💎 প্রিমিয়াম</a> <a href="/profile">👤 প্রোফাইল</a>
        </nav>
        <div class="container mx-auto p-4">{content}</div>
    </body></html>"""

# --- AUTH ROUTES ---
@app.get("/")
async def index(): return RedirectResponse("/login")

@app.get("/register", response_class=HTMLResponse)
async def reg_ui():
    return layout("""
    <div class="max-w-md mx-auto bg-gray-800 p-6 rounded shadow-lg mt-10">
        <h2 class="text-2xl font-bold mb-4">রেজিস্ট্রেশন</h2>
        <form action="/register" method="post" class="space-y-4">
            <input name="f" placeholder="First Name" class="w-full p-2 bg-gray-700 rounded" required>
            <input name="l" placeholder="Last Name" class="w-full p-2 bg-gray-700 rounded" required>
            <input name="m" placeholder="Mobile Number" class="w-full p-2 bg-gray-700 rounded" required>
            <input name="p" type="password" placeholder="Password" class="w-full p-2 bg-gray-700 rounded" required>
            <button class="w-full bg-green-600 p-2 rounded">Register</button>
        </form>
    </div>""")

@app.post("/register")
async def register(f:str=Form(...), l:str=Form(...), m:str=Form(...), p:str=Form(...)):
    if await db.users.find_one({"mobile": m}): return "Mobile exists!"
    await db.users.insert_one({"name": f"{f} {l}", "mobile": m, "password": p, "coins": 0, "premium": None})
    return RedirectResponse("/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_ui():
    return layout('<div class="max-w-md mx-auto bg-gray-800 p-6 mt-10 rounded shadow-lg"><h2 class="text-2xl font-bold mb-4 text-center">লগইন</h2><form action="/login" method="post" class="space-y-4"><input name="m" placeholder="Mobile" class="w-full p-2 bg-gray-700 rounded" required><input name="p" type="password" placeholder="Password" class="w-full p-2 bg-gray-700 rounded" required><button class="w-full bg-blue-600 p-2 rounded font-bold">Login</button></form></div>')

@app.post("/login")
async def login(request: Request, m:str=Form(...), p:str=Form(...)):
    u = await db.users.find_one({"mobile": m, "password": p})
    if u:
        request.session["uid"] = str(u["_id"])
        return RedirectResponse("/home", status_code=303)
    return "Invalid Mobile or Password"

# --- HOME & PAGINATION ---
@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, page: int = 1):
    if "uid" not in request.session: return RedirectResponse("/login")
    limit = 30
    skip = (page-1)*limit
    movies = await db.movies.find().sort("date", -1).skip(skip).limit(limit).to_list(length=limit)
    
    cards = '<div class="grid grid-cols-2 md:grid-cols-5 gap-4">'
    for m in movies:
        cards += f"""<div class="bg-gray-800 p-2 rounded shadow-lg"><img src="{m['poster']}" class="w-full h-40 object-cover rounded">
        <p class="mt-2 text-sm truncate font-bold">{m['title']}</p><a href="/movie/{m['_id']}" class="block bg-blue-600 text-center text-xs py-1 mt-2 rounded">Watch Now</a></div>"""
    cards += '</div>'
    
    nav = f'<div class="flex justify-center mt-10 space-x-4"><a href="/home?page={max(1, page-1)}" class="bg-gray-700 px-4 py-2 rounded">Preview</a>'
    nav += f'<span class="py-2">Page {page}</span><a href="/home?page={page+1}" class="bg-gray-700 px-4 py-2 rounded">Next</a></div>'
    return layout(cards + nav)

@app.get("/movie/{mid}", response_class=HTMLResponse)
async def movie_detail(request: Request, mid: str):
    m = await db.movies.find_one({"_id": ObjectId(mid)})
    u = await db.users.find_one({"_id": ObjectId(request.session["uid"])})
    ads = await db.settings.find_one({"type": "ads"}) or {"ads_id": "#", "zone_id": "#"}
    
    premium = u.get("premium") and u["premium"] > datetime.now()
    ad_url = f"https://{ads['ads_id']}.com/{ads['zone_id']}"
    
    eps = ""
    for i, ep in enumerate(m["episodes"]):
        link = f"/play/{mid}/{i}" if premium else ad_url
        target = "" if premium else 'target="_blank"'
        eps += f'<a href="{link}" {target} class="block bg-gray-800 p-4 mb-2 rounded border-l-4 border-blue-500 hover:bg-gray-700 transition">{ep["name"]}</a>'
    
    return layout(f'<img src="{m["poster"]}" class="w-full h-64 object-cover rounded-xl mb-4"><h1 class="text-3xl font-bold mb-6">{m["title"]}</h1>{eps}')

# --- TASK SYSTEM ---
@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    u = await db.users.find_one({"_id": ObjectId(request.session["uid"])})
    ts = await db.tasks.find().to_list(length=100)
    
    html = f'<div class="bg-blue-900 p-4 rounded text-center mb-6 font-bold">Balance: {u["coins"]} Coins</div>'
    for t in ts:
        if t["type"] == "monetag":
            btn = f'<button onclick="doAd(\'{t["link"]}\', \'{t["_id"]}\')" class="bg-red-600 px-4 py-1 rounded">Watch Ad</button>'
        else:
            btn = f'<a href="{t["link"]}" onclick="setTimeout(()=>{{location.href=\'/complete/{t["_id"]}\'}}, 8000)" target="_blank" class="bg-green-600 px-4 py-1 rounded text-sm">Visit Link</a>'
        html += f'<div class="bg-gray-800 p-4 flex justify-between items-center mb-2 rounded"><span>{t["name"]} ({t["coins"]} Coins)</span>{btn}</div>'
    
    html += "<script>function doAd(url, id){ window.open(url, '_blank'); setTimeout(()=>{location.href='/complete/'+id}, 10000); }</script>"
    return layout(html)

@app.get("/complete/{tid}")
async def complete(request: Request, tid: str):
    t = await db.tasks.find_one({"_id": ObjectId(tid)})
    await db.users.update_one({"_id": ObjectId(request.session["uid"])}, {"$inc": {"coins": int(t["coins"])}})
    return RedirectResponse("/tasks")

# --- PROFILE & PREMIUM ---
@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    u = await db.users.find_one({"_id": ObjectId(request.session["uid"])})
    return layout(f"""
    <div class="max-w-md mx-auto bg-gray-800 p-6 rounded shadow-lg mt-10">
        <h2 class="text-2xl font-bold mb-6">Profile</h2>
        <form action="/profile/update" method="post" class="space-y-4">
            <div><label>Full Name</label><input name="n" value="{u['name']}" class="w-full p-2 bg-gray-700 rounded"></div>
            <div><label>Mobile Number</label><input value="{u['mobile']}" class="w-full p-2 bg-gray-900 rounded" disabled></div>
            <div><label>New Password</label><input name="p" type="password" placeholder="New Password" class="w-full p-2 bg-gray-700 rounded"></div>
            <p class="text-yellow-500 font-bold">Balance: {u['coins']} Coins</p>
            <button class="w-full bg-orange-600 p-2 rounded font-bold">Update Profile</button>
        </form>
        <a href="/logout" class="block text-center mt-6 text-red-500 font-bold">Logout</a>
    </div>""")

@app.post("/profile/update")
async def update_profile(request: Request, n:str=Form(...), p:str=Form(None)):
    update = {"name": n}
    if p: update["password"] = p
    await db.users.update_one({"_id": ObjectId(request.session["uid"])}, {"$set": update})
    return RedirectResponse("/profile")

@app.get("/premium", response_class=HTMLResponse)
async def premium_ui(request: Request):
    pkgs = await db.packages.find().to_list(length=100)
    html = '<div class="grid grid-cols-1 gap-4">'
    for p in pkgs:
        html += f'<div class="bg-gray-800 p-6 rounded flex justify-between items-center border border-yellow-600"><div><p class="text-xl font-bold">{p["days"]} Days Pack</p><p>{p["price"]} Coins</p></div><a href="/buy/{p["_id"]}" class="bg-yellow-600 text-black px-6 py-2 rounded font-bold">Buy</a></div>'
    return layout(f'<h2 class="text-2xl font-bold mb-6">💎 প্রিমিয়াম কিনুন</h2>{html or "প্যাকেজ নেই"}')

@app.get("/buy/{pid}")
async def buy_pkg(request: Request, pid: str):
    u = await db.users.find_one({"_id": ObjectId(request.session["uid"])})
    p = await db.packages.find_one({"_id": ObjectId(pid)})
    if u["coins"] >= int(p["price"]):
        exp = datetime.now() + timedelta(days=int(p["days"]))
        await db.users.update_one({"_id": u["_id"]}, {"$inc": {"coins": -int(p["price"])}, "$set": {"premium": exp}})
        return RedirectResponse("/profile")
    return "Insufficient Balance!"

# --- ADMIN PANEL ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_log():
    return layout('<div class="max-w-sm mx-auto mt-20"><form action="/admin" method="post" class="bg-gray-800 p-6 rounded shadow-xl"><h2 class="mb-4 font-bold">Admin Login</h2><input name="pw" type="password" class="w-full p-2 bg-gray-700 rounded mb-4" required><button class="bg-red-600 w-full p-2 rounded">Login</button></form></div>')

@app.post("/admin")
async def admin_auth(request: Request, pw: str = Form(...)):
    if pw == ADMIN_WEB_PASS:
        request.session["admin"] = True
        return RedirectResponse("/admin/dashboard")
    return "Access Denied"

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not request.session.get("admin"): return "Unauthorized"
    return layout("""
    <h2 class="text-2xl font-bold mb-6">Admin Panel</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-gray-800 p-4 rounded shadow-xl">
            <h3 class="font-bold mb-4">Ad Settings</h3>
            <form action="/admin/set-ads" method="post" class="space-y-4">
                <input name="aid" placeholder="Ad Link/ID" class="w-full p-2 bg-gray-700">
                <input name="zid" placeholder="Zone ID" class="w-full p-2 bg-gray-700">
                <button class="bg-blue-600 w-full p-2 rounded">Save Ads Data</button>
            </form>
        </div>
        <div class="bg-gray-800 p-4 rounded shadow-xl">
            <h3 class="font-bold mb-4">Add Task</h3>
            <form action="/admin/add-task" method="post" class="space-y-2">
                <input name="n" placeholder="Task Name" class="w-full p-2 bg-gray-700">
                <select name="t" class="w-full p-2 bg-gray-700"><option value="direct">Direct</option><option value="monetag">Monetag</option></select>
                <input name="l" placeholder="Link/Script" class="w-full p-2 bg-gray-700">
                <input name="c" placeholder="Coins" class="w-full p-2 bg-gray-700">
                <button class="bg-green-600 w-full p-2 rounded">Add Task</button>
            </form>
        </div>
        <div class="bg-gray-800 p-4 rounded shadow-xl">
            <h3 class="font-bold mb-4">Add Package</h3>
            <form action="/admin/add-pkg" method="post" class="space-y-2">
                <input name="d" placeholder="Validity Days" class="w-full p-2 bg-gray-700">
                <input name="p" placeholder="Price (Coins)" class="w-full p-2 bg-gray-700">
                <button class="bg-yellow-600 text-black w-full p-2 rounded font-bold">Add Package</button>
            </form>
        </div>
    </div>
    """)

@app.post("/admin/set-ads")
async def set_ads(aid:str=Form(...), zid:str=Form(...)):
    await db.settings.update_one({"type":"ads"}, {"$set":{"ads_id":aid, "zone_id":zid}}, upsert=True)
    return RedirectResponse("/admin/dashboard", status_code=303)

@app.post("/admin/add-task")
async def add_task(n:str=Form(...), t:str=Form(...), l:str=Form(...), c:str=Form(...)):
    await db.tasks.insert_one({"name":n, "type":t, "link":l, "coins":c})
    return RedirectResponse("/admin/dashboard", status_code=303)

@app.post("/admin/add-pkg")
async def add_pkg(d:str=Form(...), p:str=Form(...)):
    await db.packages.insert_one({"days":d, "price":p})
    return RedirectResponse("/admin/dashboard", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

# --- SERVER START ---
if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: bot.run_until_disconnected(), daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
