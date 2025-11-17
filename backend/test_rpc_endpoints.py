#!/usr/bin/env python3
"""
Quick test script to find working Babylon RPC endpoints
Tests multiple endpoints with httpx (same library as our RPC client)
"""
import asyncio
import httpx
import json

# List of RPC endpoints to test
ENDPOINTS = [
    # Mainnet endpoints
    ("Polkachu Mainnet", "https://babylon-rpc.polkachu.com"),
    ("Nodes.Guru Mainnet", "https://babylon-rpc.nodes.guru"),
    ("NodeStake Mainnet", "https://rpc.babylon.nodestake.org"),
    ("PublicNode Mainnet", "https://babylon-mainnet-rpc.publicnode.com"),
    ("ITRocket Mainnet", "https://babylon-mainnet-rpc.itrocket.net"),

    # Testnet endpoints
    ("Polkachu Testnet", "https://babylon-testnet-rpc.polkachu.com"),
    ("Nodes.Guru Testnet", "https://babylon-testnet-rpc.nodes.guru"),
    ("NodeStake Testnet", "https://rpc-t.babylon.nodestake.org"),
]

async def test_endpoint(name: str, base_url: str):
    """Test a single RPC endpoint"""
    print(f"\n{'='*80}")
    print(f"🔍 Testing: {name}")
    print(f"📡 URL: {base_url}")
    print(f"{'='*80}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: /status endpoint
        try:
            print(f"  → GET {base_url}/status")
            response = await client.get(f"{base_url}/status")
            print(f"  ✓ Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'node_info' in data['result']:
                    network = data['result']['node_info'].get('network', 'unknown')
                    latest_height = data['result']['sync_info'].get('latest_block_height', 'unknown')
                    print(f"  ✅ SUCCESS!")
                    print(f"  ✓ Network: {network}")
                    print(f"  ✓ Latest Height: {latest_height}")
                    return True, base_url
                else:
                    print(f"  ⚠️  Unexpected response format")
                    print(f"  Response: {response.text[:200]}")
            else:
                print(f"  ❌ Failed: HTTP {response.status_code}")
                print(f"  Response: {response.text[:200]}")

        except httpx.TimeoutException:
            print(f"  ❌ Timeout after 10 seconds")
        except httpx.ConnectError as e:
            print(f"  ❌ Connection failed: {e}")
        except Exception as e:
            print(f"  ❌ Error: {type(e).__name__}: {str(e)[:100]}")

    return False, None

async def main():
    """Test all endpoints"""
    print("\n" + "="*80)
    print("🚀 BABYLON RPC ENDPOINT TESTING")
    print("="*80)
    print(f"Testing {len(ENDPOINTS)} RPC endpoints...")

    working_endpoints = []

    for name, url in ENDPOINTS:
        success, endpoint = await test_endpoint(name, url)
        if success:
            working_endpoints.append((name, endpoint))

        # Small delay between tests
        await asyncio.sleep(0.5)

    # Print summary
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)

    if working_endpoints:
        print(f"✅ Found {len(working_endpoints)} working endpoint(s):\n")
        for name, url in working_endpoints:
            print(f"  ✓ {name}")
            print(f"    {url}\n")
    else:
        print("❌ No working endpoints found!")
        print("\nPossible reasons:")
        print("  • RPC endpoints require API keys or authentication")
        print("  • Rate limiting or IP blocking")
        print("  • Network/firewall restrictions")
        print("  • Endpoints may be down or unavailable")
        print("\nNext steps:")
        print("  • Check Babylon docs for updated endpoints")
        print("  • Consider running your own Babylon node")
        print("  • Contact Babylon community for RPC access")

    print("="*80 + "\n")

    return working_endpoints

if __name__ == "__main__":
    results = asyncio.run(main())

    # If we found working endpoints, show how to use them
    if results:
        print("\n💡 To use these endpoints, update backend/.env:")
        print("-" * 80)
        name, url = results[0]  # Use first working endpoint
        print(f"BABYLON_RPC_URL={url}")
        print(f"# Using: {name}")
        print("-" * 80 + "\n")
