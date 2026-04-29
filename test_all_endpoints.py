#!/usr/bin/env python3
import requests
import json

print("Testing all Vera Bot endpoints...\n")

endpoints = [
    ("GET", "http://localhost:8080/"),
    ("GET", "http://localhost:8080/v1/healthz"),
    ("GET", "http://localhost:8080/v1/metadata"),
]

for method, url in endpoints:
    try:
        if method == "GET":
            response = requests.get(url, timeout=3)
        print(f"✓ {method} {url}")
        print(f"  Status: {response.status_code}")
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
        print()
    except Exception as e:
        print(f"✗ {method} {url}")
        print(f"  Error: {e}\n")

print("Bot is accessible at: http://localhost:8080/")
print("Health check: http://localhost:8080/v1/healthz")
print("Metadata: http://localhost:8080/v1/metadata")

