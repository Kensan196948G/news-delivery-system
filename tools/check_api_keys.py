#!/usr/bin/env python3
"""
API Keys Validation Script
Checks all API keys and their validity for the News Delivery System
"""

import os
import asyncio
import aiohttp
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

async def check_newsapi_key():
    """Check NewsAPI key validity"""
    print("🔍 Checking NewsAPI key...")
    
    api_key = os.getenv('NEWSAPI_KEY')
    if not api_key:
        print("❌ NewsAPI key not found in environment")
        return False
    
    try:
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            'apiKey': api_key,
            'country': 'us',
            'pageSize': 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    total_results = data.get('totalResults', 0)
                    print(f"✅ NewsAPI key is valid - {total_results} articles available")
                    return True
                elif response.status == 401:
                    print("❌ NewsAPI key is invalid (401 Unauthorized)")
                    return False
                elif response.status == 429:
                    print("⚠️  NewsAPI rate limit exceeded")
                    return True  # Key is valid but rate limited
                else:
                    print(f"⚠️  NewsAPI returned status {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error checking NewsAPI: {e}")
        return False

async def check_gnews_key():
    """Check GNews API key validity"""
    print("🔍 Checking GNews API key...")
    
    api_key = os.getenv('GNEWS_API_KEY')
    if not api_key:
        print("❌ GNews API key not found in environment")
        return False
    
    try:
        url = "https://gnews.io/api/v4/top-headlines"
        params = {
            'apikey': api_key,
            'lang': 'en',
            'country': 'us',
            'max': 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    total_articles = data.get('totalArticles', 0)
                    print(f"✅ GNews API key is valid - {total_articles} articles available")
                    return True
                elif response.status == 401:
                    print("❌ GNews API key is invalid (401 Unauthorized)")
                    return False
                elif response.status == 403:
                    print("❌ GNews API access forbidden (403) - Check API plan or permissions")
                    print("   This could indicate:")
                    print("   - API key is invalid")
                    print("   - Free plan limitations")
                    print("   - Exceeded quota")
                    return False
                elif response.status == 429:
                    print("⚠️  GNews API rate limit exceeded")
                    return True  # Key might be valid but rate limited
                else:
                    error_text = await response.text()
                    print(f"⚠️  GNews API returned status {response.status}")
                    print(f"   Response: {error_text[:200]}...")
                    return False
                    
    except Exception as e:
        print(f"❌ Error checking GNews API: {e}")
        return False

def check_deepl_key():
    """Check DeepL API key validity"""
    print("🔍 Checking DeepL API key...")
    
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        print("❌ DeepL API key not found in environment")
        return False
    
    try:
        # Determine if it's a free or pro key
        if api_key.endswith(':fx'):
            base_url = "https://api-free.deepl.com/v2"
            print("📝 Using DeepL Free API")
        else:
            base_url = "https://api.deepl.com/v2"
            print("📝 Using DeepL Pro API")
        
        url = f"{base_url}/usage"
        headers = {
            'Authorization': f'DeepL-Auth-Key {api_key}'
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            char_count = data.get('character_count', 0)
            char_limit = data.get('character_limit', 0)
            
            print(f"✅ DeepL API key is valid")
            print(f"   Characters used: {char_count:,} / {char_limit:,}")
            
            if char_limit > 0:
                usage_percent = (char_count / char_limit) * 100
                print(f"   Usage: {usage_percent:.1f}%")
                
                if usage_percent > 90:
                    print("⚠️  DeepL usage is very high (>90%)")
                elif usage_percent > 75:
                    print("⚠️  DeepL usage is high (>75%)")
            
            return True
        elif response.status_code == 403:
            print("❌ DeepL API key is invalid (403 Forbidden)")
            return False
        else:
            print(f"⚠️  DeepL API returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking DeepL API: {e}")
        return False

def check_anthropic_key():
    """Check Anthropic Claude API key validity"""
    print("🔍 Checking Anthropic Claude API key...")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Anthropic API key not found in environment")
        return False
    
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Test with a simple message
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Use cheaper model for testing
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": "Hello"
            }]
        )
        
        if response.content:
            print("✅ Anthropic Claude API key is valid")
            return True
        else:
            print("❌ Anthropic Claude API returned empty response")
            return False
            
    except Exception as e:
        error_message = str(e)
        if "authentication" in error_message.lower() or "unauthorized" in error_message.lower():
            print("❌ Anthropic Claude API key is invalid")
        else:
            print(f"❌ Error checking Anthropic Claude API: {e}")
        return False

