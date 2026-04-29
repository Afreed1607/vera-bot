#!/usr/bin/env python3
"""Test the bot endpoint"""
import time
import requests

print("Testing bot endpoint...")
time.sleep(2)

try:
    response = requests.get("http://localhost:8080/v1/healthz", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
    print("Bot may not be running yet. Try: python bot.py local")

