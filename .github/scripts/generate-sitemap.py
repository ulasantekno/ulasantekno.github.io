#!/usr/bin/env python3
"""
Generate sitemap.xml for Jekyll blog.
Mencari semua file markdown di _posts/ dan root untuk halaman statis.
"""
import os
import re
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom

# Konfigurasi
BASE_URL = 'https://ulasantekno.github.io'
SITEMAP_PATH = 'sitemap.xml'
POSTS_DIR = '_posts'
STATIC_PAGES = ['index.md', 'about.md', 'contact.md']  # Tambah halaman lain jika ada
PRIORITY_MAP = {
    'index.md': '1.0',
    '_posts/': '0.8',    # Artikel utama
    '.md': '0.6',        # Halaman statis
}
CHANGEFREQ = 'weekly'

def get_post_date(filename):
    """Extract date from Jekyll post filename (YYYY-MM-DD-title.md)"""
    match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.md', filename)
    if match:
        return match.group(1)
    return datetime.now().strftime('%Y-%m-%d')

def get_lastmod(filepath):
    """Get file modification time"""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')

def get_priority(url):
    """Determine priority based on URL path"""
    if url == BASE_URL + '/':
        return '1.0'
    elif '/posts/' in url or url.endswith('.html'):
        return '0.8'
    else:
        return '0.6'

def find_markdown_files():
    """Find all markdown files for sitemap"""
    urls = []
    
    # 1. Homepage
    urls.append({
        'loc': BASE_URL + '/',
        'lastmod': datetime.now().strftime('%Y-%m-%d'),
        'priority': '1.0',
        'changefreq': 'daily'
    })
    
    # 2. Blog posts
    if os.path.exists(POSTS_DIR):
        for filename in os.listdir(POSTS_DIR):
            if filename.endswith('.md'):
                filepath = os.path.join(POSTS_DIR, filename)
                slug = filename[11:-3]  # Remove date and .md
                urls.append({
                    'loc': f'{BASE_URL}/posts/{slug}/',
                    'lastmod': get_lastmod(filepath),
                    'priority': '0.8',
                    'changefreq': 'monthly'
                })
    
    # 3. Static pages (root directory)
    for page in STATIC_PAGES:
        if os.path.exists(page):
            slug = page[:-3]  # Remove .md
            if slug == 'index':
                continue  # Already added
            urls.append({
                'loc': f'{BASE_URL}/{slug}/',
                'lastmod': get_lastmod(page),
                'priority': '0.6',
                'changefreq': 'monthly'
            })
    
    # 4. Archive/category pages (jika ada)
    archive_pages = ['archive.html', 'categories.html', 'tags.html']
    for page in archive_pages:
        if os.path.exists(page):
            urls.append({
                'loc': f'{BASE_URL}/{page}',
                'lastmod': datetime.now().strftime('%Y-%m-%d'),
                'priority': '0.4',
                'changefreq': 'weekly'
            })
    
    return urls

def create_sitemap(urls):
    """Create XML sitemap"""
    # Create root element
    urlset = ET.Element('urlset')
    urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    urlset.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    urlset.set('xsi:schemaLocation', 
               'http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd')
    
    # Add each URL
    for url_info in urls:
        url_elem = ET.SubElement(urlset, 'url')
        
        loc = ET.SubElement(url_elem, 'loc')
        loc.text = url_info['loc']
        
        lastmod = ET.SubElement(url_elem, 'lastmod')
        lastmod.text = url_info['lastmod']
        
        changefreq = ET.SubElement(url_elem, 'changefreq')
        changefreq.text = url_info['changefreq']
        
        priority = ET.SubElement(url_elem, 'priority')
        priority.text = url_info['priority']
    
    # Format XML
    xml_str = ET.tostring(urlset, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    # Remove extra newlines
    pretty_xml = os.linesep.join([s for s in pretty_xml.splitlines() if s.strip()])
    
    return pretty_xml

def main():
    print("🔍 Finding markdown files...")
    urls = find_markdown_files()
    
    print(f"📝 Found {len(urls)} URLs for sitemap")
    
    print("🛠️ Creating sitemap.xml...")
    sitemap_xml = create_sitemap(urls)
    
    # Write to file
    with open(SITEMAP_PATH, 'w', encoding='utf-8') as f:
        f.write(sitemap_xml)
    
    print(f"✅ Sitemap generated: {SITEMAP_PATH}")
    print("📊 Summary:")
    for i, url in enumerate(urls[:5], 1):
        print(f"  {i}. {url['loc']}")
    if len(urls) > 5:
        print(f"  ... and {len(urls) - 5} more")

if __name__ == '__main__':
    main()