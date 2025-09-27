#!/usr/bin/env python3

import os
import sys
import subprocess
from pathlib import Path
##generic template for start
def check_requirements():
    try:
        import flask
        import flask_sqlalchemy
        import flask_bcrypt
        import flask_cors
        print("Python Requirements satisfied")
        return True
    except ImportError as e:
        print(f"❌ Missing requirement: {e}")
        print("Please run: pip install -r backend/requirements.txt")
        return False

def setup_directories():
    directories = [
        'backend',
        'frontend/static/css',
        'frontend/static/js',
        'frontend/static/images',
        'frontend/templates',
        'docs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("Directory verified")

def run_application():
    # Change to backend directory
    os.chdir('backend')
    
    # Setting Flask env vars
    os.environ['FLASK_APP'] = 'app.py'
    os.environ['FLASK_ENV'] = 'development'
    
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(" Starting TTBFP...")
    print(f"Open your browser and navigate to: http://localhost:5000 for web version. I suggest doing so on your phone/bluestacks at http://{local_ip}:5000")
    print("=" * 50)
    
    try:
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error running application: {e}")

def main():
    print("=" * 50)
    print("🎵 TTBFP - Starting")
    print("=" * 50)
    
    # dir check
    if not Path('backend/app.py').exists():
        print("❌ Please run this script from the ttbfp1 directory")
        print("   The directory should contain: backend/, frontend/, docs/")
        sys.exit(1)
    
   
    setup_directories()
    
    if not check_requirements():
        print("\nTo install requirements, run:")
        print("cd backend && pip install -r requirements.txt")
        sys.exit(1)
    
    run_application()

if __name__ == "__main__":
    main()