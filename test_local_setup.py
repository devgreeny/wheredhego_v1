#!/usr/bin/env python3
"""
Test script for local SQLite development setup
"""

import os
import sys

# Set environment for local development
os.environ['USE_LOCAL_SQLITE'] = '1'

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_flask_app():
    """Test Flask app creation and database setup"""
    try:
        from app import create_app
        
        app = create_app()
        print("✅ Flask app created successfully")
        
        with app.app_context():
            # Test database creation
            from app.starting5.models import db
            from app.auth.sqlite_models import User, GameScore
            
            # Create all tables
            db.create_all()
            print("✅ SQLite database tables created successfully")
            
            # Test user creation
            test_user = User.create_user(
                username="test_local_user",
                email="test@local.dev",
                password="testpass123",
                display_name="Local Test User"
            )
            
            if test_user:
                print("✅ User creation successful")
                print(f"   User ID: {test_user.id}")
                print(f"   Username: {test_user.username}")
                print(f"   Display Name: {test_user.display_name}")
                
                # Test authentication
                auth_user = User.authenticate("test_local_user", "testpass123")
                if auth_user:
                    print("✅ User authentication successful")
                    
                    # Test score saving
                    success = auth_user.save_game_score(
                        game_type="starting5",
                        quiz_id="test_quiz_local",
                        score=7.5,
                        max_points=10.0,
                        time_taken=90,
                        metadata={"test": True, "local": True}
                    )
                    
                    if success:
                        print("✅ Score saving successful")
                        
                        # Test score retrieval
                        scores = auth_user.get_game_scores()
                        print(f"✅ Score retrieval successful: {len(scores)} scores found")
                        
                        # Test stats
                        stats = auth_user.get_stats_summary()
                        print(f"✅ Stats retrieval successful: {len(stats)} game types")
                        
                        return True
                    else:
                        print("❌ Score saving failed")
                else:
                    print("❌ User authentication failed")
            else:
                print("ℹ️  User creation skipped (might already exist)")
                return True
                
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_routes():
    """Test that routes are accessible"""
    try:
        from app import create_app
        
        app = create_app()
        
        with app.test_client() as client:
            # Test home page
            response = client.get('/')
            if response.status_code == 200:
                print("✅ Home page accessible")
            else:
                print(f"❌ Home page failed: {response.status_code}")
                return False
            
            # Test auth pages
            response = client.get('/auth/login')
            if response.status_code == 200:
                print("✅ Login page accessible")
            else:
                print(f"❌ Login page failed: {response.status_code}")
                return False
            
            response = client.get('/auth/register')
            if response.status_code == 200:
                print("✅ Register page accessible")
            else:
                print(f"❌ Register page failed: {response.status_code}")
                return False
            
            # Test game pages
            response = client.get('/starting5/')
            if response.status_code in [200, 302]:  # 302 for redirects
                print("✅ Starting5 page accessible")
            else:
                print(f"❌ Starting5 page failed: {response.status_code}")
            
            response = client.get('/gridiron11/')
            if response.status_code in [200, 302]:
                print("✅ Gridiron11 page accessible")
            else:
                print(f"❌ Gridiron11 page failed: {response.status_code}")
            
            return True
            
    except Exception as e:
        print(f"❌ Routes test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 Testing Local SQLite Setup")
    print("=" * 40)
    
    tests = [
        ("Flask App & Database", test_flask_app),
        ("Route Accessibility", test_routes)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"   ⚠️  {test_name} test failed")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Local setup is working!")
        print("\n📝 Next steps:")
        print("   1. Run: python3 run.py")
        print("   2. Visit: http://localhost:5000")
        print("   3. Test registration and login")
        print("   4. Play games and check score tracking")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
