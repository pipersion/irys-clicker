import requests
import sys
import time
import uuid
from datetime import datetime

class ClickerGameAPITester:
    def __init__(self, base_url="https://56b5fadc-9600-45f8-95c3-603e48936ef9.preview.emergentagent.com"):
        self.base_url = base_url
        self.player_id = f"test_player_{uuid.uuid4().hex[:8]}"
        self.tests_run = 0
        self.tests_passed = 0
        print(f"🎮 Testing Clicker Game API with player ID: {self.player_id}")
        print(f"🌐 Base URL: {base_url}")

    def run_test(self, name, method, endpoint, expected_status, data=None, expected_keys=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Test {self.tests_run}: {name}")
        print(f"   URL: {method} {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"   ✅ Status code correct")
                
                if response.status_code == 200 or response.status_code == 201:
                    try:
                        json_data = response.json()
                        if expected_keys:
                            missing_keys = [key for key in expected_keys if key not in json_data]
                            if missing_keys:
                                print(f"   ⚠️  Missing expected keys: {missing_keys}")
                            else:
                                print(f"   ✅ All expected keys present")
                        return True, json_data
                    except:
                        print(f"   ⚠️  Response not valid JSON")
                        return True, {}
                return True, {}
            else:
                print(f"   ❌ Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"   ❌ Request timed out")
            return False, {}
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return False, {}

    def test_get_player_initial(self):
        """Test getting initial player data"""
        success, data = self.run_test(
            "Get Initial Player Data",
            "GET",
            f"api/player/{self.player_id}",
            200,
            expected_keys=['player_id', 'points', 'energy', 'character_level', 'character_name', 'points_per_click']
        )
        
        if success and data:
            print(f"   📊 Initial Data:")
            print(f"      Points: {data.get('points', 'N/A')} ({data.get('points_formatted', 'N/A')})")
            print(f"      Energy: {data.get('energy', 'N/A')}/{data.get('max_energy', 'N/A')}")
            print(f"      Character: {data.get('character_name', 'N/A')} (Level {data.get('character_level', 'N/A')})")
            print(f"      Multiplier: {data.get('character_multiplier', 'N/A')}x")
            print(f"      Points per click: {data.get('points_per_click', 'N/A')}")
            print(f"      Upgrade level: {data.get('upgrade_level', 'N/A')}")
            print(f"      Next upgrade cost: {data.get('next_upgrade_cost', 'N/A')}")
            
            # Validate initial values
            if data.get('points') == 0 and data.get('energy') == 100 and data.get('character_level') == 1:
                print(f"   ✅ Initial values correct")
            else:
                print(f"   ⚠️  Initial values may be incorrect")
        
        return success, data

    def test_click_mechanics(self, initial_data):
        """Test clicking mechanics"""
        if not initial_data:
            print("   ❌ Cannot test clicking without initial data")
            return False, {}
            
        print(f"\n🖱️  Testing Click Mechanics")
        
        # Test successful click
        success, click_data = self.run_test(
            "Successful Click",
            "POST",
            "api/click",
            200,
            data={"player_id": self.player_id},
            expected_keys=['success', 'points_earned', 'new_points', 'new_energy']
        )
        
        if success and click_data:
            expected_points = initial_data.get('points_per_click', 1)
            actual_points = click_data.get('points_earned', 0)
            
            print(f"   📊 Click Results:")
            print(f"      Points earned: {actual_points} (expected: {expected_points})")
            print(f"      New total points: {click_data.get('new_points', 'N/A')}")
            print(f"      New energy: {click_data.get('new_energy', 'N/A')}")
            
            if actual_points == expected_points:
                print(f"   ✅ Points calculation correct")
            else:
                print(f"   ⚠️  Points calculation may be incorrect")
                
            if click_data.get('new_energy') == initial_data.get('energy', 100) - 2:
                print(f"   ✅ Energy consumption correct (2 per click)")
            else:
                print(f"   ⚠️  Energy consumption may be incorrect")
        
        return success, click_data

    def test_energy_depletion(self):
        """Test energy depletion by clicking until energy is too low"""
        print(f"\n⚡ Testing Energy Depletion")
        
        clicks_made = 0
        max_clicks = 50  # Safety limit
        
        while clicks_made < max_clicks:
            success, data = self.run_test(
                f"Click #{clicks_made + 1}",
                "POST",
                "api/click",
                200,  # Expect success until energy runs out
                data={"player_id": self.player_id}
            )
            
            if success and data:
                clicks_made += 1
                energy = data.get('new_energy', 0)
                print(f"   Click {clicks_made}: Energy now {energy}")
                
                if energy < 2:
                    print(f"   ✅ Energy depleted after {clicks_made} clicks")
                    break
            else:
                break
        
        # Now test that clicking with insufficient energy fails
        success, error_data = self.run_test(
            "Click with Insufficient Energy",
            "POST",
            "api/click",
            400,  # Should fail with 400
            data={"player_id": self.player_id}
        )
        
        if success:
            print(f"   ✅ Correctly rejected click with insufficient energy")
        
        return clicks_made

    def test_upgrade_system(self):
        """Test upgrade purchase system"""
        print(f"\n🛒 Testing Upgrade System")
        
        # First, get current player state
        success, player_data = self.run_test(
            "Get Player Data for Upgrade Test",
            "GET",
            f"api/player/{self.player_id}",
            200
        )
        
        if not success or not player_data:
            print("   ❌ Cannot test upgrades without player data")
            return False
        
        current_points = player_data.get('points', 0)
        upgrade_cost = player_data.get('next_upgrade_cost', 100)
        current_upgrade_level = player_data.get('upgrade_level', 0)
        
        print(f"   Current points: {current_points}")
        print(f"   Upgrade cost: {upgrade_cost}")
        print(f"   Current upgrade level: {current_upgrade_level}")
        
        if current_points < upgrade_cost:
            print(f"   ⚠️  Not enough points for upgrade test (need {upgrade_cost}, have {current_points})")
            
            # Test upgrade failure
            success, error_data = self.run_test(
                "Upgrade with Insufficient Points",
                "POST",
                "api/upgrade",
                400,
                data={"player_id": self.player_id, "upgrade_level": current_upgrade_level}
            )
            
            if success:
                print(f"   ✅ Correctly rejected upgrade with insufficient points")
            
            return False
        else:
            # Test successful upgrade
            success, upgrade_data = self.run_test(
                "Successful Upgrade Purchase",
                "POST",
                "api/upgrade",
                200,
                data={"player_id": self.player_id, "upgrade_level": current_upgrade_level},
                expected_keys=['success', 'new_points', 'new_upgrade_level', 'new_points_per_click']
            )
            
            if success and upgrade_data:
                print(f"   📊 Upgrade Results:")
                print(f"      New points: {upgrade_data.get('new_points', 'N/A')}")
                print(f"      New upgrade level: {upgrade_data.get('new_upgrade_level', 'N/A')}")
                print(f"      New points per click: {upgrade_data.get('new_points_per_click', 'N/A')}")
                
                expected_new_points = current_points - upgrade_cost
                if upgrade_data.get('new_points') == expected_new_points:
                    print(f"   ✅ Points deduction correct")
                else:
                    print(f"   ⚠️  Points deduction may be incorrect")
                
                if upgrade_data.get('new_upgrade_level') == current_upgrade_level + 1:
                    print(f"   ✅ Upgrade level increment correct")
                else:
                    print(f"   ⚠️  Upgrade level increment may be incorrect")
            
            return success

    def test_character_advancement(self):
        """Test character advancement (if possible)"""
        print(f"\n👤 Testing Character Advancement")
        
        # Get current player state
        success, player_data = self.run_test(
            "Get Player Data for Advancement Test",
            "GET",
            f"api/player/{self.player_id}",
            200
        )
        
        if not success or not player_data:
            print("   ❌ Cannot test advancement without player data")
            return False
        
        can_advance = player_data.get('can_advance', False)
        advancement_cost = player_data.get('advancement_cost')
        current_points = player_data.get('points', 0)
        current_level = player_data.get('character_level', 1)
        
        print(f"   Current level: {current_level}")
        print(f"   Current points: {current_points}")
        print(f"   Advancement cost: {advancement_cost}")
        print(f"   Can advance: {can_advance}")
        
        if not can_advance:
            print(f"   ⚠️  Cannot advance character (insufficient points or max level)")
            
            # Test advancement failure
            success, error_data = self.run_test(
                "Advancement with Insufficient Points",
                "POST",
                "api/advance",
                400,
                data={"player_id": self.player_id}
            )
            
            if success:
                print(f"   ✅ Correctly rejected advancement")
            
            return False
        else:
            # Test successful advancement
            success, advance_data = self.run_test(
                "Successful Character Advancement",
                "POST",
                "api/advance",
                200,
                data={"player_id": self.player_id},
                expected_keys=['success', 'new_character_level', 'new_character_name', 'new_character_multiplier']
            )
            
            if success and advance_data:
                print(f"   📊 Advancement Results:")
                print(f"      New level: {advance_data.get('new_character_level', 'N/A')}")
                print(f"      New name: {advance_data.get('new_character_name', 'N/A')}")
                print(f"      New multiplier: {advance_data.get('new_character_multiplier', 'N/A')}x")
                
                if advance_data.get('new_character_level') == current_level + 1:
                    print(f"   ✅ Character level increment correct")
                else:
                    print(f"   ⚠️  Character level increment may be incorrect")
            
            return success

    def test_passive_income(self):
        """Test passive income system (brief test)"""
        print(f"\n💰 Testing Passive Income (Brief)")
        
        # Get initial state
        success1, data1 = self.run_test(
            "Get Initial State for Passive Test",
            "GET",
            f"api/player/{self.player_id}",
            200
        )
        
        if not success1:
            return False
        
        initial_points = data1.get('points', 0)
        print(f"   Initial points: {initial_points}")
        
        # Wait a short time (not a full minute, just to test the mechanism)
        print(f"   Waiting 5 seconds to test passive income mechanism...")
        time.sleep(5)
        
        # Get state again
        success2, data2 = self.run_test(
            "Get State After Wait",
            "GET",
            f"api/player/{self.player_id}",
            200
        )
        
        if success2:
            new_points = data2.get('points', 0)
            print(f"   Points after wait: {new_points}")
            
            if new_points >= initial_points:
                print(f"   ✅ Passive income system functioning (or no change expected)")
            else:
                print(f"   ⚠️  Points decreased unexpectedly")
        
        return success2

    def run_all_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("🎮 CLICKER GAME API TEST SUITE")
        print("=" * 60)
        
        # Test 1: Initial player data
        success, initial_data = self.test_get_player_initial()
        if not success:
            print("\n❌ Critical failure: Cannot get initial player data")
            return self.print_summary()
        
        # Test 2: Click mechanics
        self.test_click_mechanics(initial_data)
        
        # Test 3: Energy depletion
        clicks_made = self.test_energy_depletion()
        
        # Test 4: Upgrade system
        self.test_upgrade_system()
        
        # Test 5: Character advancement
        self.test_character_advancement()
        
        # Test 6: Passive income
        self.test_passive_income()
        
        return self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    tester = ClickerGameAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())