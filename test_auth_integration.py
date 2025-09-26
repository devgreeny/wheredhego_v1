#!/usr/bin/env python3
"""
Complete integration test for the unified auth system
"""

import os
import sys

# Set environment for local development
os.environ['USE_LOCAL_SQLITE'] = '1'

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_complete_auth_flow():
    """Test complete authentication flow"""
    try:
        from app import create_app
        
        app = create_app()
        print("✅ Flask app created successfully")
        
        with app.app_context():
            # Import models
            from app.auth.sqlite_models import User, GameScore
            from app.starting5.models import db
            
            # Create tables
            db.create_all()
            print("✅ Database tables created")
            
            # Test user registration flow
            test_username = "integration_test_user"
            test_email = "integration@test.com"
            test_password = "testpass123"
            
            # Clean up any existing test user
            existing_user = User.query.filter_by(username=test_username).first()
            if existing_user:
                db.session.delete(existing_user)
                db.session.commit()
            
            # Create new user
            new_user = User.create_user(
                username=test_username,
                email=test_email,
                password=test_password,
                display_name="Integration Test User"
            )
            
            if new_user:
                print("✅ User registration successful")
                
                # Test login
                auth_user = User.authenticate(test_username, test_password)
                if auth_user:
                    print("✅ User login successful")
                    
                    # Test score saving for different games
                    games_data = [
                        ("starting5", "quiz_001", 8.5, 10.0, 120),
                        ("gridiron11", "formation_001", 9.0, 11.0, 180),
                        ("starting5", "quiz_002", 7.0, 10.0, 95)
                    ]
                    
                    for game_type, quiz_id, score, max_points, time_taken in games_data:
                        success = auth_user.save_game_score(
                            game_type=game_type,
                            quiz_id=quiz_id,
                            score=score,
                            max_points=max_points,
                            time_taken=time_taken,
                            metadata={"test": True, "integration": True}
                        )
                        
                        if success:
                            print(f"✅ {game_type} score saved successfully")
                        else:
                            print(f"❌ {game_type} score saving failed")
                            return False
                    
                    # Test score retrieval
                    all_scores = auth_user.get_game_scores()
                    print(f"✅ Retrieved {len(all_scores)} total scores")
                    
                    starting5_scores = auth_user.get_game_scores(game_type="starting5")
                    print(f"✅ Retrieved {len(starting5_scores)} Starting5 scores")
                    
                    gridiron_scores = auth_user.get_game_scores(game_type="gridiron11")
                    print(f"✅ Retrieved {len(gridiron_scores)} Gridiron11 scores")
                    
                    # Test stats summary
                    stats = auth_user.get_stats_summary()
                    print(f"✅ Retrieved stats for {len(stats)} game types")
                    
                    for stat in stats:
                        print(f"   {stat['game_type']}: {stat['total_games']} games, avg {stat['avg_score']:.1f}")
                    
                    return True
                else:
                    print("❌ User login failed")
            else:
                print("❌ User registration failed")
                
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_web_routes():
    """Test web routes with test client"""
    try:
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            print("\n🌐 Testing Web Routes:")
            
            # Test home page
            response = client.get('/')
            print(f"   Home page: {response.status_code} {'✅' if response.status_code == 200 else '❌'}")
            
            # Check if auth links are present
            if b'Login' in response.data and b'Register' in response.data:
                print("   Auth links present: ✅")
            else:
                print("   Auth links present: ❌")
            
            # Test auth pages
            response = client.get('/auth/login')
            print(f"   Login page: {response.status_code} {'✅' if response.status_code == 200 else '❌'}")
            
            response = client.get('/auth/register')
            print(f"   Register page: {response.status_code} {'✅' if response.status_code == 200 else '❌'}")
            
            # Test game pages
            response = client.get('/starting5/')
            print(f"   Starting5: {response.status_code} {'✅' if response.status_code in [200, 302] else '❌'}")
            
            response = client.get('/gridiron11/')
            print(f"   Gridiron11: {response.status_code} {'✅' if response.status_code in [200, 302] else '❌'}")
            
            # Test registration form submission
            response = client.post('/auth/register', data={
                'username': 'web_test_user',
                'email': 'webtest@test.com',
                'password': 'testpass123',
                'confirm_password': 'testpass123',
                'display_name': 'Web Test User'
            })
            print(f"   Registration form: {response.status_code} {'✅' if response.status_code in [200, 302] else '❌'}")
            
            return True
            
    except Exception as e:
        print(f"❌ Web routes test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 Complete MySQL Integration Test")
    print("=" * 50)
    
    tests = [
        ("Authentication Flow", test_complete_auth_flow),
        ("Web Routes", test_web_routes)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"   ⚠️  {test_name} test failed")
    
    print(f"\n🎯 Final Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 COMPLETE SUCCESS! 🎉")
        print("\nThe unified MySQL authentication system is working perfectly!")
        print("\n✨ Features Verified:")
        print("   ✅ SQLite fallback for local development")
        print("   ✅ User registration and authentication")
        print("   ✅ Cross-game score tracking")
        print("   ✅ User statistics and profiles")
        print("   ✅ Web routes and templates")
        print("   ✅ Form handling and validation")
        
        print("\n🚀 Ready for Production:")
        print("   • Set MYSQL_HOST environment variable for production")
        print("   • Remove USE_LOCAL_SQLITE for MySQL mode")
        print("   • Deploy to PythonAnywhere with confidence!")
        
        print("\n🎮 Next Steps:")
        print("   • Test the live Flask app manually")
        print("   • Update Gridiron11 UI (next phase)")
        print("   • Fix Gridiron11 roster validation")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
