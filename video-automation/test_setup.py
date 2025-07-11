#!/usr/bin/env python3
"""
Test script to verify all components are working
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_env_vars():
    """Check if all required environment variables are set"""
    required_vars = [
        'GOOGLE_SHEETS_CREDENTIALS_PATH',
        'SPREADSHEET_ID',
        'GROK_API_KEY',
        'FAL_API_KEY',
        'YOUTUBE_CLIENT_SECRETS_PATH'
    ]
    
    print("Checking environment variables...")
    missing = []
    for var in required_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is missing")
            missing.append(var)
    
    if missing:
        print(f"\nPlease set the following in your .env file: {', '.join(missing)}")
        return False
    return True

def test_imports():
    """Test if all required packages are installed"""
    print("\nChecking package imports...")
    packages = [
        ('gspread', 'gspread'),
        ('google.oauth2', 'google-auth'),
        ('googleapiclient', 'google-api-python-client'),
        ('loguru', 'loguru'),
        ('fal_client', 'fal-client'),
        ('requests', 'requests'),
        ('schedule', 'schedule')
    ]
    
    missing = []
    for module, package in packages:
        try:
            __import__(module)
            print(f"✓ {module} imported successfully")
        except ImportError:
            print(f"✗ {module} import failed")
            missing.append(package)
    
    if missing:
        print(f"\nInstall missing packages: pip install {' '.join(missing)}")
        return False
    return True

def test_file_structure():
    """Check if required directories exist"""
    print("\nChecking file structure...")
    dirs = ['config', 'logs', 'output']
    
    for dir_name in dirs:
        if os.path.exists(dir_name):
            print(f"✓ {dir_name}/ directory exists")
        else:
            print(f"✗ {dir_name}/ directory missing - creating...")
            os.makedirs(dir_name)

def main():
    print("Video Automation Setup Test\n" + "="*30)
    
    # Test file structure
    test_file_structure()
    
    # Test imports
    imports_ok = test_imports()
    
    # Test environment variables
    env_ok = test_env_vars()
    
    print("\n" + "="*30)
    if imports_ok and env_ok:
        print("✓ All tests passed! Ready to run video automation.")
    else:
        print("✗ Setup incomplete. Please fix the issues above.")

if __name__ == "__main__":
    main()