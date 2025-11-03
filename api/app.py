import os, json, csv, random, re, requests
from flask import Flask, request, jsonify, render_template, make_response
from pathlib import Path
import openai

app = Flask(__name__)

########## COOKIE STORAGE ##########
def get_env_from_cookie(req):
    """Get stored API keys from cookies"""
    return {
        "OPENAI_API_KEY": req.cookies.get("OPENAI_API_KEY", ""),
        "GALLABOX_API_KEY": req.cookies.get("GALLABOX_API_KEY", ""),
        "GALLABOX_API_SECRET": req.cookies.get("GALLABOX_API_SECRET", ""),
        "GALLABOX_CHANNEL_ID": req.cookies.get("GALLABOX_CHANNEL_ID", "")
    }

########## SETUP PAGE ##########
@app.route("/", methods=["GET", "POST"])
def setup():
    """Ask user for API keys and store in cookies"""
    if request.method == "POST":
        data = request.form
        resp = make_response(render_template("setup.html", saved=True))
        for key in ["OPENAI_API_KEY", "GALLABOX_API_KEY", "GALLABOX_API_SECRET", "GALLABOX_CHANNEL_ID"]:
            resp.set_cookie(key, data.get(key, ""), max_age=60*60*24*7)  # valid 7 days
        return resp
    return render_template("setup.html", saved=False)

########## ZULU CLUB INFO ##########
ZULU_CLUB_INFO = """
We're building a new way to shop and discover lifestyle products online.

Introducing Zulu Club — your personalized lifestyle shopping experience, delivered right to your doorstep.

Browse and shop high-quality lifestyle products:
- Women's Fashion — dresses, tops, co-ords, winterwear, loungewear & more
- Men's Fashion — shirts, tees, jackets, athleisure & more
- Kids — clothing, toys, learning kits & accessories
- Footwear — sneakers, heels, flats, sandals & kids shoes
- Home Decor — showpieces, vases, lamps, aroma decor, premium home accessories
- Beauty & Self-Care — skincare, bodycare, fragrances & grooming essentials
- Fashion Accessories — bags, jewelry, watches, sunglasses & belts
- Lifestyle Gifting — curated gift sets & décor-based gifting

Your selection arrives in just 100 minutes. Try at home, keep what you love, return instantly.
Now live in Gurgaon — Visit zulu.club or our pop-ups at AIPL Joy Street & AIPL Central.
"""

########## CHATGPT RESPONSE ##########
def get_chatgpt_response(user_message, keys, conversation_history=None):
    if not keys["OPENAI_API_KEY"]:
        return "⚠️ Missing OpenAI API key. Please visit / to set it up."
    try:
        client = openai.OpenAI(api_key=keys["OPENAI_API_KEY"])
        messages = [
            {"role": "system", "content": f"You are a helpful Zulu Club assistant.\n{ZULU_CLUB_INFO}"},
            {"role": "user", "content": user_message}
        ]
        res = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("❌ ChatGPT Error:", e)
        return "Hi 👋 Welcome to Zulu Club — your premium lifestyle shopping experience with 100-minute delivery!"

########## CATEGORY LOGIC ##########
PRODUCTS_CSV = Path("products.csv")
_products, _categories, _category_index = [], set(), {}

def _canonicalize(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower().strip())) if text else ""

def _load_products():
    if not PRODUCTS_CSV.exists():
        print("⚠️ products.csv not found.")
        return
    with PRODUCTS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            name, category, price, img = r.get("name",""), r.get("category",""), r.get("price",""), r.get("image_url","")
            if not name or not category: continue
            if price and not price.startswith("₹"): price = f"₹{price}"
            _products.append({"name": name, "category": category, "price": price, "image_url": img})
    _categories.update(_canonicalize(p["category"]) for p in _products)
    for p in _products:
        key = _canonicalize(p["category"])
        _category_index.setdefault(key, []).append(p)
    print(f"✅ Loaded {len(_products)} products across {len(_categories)} categories.")
_load_products()

def get_random_products(cat, n=3):
    items = _category_index.get(cat, [])
    return random.sample(items, min(n, len(items))) if items else []

########## HANDLE MESSAGE ##########
def handle_message(msg, keys):
    msgl = msg.lower().strip()
    print(f"📩 Message received: {msg}")
    reply = get_chatgpt_response(msgl, keys)
    return {"type": "text", "content": reply}

########## GALLABOX WEBHOOK ##########
@app.route("/api/gallabox_webhook", methods=["POST"])
def gallabox_webhook():
    keys = get_env_from_cookie(request)
    if not all(keys.values()):
        return jsonify({"error": "Missing Gallabox or OpenAI keys. Visit / to configure."}), 400

    data = request.get_json(force=True)
    print("📩 Received Gallabox webhook:", data)
    phone = data.get("data", {}).get("from", "")
    user_message = data.get("data", {}).get("message", {}).get("text", "").strip() or "hi"

    reply_data = handle_message(user_message, keys)
    reply = reply_data["content"]

    try:
        r = requests.post(
            "https://backend.gallabox.com/api/v1/messages/whatsapp",
            headers={
                "Content-Type": "application/json",
                "x-api-key": keys["GALLABOX_API_KEY"],
                "x-api-secret": keys["GALLABOX_API_SECRET"]
            },
            json={
                "channelId": keys["GALLABOX_CHANNEL_ID"],
                "to": phone,
                "type": "text",
                "message": {"text": reply}
            }
        )
        print("📤 Gallabox Response:", r.status_code, r.text)
    except Exception as e:
        print("❌ Gallabox send error:", e)

    return jsonify({"status": "sent"}), 200

########## VERCEL ENTRY ##########
def handler(request):
    with app.request_context(request.environ):
        return app.full_dispatch_request()
