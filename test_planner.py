"""
Test script for PC Planner API endpoints.
Run this after starting the server to verify planner functionality.
"""

import requests
import json

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/planner"

# Mock user_id for testing (adjust based on your auth setup)
HEADERS = {
    "Content-Type": "application/json",
}


def print_response(title, response):
    """Pretty print API response."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")


def test_planner():
    """Test the PC Planner API endpoints."""
    
    # 1. Create a new build with target profit
    print("\n🔧 TEST 1: Create Build with Target Profit")
    build_data = {
        "name": "Gaming PC - Test Build",
        "target_profit_percentage": 30
    }
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/builds",
        json=build_data,
        headers=HEADERS
    )
    print_response("Create Build Response", response)
    
    if response.status_code != 200:
        print("\n❌ Failed to create build. Check authentication.")
        return
    
    build = response.json()
    build_id = build["id"]
    
    # 2. Get available inventory
    print("\n📦 TEST 2: Get Available Inventory")
    response = requests.get(
        f"{BASE_URL}{API_PREFIX}/inventory-available",
        headers=HEADERS
    )
    print_response("Available Inventory", response)
    
    # 3. Get all builds
    print("\n📋 TEST 3: Get All Builds")
    response = requests.get(
        f"{BASE_URL}{API_PREFIX}/builds",
        headers=HEADERS
    )
    print_response("All Builds", response)
    
    # 4. Get build details
    print("\n🔍 TEST 4: Get Build Details")
    response = requests.get(
        f"{BASE_URL}{API_PREFIX}/builds/{build_id}",
        headers=HEADERS
    )
    print_response("Build Details", response)
    
    # 5. Add a component (inventory-backed)
    print("\n➕ TEST 5: Add Inventory-Backed Component")
    # Note: You'll need to adjust product_id and lot_id based on your data
    component_data = {
        "product_id": 1,
        "lot_id": 1,
        "quantity": 1,
        "cost_at_time": 399.99,
        "is_external": False
    }
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/builds/{build_id}/components",
        json=component_data,
        headers=HEADERS
    )
    print_response("Add Component Response", response)
    
    # 6. Add an external component
    print("\n➕ TEST 6: Add External Component")
    external_component = {
        "product_id": 2,
        "lot_id": None,
        "quantity": 1,
        "cost_at_time": 149.99,
        "is_external": True
    }
    response = requests.post(
        f"{BASE_URL}{API_PREFIX}/builds/{build_id}/components",
        json=external_component,
        headers=HEADERS
    )
    print_response("Add External Component Response", response)
    
    # 7. Get target profit analysis
    print("\n📊 TEST 7: Target Profit Analysis")
    response = requests.get(
        f"{BASE_URL}{API_PREFIX}/builds/{build_id}/target-profit-analysis",
        headers=HEADERS
    )
    print_response("Target Profit Analysis", response)
    
    # 8. Get build reservations
    print("\n🔒 TEST 8: Get Build Reservations")
    response = requests.get(
        f"{BASE_URL}{API_PREFIX}/builds/{build_id}/reservations",
        headers=HEADERS
    )
    print_response("Build Reservations", response)
    
    # 9. Update build target profit
    print("\n✏️ TEST 9: Update Build Target Profit")
    update_data = {
        "target_profit_amount": 500
    }
    response = requests.put(
        f"{BASE_URL}{API_PREFIX}/builds/{build_id}",
        json=update_data,
        headers=HEADERS
    )
    print_response("Update Build Response", response)
    
    # 10. Delete build (cleanup)
    print("\n🗑️ TEST 10: Delete Build")
    response = requests.delete(
        f"{BASE_URL}{API_PREFIX}/builds/{build_id}",
        headers=HEADERS
    )
    print_response("Delete Build Response", response)
    
    print("\n" + "=" * 60)
    print("✅ Test Suite Complete")
    print("=" * 60)


if __name__ == "__main__":
    print("🚀 Starting PC Planner API Tests")
    print("Make sure the server is running on http://localhost:8000")
    print("Press Ctrl+C to cancel...")
    
    try:
        test_planner()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("Make sure the server is running on http://localhost:8000")
    except KeyboardInterrupt:
        print("\n\n⚠️ Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
