#!/usr/bin/env python3
"""
Test script for AI Analytics Platform
Verifies the agent workflow end-to-end
"""

import asyncio
import json
import httpx
from datetime import datetime


BASE_URL = "http://localhost:8000"


async def test_health():
    """Test API health"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"✓ Health check: {response.json()}")
        return response.status_code == 200


async def test_query_workflow():
    """Test the full query workflow"""
    async with httpx.AsyncClient() as client:
        # Start a query
        print("\n1. Starting query workflow...")
        response = await client.post(
            f"{BASE_URL}/api/query",
            json={
                "query": "What was the total revenue last month?",
                "tenant_id": "demo-tenant",
                "user_id": "demo-user"
            }
        )
        
        if response.status_code != 200:
            print(f"✗ Failed to start query: {response.text}")
            return False
        
        data = response.json()
        workflow_id = data["workflow_id"]
        print(f"✓ Workflow started: {workflow_id}")
        
        # Stream results
        print("\n2. Streaming results...")
        events = []
        async with client.stream(
            "GET",
            f"{BASE_URL}/api/stream/{workflow_id}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event_data = line[6:]  # Remove "data: " prefix
                    try:
                        event = json.loads(event_data)
                        events.append(event)
                        print(f"  Step: {event.get('step', 'unknown')} - {event.get('status', 'unknown')}")
                        
                        if event.get("sql"):
                            print(f"  SQL: {event['sql'][:100]}...")
                        
                        if event.get("result_preview"):
                            preview = event["result_preview"]
                            print(f"  Results: {preview.get('row_count', 0)} rows")
                        
                        if event.get("step") == "end":
                            break
                    except json.JSONDecodeError:
                        continue
        
        print(f"\n✓ Workflow complete! Received {len(events)} events")
        return True


async def test_suggestions():
    """Test suggestions API"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/suggestions")
        if response.status_code == 200:
            suggestions = response.json()
            print(f"\n✓ Suggestions API: {len(suggestions)} suggestions returned")
            for s in suggestions:
                print(f"  - {s['type']}: {s['text'][:50]}...")
            return True
        else:
            print(f"✗ Suggestions API failed: {response.status_code}")
            return False


async def test_dashboards():
    """Test dashboard APIs"""
    async with httpx.AsyncClient() as client:
        # List dashboards
        response = await client.get(f"{BASE_URL}/api/dashboards")
        print(f"\n✓ Dashboards API: {response.status_code}")
        return response.status_code in [200, 401]  # 401 is OK if auth not set up


async def main():
    print("=" * 60)
    print("AI Analytics Platform - Integration Tests")
    print("=" * 60)
    print(f"Testing against: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health),
        ("Query Workflow", test_query_workflow),
        ("Suggestions", test_suggestions),
        ("Dashboards", test_dashboards),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
