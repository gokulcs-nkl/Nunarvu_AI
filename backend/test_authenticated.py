"""
Enhanced System Test with Authentication
=========================================
Tests all endpoints with proper authentication
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project101.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from app1.models import Student, Attendance, CameraConfiguration, BehaviourAlert, AttentionScore
from datetime import datetime, timedelta

class AuthenticatedSystemTest:
    def __init__(self):
        self.client = Client()
        self.user = None
        self.results = {
            'views': {},
            'apis': {},
            'models': {},
            'errors': []
        }
        self.passed = 0
        self.failed = 0
        self.setup_auth()
    
    def setup_auth(self):
        """Create test user and authenticate"""
        # Delete existing test user if any
        User.objects.filter(username='testadmin').delete()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testadmin',
            email='test@example.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        
        # Login
        self.client.login(username='testadmin', password='testpass123')
        print(f"✓ Authenticated as: {self.user.username}\n")
    
    def test_api(self, endpoint, method='GET', name=''):
        """Test an API endpoint"""
        try:
            url = f'/api{endpoint}'
            if method == 'GET':
                response = self.client.get(url, HTTP_ACCEPT='application/json')
            elif method == 'POST':
                response = self.client.post(url, {}, content_type='application/json')
            
            status_ok = 200 <= response.status_code < 400
            status_icon = '✓' if status_ok else '✗'
            
            self.results['apis'][name or endpoint] = f'{status_icon} [{response.status_code}]'
            
            if status_ok:
                self.passed += 1
            else:
                self.failed += 1
                self.results['errors'].append(f"{method} {endpoint}: {response.status_code}")
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        self.results['errors'].append(f"  Response: {error_data}")
                    except:
                        pass
            
            return response, status_ok
        except Exception as e:
            self.results['apis'][name or endpoint] = f'✗ ERROR'
            self.failed += 1
            self.results['errors'].append(f"{method} {endpoint}: {str(e)}")
            return None, False
    
    def run_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print(" AUTHENTICATED API TESTS")
        print("="*70 + "\n")
        
        print("📍 Configuration API Endpoints:")
        self.test_api('/config/behavior/', name='Config - Behavior')
        self.test_api('/config/optimization/', name='Config - Optimization')
        self.test_api('/config/detectors/', name='Config - Detectors')
        self.test_api('/config/thresholds/', name='Config - Thresholds')
        self.test_api('/config/audit/', name='Config - Audit Trail')
        
        print("\n📍 Behavior Analysis API Endpoints:")
        self.test_api('/behaviour-events/', name='Behaviour Events')
        self.test_api('/attention-scores/', name='Attention Scores')
        self.test_api('/behaviour-alerts/', name='Behaviour Alerts')
        
        print("\n📍 Other API Endpoints:")
        self.test_api('/students/', name='Students')
        self.test_api('/attendance/', name='Attendance')
        self.test_api('/cameras/', name='Cameras')
        
        # Print summary
        print("\n" + "="*70)
        print(" TEST RESULTS")
        print("="*70 + "\n")
        
        print(f"✓ PASSED: {self.passed}/{self.passed + self.failed}")
        print(f"✗ FAILED: {self.failed}/{self.passed + self.failed}")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%\n")
        
        if self.results['apis']:
            print("📋 API ENDPOINTS:")
            for name, result in self.results['apis'].items():
                print(f"  {name:40} {result}")
        
        if self.results['errors']:
            print(f"\n⚠️  Errors ({len(self.results['errors'])}):")
            for error in self.results['errors'][:10]:
                print(f"  {error}")
        
        print("\n" + "="*70 + "\n")
        
        return {
            'passed': self.passed,
            'failed': self.failed,
            'total': self.passed + self.failed,
            'pass_rate': f"{(self.passed / (self.passed + self.failed) * 100):.1f}%",
        }

if __name__ == '__main__':
    tester = AuthenticatedSystemTest()
    results = tester.run_tests()
    
    print("FINAL SUMMARY:")
    print(f"  Pass Rate: {results['pass_rate']}")
    print(f"  Status: {'✓ ALL TESTS PASSED' if results['failed'] == 0 else '⚠ SOME TESTS FAILED'}")
