#!/usr/bin/env python3
import asyncio
import httpx
import sys
import os
sys.path.insert(0, '/root/.claude/worktrees/contentflow-bot/contentflow')

from utils.auth import sign_user_id

async def test_posts():
    """Test GET /api/posts endpoint with service auth"""
    user_id = 5264530602
    sig = sign_user_id(user_id)

    api_key = os.environ.get("API_KEY", "")
    if not api_key:
        print("❌ API_KEY not found in environment")
        return

    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        print("\n" + "="*60)
        print("TEST 1: GET /api/posts with status=new")
        print("="*60)

        resp = await client.get(
            '/api/posts',
            headers={'Authorization': f'Bearer {api_key}'},
            params={'status': 'new', 'user_id': user_id, 'user_signature': sig}
        )
        print(f"Status: {resp.status_code}")
        print(f"URL: {resp.request.url}")
        if resp.status_code == 200:
            posts = resp.json()
            print(f"✅ Success! Posts returned: {len(posts)}")
            if posts:
                print(f"   First post: {posts[0].get('title', 'No title')[:50]}")
        else:
            print(f"❌ Error: {resp.text[:200]}")

        print("\n" + "="*60)
        print("TEST 2: GET /api/posts with status=draft")
        print("="*60)

        resp = await client.get(
            '/api/posts',
            headers={'Authorization': f'Bearer {api_key}'},
            params={'status': 'draft', 'user_id': user_id, 'user_signature': sig}
        )
        print(f"Status: {resp.status_code}")
        print(f"URL: {resp.request.url}")
        if resp.status_code == 200:
            posts = resp.json()
            print(f"✅ Success! Posts returned: {len(posts)}")
        else:
            print(f"❌ Error: {resp.text[:200]}")

        print("\n" + "="*60)
        print("TEST 3: GET /api/posts/ (with trailing slash)")
        print("="*60)

        resp = await client.get(
            '/api/posts/',
            headers={'Authorization': f'Bearer {api_key}'},
            params={'status': 'new', 'user_id': user_id, 'user_signature': sig}
        )
        print(f"Status: {resp.status_code}")
        print(f"URL: {resp.request.url}")
        if resp.status_code == 200:
            posts = resp.json()
            print(f"✅ Success! No 307 redirect - direct 200 response")
        else:
            print(f"❌ Error: {resp.text[:200]}")

        print("\n" + "="*60)
        print("TEST 4: Missing signature (should fail)")
        print("="*60)

        resp = await client.get(
            '/api/posts',
            headers={'Authorization': f'Bearer {api_key}'},
            params={'status': 'new', 'user_id': user_id}
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 400:
            print(f"✅ Correctly rejected: {resp.json()['detail']}")
        else:
            print(f"❌ Should be 400, got {resp.status_code}")

if __name__ == '__main__':
    asyncio.run(test_posts())
