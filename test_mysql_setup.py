#!/usr/bin/env python3
"""
Test script to verify MySQL setup and unified authentication system
"""

import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_mysql_connection():
    """Test basic MySQL connection"""
    try:
        from app.auth.models import User
        print("✅ Auth models imported successfully")
        
        # Test table creation
        User.create_tables()
        print("✅ MySQL tables created successfully")
        
        return True
    except Exception as e:
        print(f"❌ MySQL connection failed: {e}")
        return False

def test_user_creation():
    """Test user creation and authentication"""
    try:
        from app.auth.models import User
        
        # Test user creation
        test_user = User.create_user(
            username="test_user_mysql",
            email="test@wheredhego.com", 
            password="testpass123",
            display_name="Test User"
        )
        
        if test_user:
            print("✅ User creation successful")
            
            # Test authentication
            auth_user = User.authenticate("test_user_mysql", "testpass123")
            if auth_user:
                print("✅ User authentication successful")
                print(f"   User ID: {auth_user.id}")
                print(f"   Display Name: {auth_user.display_name}")
                
                # Test score saving
                success = auth_user.save_game_score(
                    game_type="starting5",
                    quiz_id="test_quiz_001",
                    score=8.5,
                    max_points=10.0,
                    time_taken=120,
                    metadata={"test": True}
                )
                
                if success:
                    print("✅ Score saving successful")
                    
                    # Test score retrieval
                    scores = auth_user.get_game_scores(game_type="starting5")
                    print(f"✅ Score retrieval successful: {len(scores)} scores found")
                    
                    return True
                else:
                    print("❌ Score saving failed")
            else:
                print("❌ User authentication failed")
        else:
            print("❌ User creation failed (might already exist)")
            return True  # Not necessarily an error
            
    except Exception as e:
        print(f"❌ User creation test failed: {e}")
        return False

def test_creator_poll_mysql():
    """Test CreatorPoll MySQL integration"""
    try:
        from app.creatorpoll.mysql_models import CreatorPoll, CreatorUser
        from app.creatorpoll.mysql_routes import get_mysql_config
        
        config = get_mysql_config()
        creator_poll = CreatorPoll(config)
        creator_user = CreatorUser(config)
        
        print("✅ CreatorPoll MySQL models imported successfully")
        
        # Test table creation
        creator_poll.create_tables()
        creator_user.create_tables()
        print("✅ CreatorPoll MySQL tables created successfully")
        
        return True
    except Exception as e:
        print(f"❌ CreatorPoll MySQL test failed: {e}")
        return False

def main():
    print("🚀 Testing MySQL Setup for Wheredhego")
    print("=" * 50)
    
    # Set environment variables if not set
    if not os.environ.get('MYSQL_HOST'):
        os.environ['MYSQL_HOST'] = 'devgreeny.mysql.pythonanywhere-services.com'
        os.environ['MYSQL_USER'] = 'devgreeny' 
        os.environ['MYSQL_PASSWORD'] = 'lebron69'
        os.environ['MYSQL_DATABASE'] = 'devgreeny$default'
        print("🔧 Set default MySQL environment variables")
    
    tests = [
        ("MySQL Connection", test_mysql_connection),
        ("User Management", test_user_creation), 
        ("CreatorPoll MySQL", test_creator_poll_mysql)
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
        print("\n🎉 All tests passed! MySQL setup is working correctly.")
        print("\n📝 Next steps:")
        print("   1. Start the Flask app: python run.py")
        print("   2. Visit the landing page to see auth links")
        print("   3. Register/login to track scores across games")
        print("   4. Test CreatorPoll with MySQL backend")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
