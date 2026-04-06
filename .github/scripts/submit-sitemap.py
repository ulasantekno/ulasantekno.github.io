#!/usr/bin/env python3
"""
Script untuk submit sitemap.xml ke Google Search Console.
Dijalankan otomatis oleh GitHub Actions setiap ada update blog.
"""
import os
import json
import sys
import google.auth
from googleapiclient.discovery import build
from google.oauth2 import service_account
from urllib.parse import urlparse

# Konfigurasi
SITE_URL = 'https://ulasantekno.github.io'
SITEMAP_URL = f'{SITE_URL}/sitemap.xml'
SCOPES = ['https://www.googleapis.com/auth/webmasters']

def load_credentials_from_env():
    """Load credentials dari environment variable (GitHub Secret)"""
    creds_json = os.environ.get('GSC_SERVICE_ACCOUNT_JSON')
    if not creds_json:
        print("❌ GSC_SERVICE_ACCOUNT_JSON environment variable tidak ditemukan")
        sys.exit(1)
    
    try:
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        return credentials
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON credentials: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading credentials: {e}")
        sys.exit(1)

def submit_sitemap(service):
    """Submit sitemap ke Google Search Console"""
    try:
        # Submit sitemap
        service.sitemaps().submit(
            siteUrl=SITE_URL,
            feedpath=SITEMAP_URL
        ).execute()
        print(f"✅ Sitemap submitted: {SITEMAP_URL}")
        
        # Get status untuk verifikasi
        response = service.sitemaps().get(
            siteUrl=SITE_URL,
            feedpath=SITEMAP_URL
        ).execute()
        
        print("📊 Sitemap Status:")
        print(f"  - Last submitted: {response.get('lastSubmitted', 'N/A')}")
        print(f"  - Last downloaded: {response.get('lastDownloaded', 'N/A')}")
        print(f"  - Status: {response.get('type', 'N/A')}")
        
        if 'errors' in response:
            print(f"  ⚠️  Errors: {response['errors']}")
            
    except Exception as e:
        print(f"❌ Failed to submit sitemap: {e}")
        sys.exit(1)

def main():
    print("🚀 Starting Google Search Console sitemap submission...")
    print(f"📝 Site URL: {SITE_URL}")
    print(f"🗺️  Sitemap: {SITEMAP_URL}")
    
    # Load credentials
    print("🔑 Loading credentials...")
    credentials = load_credentials_from_env()
    
    # Build service
    print("🔧 Building Search Console service...")
    service = build('searchconsole', 'v1', credentials=credentials)
    
    # Submit sitemap
    submit_sitemap(service)
    
    print("🎉 Sitemap submission completed successfully!")

if __name__ == '__main__':
    main()