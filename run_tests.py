# Test Runner Script
# run_tests.py
#!/usr/bin/env python3

import subprocess
import sys
import os
from pathlib import Path

def run_backend_tests():
    """Run backend tests"""
    print("🧪 Running backend tests...")
    
    os.chdir("backend")
    
    # Install test dependencies
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"], check=True)
    
    # Run tests with coverage
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--cov=app",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--tb=short"
    ])
    
    os.chdir("..")
    return result.returncode == 0

def run_frontend_tests():
    """Run frontend tests"""
    print("🧪 Running frontend tests...")
    
    os.chdir("frontend")
    
    # Install dependencies
    subprocess.run(["npm", "install"], check=True)
    
    # Run tests
    result = subprocess.run(["npm", "test", "--", "--coverage", "--watchAll=false"])
    
    os.chdir("..")
    return result.returncode == 0

def run_integration_tests():
    """Run integration tests"""
    print("🧪 Running integration tests...")
    
    # Start services for testing
    subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"], check=True)
    
    try:
        # Wait for services to be ready
        import time
        time.sleep(30)
        
        # Run integration tests
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/integration/",
            "-v",
            "--tb=short"
        ])
        
        return result.returncode == 0
    
    finally:
        # Clean up
        subprocess.run(["docker-compose", "-f", "docker-compose.test.yml", "down"])

def main():
    """Main test runner"""
    print("🚀 Running UGENE Web Platform test suite...")
    
    backend_passed = run_backend_tests()
    frontend_passed = run_frontend_tests()
    integration_passed = run_integration_tests()
    
    print("\n" + "="*50)
    print("📊 Test Results:")
    print(f"Backend Tests: {'✅ PASSED' if backend_passed else '❌ FAILED'}")
    print(f"Frontend Tests: {'✅ PASSED' if frontend_passed else '❌ FAILED'}")
    print(f"Integration Tests: {'✅ PASSED' if integration_passed else '❌ FAILED'}")
    
    all_passed = backend_passed and frontend_passed and integration_passed
    
    if all_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()