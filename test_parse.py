#!/usr/bin/env python3
import asyncio
import httpx
import sys
import os
sys.path.insert(0, '/root/.claude/worktrees/contentflow-bot/contentflow')

from utils.auth import sign_user_id

async def test_parse():
    """Test POST /api/sources/parse-all endpoint"""
    user_id = 5264530602
    sig = sign_user_id(user_id)
    api_key = os.environ.get("API_KEY", "")

    if not api_key:
        print("❌ API_KEY not found")
        return

    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        print("\nTesting POST /api/sources/parse-all")
        print("=" * 60)

        resp = await client.post(
            '/api/sources/parse-all',
            headers={'Authorization': f'Bearer {api_key}'},
            json={'user_id': user_id, 'user_signature': sig}
        )

        print(f"Status: {resp.status_code}")
        print(f"URL: {resp.request.url}")

        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ Success!")
            print(f"   Parsed sources: {result.get('parsed_count', 0)}")
            print(f"   Items found: {result.get('items_count', 0)}")
        else:
            print(f"❌ Error: {resp.text[:300]}")

if __name__ == '__main__':
    asyncio.run(test_parse())
