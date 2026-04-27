#!/usr/bin/env python3
"""
Cross-post artikel UlasanTekno ke Medium & Kompasiana untuk backlink SEO.
Usage:
  python3 scripts/cross-post.py _posts/2026-04-27-judul-artikel.md
  python3 scripts/cross-post.py          # auto: artikel terbaru
"""
import sys, os, re, json, urllib.request
from pathlib import Path
from datetime import datetime

REPO = Path(__file__).parent.parent
POSTS_DIR = REPO / "_posts"
CROSS_DIR = REPO / "cross-post"
CROSS_DIR.mkdir(exist_ok=True)

# Medium API token (optional — kalau mau auto-publish)
MEDIUM_TOKEN = os.environ.get("MEDIUM_API_TOKEN", "")


def latest_post():
    posts = sorted(POSTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return posts[0] if posts else None


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, parts[2]


def strip_affiliate_links(text):
    """Remove Jekyll affiliate syntax for cross-post."""
    # Remove {:target="_blank"}
    text = re.sub(r'\{:target=["\']_blank["\']\}', '', text)
    # Keep links but clean them
    return text


def to_medium_markdown(fm, body, url):
    """Format for Medium (Markdown)."""
    title = fm.get("title", "Untitled")
    tags = [fm.get("category", "Technology"), "Indonesia", "Review", "Gadget", "2026"]
    
    md = f"# {title}\n\n"
    md += f"_Originally published on [UlasanTekno]({url})_\n\n"
    md += strip_affiliate_links(body)
    md += f"\n\n---\n\n"
    md += f"Baca versi lengkap dengan link pembelian terbaik di **[UlasanTekno]({url})** 🚀\n\n"
    md += "#" + " #".join(tags) + "\n"
    return md


def to_kompasiana_html(fm, body, url):
    """Format for Kompasiana (HTML editor)."""
    title = fm.get("title", "Untitled")
    # Convert simple markdown to HTML
    html = body
    # Headers
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    # Bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    # Italic
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    # Links
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank">\1</a>', html)
    # Lists
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.+</li>\n)+', r'<ul>\g<0></ul>', html)
    # Paragraphs (simple)
    paragraphs = html.split('\n\n')
    new_ps = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('<'):
            p = f'<p>{p}</p>'
        new_ps.append(p)
    html = '\n\n'.join(new_ps)
    
    full = f"""<h1>{title}</h1>
<p><em>Artikel asli dari <a href="{url}" target="_blank">UlasanTekno</a></em></p>
<hr/>
{html}
<hr/>
<p>Baca versi lengkap dengan harga terupdate dan link pembelian di <strong><a href="{url}" target="_blank">UlasanTekno</a></strong> 🛒</p>
"""
    return full


def publish_medium(title, content, tags):
    """Publish to Medium via API."""
    if not MEDIUM_TOKEN:
        print("ℹ️  MEDIUM_API_TOKEN not set, skipping auto-publish.")
        return None
    
    # Get user ID
    req = urllib.request.Request(
        "https://api.medium.com/v1/me",
        headers={"Authorization": f"Bearer {MEDIUM_TOKEN}", "Content-Type": "application/json"}
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        user = json.loads(r.read())["data"]["id"]
    except Exception as e:
        print(f"❌ Medium auth failed: {e}")
        return None
    
    payload = {
        "title": title,
        "contentFormat": "markdown",
        "content": content,
        "tags": tags[:5],
        "publishStatus": "public"
    }
    
    req = urllib.request.Request(
        f"https://api.medium.com/v1/users/{user}/posts",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {MEDIUM_TOKEN}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())["data"]
        print(f"✅ Medium published: {data['url']}")
        return data["url"]
    except Exception as e:
        print(f"❌ Medium publish failed: {e}")
        return None


def main():
    post_file = sys.argv[1] if len(sys.argv) > 1 else None
    if not post_file:
        lp = latest_post()
        if not lp:
            print("No posts found.")
            sys.exit(1)
        post_file = str(lp)
    
    path = Path(post_file)
    if not path.exists():
        print(f"File not found: {post_file}")
        sys.exit(1)
    
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    
    slug = path.stem
    # Convert Jekyll slug to URL
    parts = slug.split("-")
    if len(parts) >= 3 and parts[0].isdigit():
        date_part = "/".join(parts[:3])
        title_part = "-".join(parts[3:])
        url = f"https://ulasanteknoid.my.id/{date_part}/{title_part}.html"
    else:
        url = f"https://ulasanteknoid.my.id/{slug}.html"
    
    title = fm.get("title", "Untitled")
    print(f"📝 Processing: {title}")
    print(f"🔗 URL: {url}\n")
    
    # Generate Medium version
    medium_md = to_medium_markdown(fm, body, url)
    medium_file = CROSS_DIR / f"{slug}-medium.md"
    medium_file.write_text(medium_md, encoding="utf-8")
    print(f"✅ Medium draft: {medium_file}")
    
    # Generate Kompasiana version
    komp_html = to_kompasiana_html(fm, body, url)
    komp_file = CROSS_DIR / f"{slug}-kompasiana.html"
    komp_file.write_text(komp_html, encoding="utf-8")
    print(f"✅ Kompasiana draft: {komp_file}")
    
    # Try auto-publish Medium
    tags = [fm.get("category", "Technology"), "Indonesia", "Review", "Gadget", "2026"]
    medium_url = publish_medium(title, medium_md, tags)
    
    print("\n" + "="*60)
    print("📋 Next Steps:")
    if not medium_url:
        print("1. Copy medium draft ke https://medium.com/new-story")
        print(f"   File: {medium_file}")
    print("2. Copy kompasiana draft ke https://www.kompasiana.com/tulis")
    print(f"   File: {komp_file}")
    print("3. Tambahkan canonical link ke artikel asli (sudah ada di dalam konten)")
    print("="*60)


if __name__ == "__main__":
    main()