async def check_nvd_api():
    """Check NVD API availability"""
    print("🔍 Checking NVD API availability...")
    
    # NVD API doesn't require an API key for basic access
    try:
        url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        params = {
            'resultsPerPage': 1,
            'startIndex': 0
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    total_results = data.get('totalResults', 0)
                    print(f"✅ NVD API is accessible - {total_results:,} CVEs available")
                    return True
                elif response.status == 403:
                    print("❌ NVD API access forbidden (403)")
                    return False
                elif response.status == 503:
                    print("⚠️  NVD API service unavailable (503)")
                    return False
                else:
                    print(f"⚠️  NVD API returned status {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        print("❌ NVD API timeout")
        return False
    except Exception as e:
        print(f"❌ Error checking NVD API: {e}")
        return False

def check_gmail_setup():
    """Check Gmail API setup"""
    print("🔍 Checking Gmail API setup...")
    
    client_id = os.getenv('GMAIL_CLIENT_ID')
    client_secret = os.getenv('GMAIL_CLIENT_SECRET')
    refresh_token = os.getenv('GMAIL_REFRESH_TOKEN')
    
    if not client_id:
        print("❌ GMAIL_CLIENT_ID not found in environment")
        return False
    
    if not client_secret:
        print("❌ GMAIL_CLIENT_SECRET not found in environment")
        return False
    
    if not refresh_token:
        print("❌ GMAIL_REFRESH_TOKEN not found in environment")
        print("   Run setup_gmail_auth.py to set up authentication")
        return False
    
    # Check if token.json exists
    token_path = Path('token.json')
    if token_path.exists():
        print("✅ Gmail token.json file exists")
        
        # Check if authentication is marked as completed
        auth_completed = os.getenv('GMAIL_AUTH_COMPLETED', 'false').lower() == 'true'
        if auth_completed:
            print("✅ Gmail authentication marked as completed")
        else:
            print("⚠️  Gmail authentication not marked as completed")
            print("   Consider running setup_gmail_auth.py")
        
        return True
    else:
        print("⚠️  Gmail token.json file not found")
        print("   Run setup_gmail_auth.py to set up authentication")
        return False

async def main():
    """Main validation function"""
    
    print("=" * 70)
    print("🔑 API Keys Validation for News Delivery System")
    print("=" * 70)
    print(f"📅 Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load environment variables
    load_dotenv()
    
    # Check all APIs
    results = {}
    
    results['newsapi'] = await check_newsapi_key()
    print()
    
    results['gnews'] = await check_gnews_key()
    print()
    
    results['deepl'] = check_deepl_key()
    print()
    
    results['anthropic'] = check_anthropic_key()
    print()
    
    results['nvd'] = await check_nvd_api()
    print()
    
    results['gmail'] = check_gmail_setup()
    print()
    
    # Summary
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        service_name = service.upper().replace('_', ' ')
        print(f"{status_icon} {service_name:<20} {'WORKING' if status else 'NEEDS ATTENTION'}")
    
    total_working = sum(results.values())
    total_services = len(results)
    
    print()
    print(f"📈 Overall Status: {total_working}/{total_services} services working")
    
    if total_working == total_services:
        print("🎉 All services are working correctly!")
    elif total_working >= total_services * 0.8:
        print("⚠️  Most services working, some need attention")
    else:
        print("❌ Multiple services need attention")
    
    print("=" * 70)
    
    # Specific recommendations
    if not results['gnews']:
        print("\n💡 GNews API Recommendations:")
        print("   1. Check if your API key is correct")
        print("   2. Verify your GNews plan limits")
        print("   3. Consider upgrading your GNews plan")
        print("   4. Use alternative news sources if needed")
    
    if not results['gmail']:
        print("\n💡 Gmail API Recommendations:")
        print("   1. Run: python setup_gmail_auth.py")
        print("   2. Follow the OAuth2 authentication flow")
        print("   3. Ensure all Gmail credentials are set correctly")
    
    return total_working == total_services

if __name__ == '__main__':
    success = asyncio.run(main())
    exit(0 if success else 1)