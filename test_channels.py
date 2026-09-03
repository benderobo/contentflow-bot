#!/usr/bin/env python3
"""Test channels endpoint with service auth."""
import asyncio
import httpx
import sys
sys.path.insert(0, '/root/.claude/worktrees/contentflow-bot/contentflow')

from utils.auth import sign_user_id

async def test_channels():
    user_id = 5264530602
    sig = sign_user_id(user_id)
    api_key = "internal-bot-key-production-change-this"

    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        # Test GET /api/channels
        resp = await client.get(
            '/api/channels',
            headers={
                'Authorization': f'Bearer {api_key}',
                'X-Service-Account': 'bot'
            },
            params={'user_id': user_id, 'user_signature': sig}
        )
        print(f"GET /api/channels: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Loaded {len(data)} channels")
            for ch in data:
                print(f"  - {ch['name']} ({ch['telegram_id']})")
        else:
            print(f"❌ Error: {resp.text[:200]}")

asyncio.run(test_channels())
