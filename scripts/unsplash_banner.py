#!/usr/bin/env python3
"""Unsplash Banner Generator for UlasanTekno Blog."""

import requests, os, sys, random
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

ACCESS_KEY = "Jv9Yi0kWHA9MFfbywqwZQ3r4qTm697qUUHglctoBunk"
W, H = 1200, 675
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets/images/posts")

KEYWORDS = {
    "Gadget": {
        "Smartphone": "smartphone",
        "HP": "smartphone",
        "Tablet": "tablet ipad",
        "Laptop": "laptop computer",
        "Charger": "charger cable",
        "Powerbank": "power bank battery",
        "Smartwatch": "smart watch wearable",
        "Accessories": "gadget accessories tech",
        "default": "gadget technology"
    },
    "Audio": {
        "TWS": "wireless earbuds",
        "Earphone": "earphones",
        "Headset": "headphones",
        "Speaker": "bluetooth speaker",
        "default": "headphones audio"
    },
    "Smart Home": {
        "Smart TV": "smart tv television",
        "TV": "television screen",
        "Fridge": "refrigerator kitchen",
        "Kulkas": "refrigerator",
        "AC": "air conditioner",
        "Vacuum": "robot vacuum cleaner",
        "default": "smart home device"
    },
    "Lifestyle": {
        "Tripod": "camera tripod",
        "Keyboard": "mechanical keyboard",
        "Mouse": "wireless mouse",
        "default": "lifestyle gadget"
    },
    "Beauty Tech": {
        "Hair Dryer": "hair dryer",
        "Skincare": "skincare device",
        "default": "beauty technology"
    },
    "Gaming": {
        "Controller": "game controller",
        "Mouse": "gaming mouse",
        "Keyboard": "gaming keyboard",
        "default": "gaming setup"
    },
    "default": "technology"
}

def extract_keyword_from_title(title, subcategory, category):
    """Extract best Unsplash search keyword from title."""
    title_lower = title.lower()
    
    # Priority: exact subcategory match
    cat_map = KEYWORDS.get(category, KEYWORDS["default"])
    if isinstance(cat_map, dict):
        for key, val in cat_map.items():
            if key != "default" and key.lower() in title_lower:
                return val
        # Fallback to subcategory if provided
        if subcategory and subcategory != "default":
            for key, val in cat_map.items():
                if key.lower() in subcategory.lower():
                    return val
        return cat_map.get("default", "technology")
    return cat_map

def extract_keyword_from_title_legacy(title):
    """Legacy fallback: extract keyword directly from title words."""
    keyword_map = {
        "powerbank": "power bank battery",
        "charger": "charger cable usb",
        "smartphone": "smartphone mobile",
        "hp": "smartphone mobile",
        "laptop": "laptop computer",
        "tablet": "tablet ipad device",
        "tws": "wireless earbuds",
        "earphone": "earphones audio",
        "headset": "headphones",
        "smartwatch": "smart watch wearable",
        "smart tv": "smart tv television",
        "fridge": "refrigerator kitchen",
        "microphone": "microphone podcast",
        "keyboard": "mechanical keyboard",
        "mouse": "wireless mouse",
        "speaker": "bluetooth speaker",
        "tripod": "camera tripod",
        "accessories": "gadget accessories",
    }
    title_lower = title.lower()
    for key, val in keyword_map.items():
        if key in title_lower:
            return val
    return "technology"

def search(q, n=10):
    r = requests.get("https://api.unsplash.com/search/photos", 
                     params={"query": q, "per_page": n, "orientation": "landscape"},
                     headers={"Authorization": f"Client-ID {ACCESS_KEY}"}, timeout=10)
    return r.json().get("results", []) if r.ok else []

def pick_random_result(results):
    """Randomly pick one result, preferring different images."""
    if not results:
        return None
    return random.choice(results)

def dl(url):
    r = requests.get(url, timeout=15)
    if r.ok:
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.thumbnail((1400, 800), Image.LANCZOS)
        return img
    return None

def make(img, title, cat, out):
    bg = img.copy()
    ratio = bg.width / bg.height
    if ratio > W/H:
        w = int(bg.height * W/H)
        bg = bg.crop(((bg.width-w)//2, 0, (bg.width+w)//2, bg.height))
    else:
        h = int(bg.width * H/W)
        bg = bg.crop((0, (bg.height-h)//2, bg.width, (bg.height+h)//2))
    bg = bg.resize((W, H), Image.LANCZOS)
    
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 120))
    bg = bg.convert("RGBA")
    banner = Image.alpha_composite(bg, overlay).convert("RGB")
    draw = ImageDraw.Draw(banner)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        sfont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
    except:
        font = sfont = ImageFont.load_default()
    
    # Category badge
    draw.rounded_rectangle([(50, 50), (250, 90)], radius=5, fill=(255, 87, 34))
    draw.text((60, 55), cat.upper(), fill="white", font=sfont)
    
    # Title
    y = H - 150
    words = title.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textbbox((0,0), test, font=font)[2] <= W-100:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    for i, l in enumerate(lines[:2]):
        draw.text((50, y + i*60), l, fill="white", font=font)
    
    banner.save(out, "JPEG", quality=90)
    return out

if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else "test"
    name = sys.argv[2] if len(sys.argv) > 2 else "Test Product"
    cat = sys.argv[3] if len(sys.argv) > 3 else "Gadget"
    sub = sys.argv[4] if len(sys.argv) > 4 else "default"
    
    # Extract keyword based on title, subcategory, and category
    kw = extract_keyword_from_title(name, sub, cat)
    print(f"🔍 Unsplash search keyword: {kw}", file=sys.stderr)
    
    results = search(kw)
    if not results:
        # Try legacy fallback
        kw2 = extract_keyword_from_title_legacy(name)
        print(f"🔍 Fallback keyword: {kw2}", file=sys.stderr)
        results = search(kw2)
    if not results:
        # Last resort: category + technology
        results = search(f"{cat} technology")
    if results:
        chosen = pick_random_result(results)
        if chosen:
            img = dl(chosen["urls"]["regular"])
            if img:
                os.makedirs(OUT, exist_ok=True)
                path = os.path.join(OUT, f"{pid}-banner.jpg")
                print(make(img, name, cat, path))
