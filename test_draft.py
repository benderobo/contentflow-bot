#!/usr/bin/env python3
import asyncio
import httpx
import sys
import os
sys.path.insert(0, '/root/.claude/worktrees/contentflow-bot/contentflow')

from utils.auth import sign_user_id

async def test():
    user_id = 5264530602
    sig = sign_user_id(user_id)
    api_key = os.environ.get("API_KEY", "")

    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        resp = await client.get(
            '/api/posts',
            headers={'Authorization': f'Bearer {api_key}'},
            params={'status': 'draft', 'user_id': user_id, 'user_signature': sig}
        )
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Posts count: {len(data)}")
        if data:
            print(f"First post: {data[0]}")

asyncio.run(test())
