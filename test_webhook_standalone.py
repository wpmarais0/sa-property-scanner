#!/usr/bin/env python3
"""Standalone webhook test — only uses standard library."""

import json
import sys
import urllib.request
import urllib.error

WEBHOOK_URL = sys.argv[1] if len(sys.argv) > 1 else ""

if not WEBHOOK_URL or "webhooks" not in WEBHOOK_URL:
    print("Usage: python3 test_webhook_standalone.py YOUR_DISCORD_WEBHOOK_URL")
    sys.exit(1)

embed = {
    "title": "🆕 3 Bedroom House in Testville",
    "description": "[📍 Testville, Western Cape](https://www.sothebysrealty.co.za)",
    "color": 0x00FF00,
    "url": "https://www.sothebysrealty.co.za",
    "image": {"url": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800"},
    "fields": [
        {"name": "💰 Price", "value": "R 1,450,000", "inline": True},
        {"name": "🛏 Bedrooms", "value": "3", "inline": True},
        {"name": "🛁 Bathrooms", "value": "2", "inline": True},
        {"name": "🚗 Garages", "value": "1", "inline": True},
        {"name": "🏠 Type", "value": "House", "inline": True},
        {"name": "📐 Size", "value": "250 m²", "inline": True},
        {"name": "📝 Notes", "value": "🐕 Pet friendly mention\n🌳 Own yard/stand mention", "inline": False},
    ],
    "footer": {"text": "Source: test | Property Scanner"},
}

payload = {
    "content": "🆕 **New Listing Alert**",
    "embeds": [embed],
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    WEBHOOK_URL,
    data=data,
    headers={"Content-Type": "application/json", "User-Agent": "PropertyScanner/1.0"},
    method="POST",
)

print(f"Sending test notification to Discord...")
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"Status: {resp.status}")
        if resp.status in (200, 204):
            print("✅ SUCCESS! Check your Discord channel for the rich embed.")
        else:
            print(f"⚠️ Unexpected status: {resp.status}")
except urllib.error.HTTPError as e:
    print(f"❌ FAILED: HTTP {e.code} — {e.reason}")
    body = e.read().decode("utf-8", errors="replace")[:300]
    if body:
        print(f"Response: {body}")
    sys.exit(1)
except Exception as e:
    print(f"❌ FAILED: {e}")
    sys.exit(1)
