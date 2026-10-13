"""
Comprehensive System Testing Script
===================================
Tests all major components: views, APIs, templates, and functionality
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project101.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client, TestCase
from django.contrib.auth.models import User
from app1.models import Student, Attendance, CameraConfiguration, BehaviourAlert, AttentionScore
from datetime import datetime, timedelta
import json

class SystemTest:
    def __init__(self):
        self.client = Client()
        self.results = {
            'views': {},
            'apis': {},
            'models': {},
            'errors': []
        }
        self.passed = 0
        self.failed = 0
    
    def test_view(self, url, method='GET', name=''):
        """Test a view endpoint"""
        try:
            if method == 'GET':
                response = self.client.get(url)
            elif method == 'POST':
                response = self.client.post(url, {})
            
            result = {
                'status': response.status_code,
                'method': method,
                'url': url
            }
            
            if 200 <= response.status_code < 400:
                self.results['views'][name or url] = '✓ PASS'
                self.passed += 1
            else:
                self.results['views'][name or url] = f'✗ FAIL ({response.status_code})'
                self.failed += 1
                self.results['errors'].append(f"{method} {url}: {response.status_code}")
            
            return response
        except Exception as e:
            self.results['views'][name or url] = f'✗ ERROR: {str(e)}'
            self.failed += 1
            self.results['errors'].append(f"{method} {url}: {str(e)}")
            return None
    
    def test_api(self, endpoint, method='GET', name=''):
        """Test an API endpoint"""
        try:
            url = f'/api{endpoint}'
            if method == 'GET':
                response = self.client.get(url, HTTP_ACCEPT='application/json')
            elif method == 'POST':
                response = self.client.post(url, {}, content_type='application/json')
            
            if 200 <= response.status_code < 400:
                self.results['apis'][name or endpoint] = '✓ PASS'
                self.passed += 1
            else:
                self.results['apis'][name or endpoint] = f'✗ FAIL ({response.status_code})'
                self.failed += 1
                self.results['errors'].append(f"{method} {endpoint}: {response.status_code}")
                if response.content:
                    self.results['errors'].append(f"  Response: {response.content[:200].decode()}")
            
            return response
        except Exception as e:
            self.results['apis'][name or endpoint] = f'✗ ERROR: {str(e)}'
            self.failed += 1
            self.results['errors'].append(f"{method} {endpoint}: {str(e)}")
            return None
    
    def test_models(self):
        """Test database models"""
        try:
            # Test Student model
            student_count = Student.objects.count()
            self.results['models']['Student'] = f'✓ {student_count} records'
            
            # Test Attendance model
            attendance_count = Attendance.objects.count()
            self.results['models']['Attendance'] = f'✓ {attendance_count} records'
            
            # Test CameraConfiguration model
            camera_count = CameraConfiguration.objects.count()
            self.results['models']['CameraConfiguration'] = f'✓ {camera_count} records'
            
            # Test BehaviourAlert model
            alert_count = BehaviourAlert.objects.count()
            self.results['models']['BehaviourAlert'] = f'✓ {alert_count} records'
            
            # Test AttentionScore model
            score_count = AttentionScore.objects.count()
            self.results['models']['AttentionScore'] = f'✓ {score_count} records'
            
            self.passed += 5
        except Exception as e:
            self.results['models']['ERROR'] = str(e)
            self.failed += 1
            self.results['errors'].append(f"Model test error: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print(" COMPREHENSIVE SYSTEM TEST")
        print("="*70 + "\n")
        
        # Test Views
        print("📍 TESTING VIEWS...")
        self.test_view('/home/', name='Dashboard (Home)')
        self.test_view('/students/', name='Student List')
        self.test_view('/students/attendance/', name='Attendance List')
        self.test_view('/manual-check-in-out/', name='Manual Check-in-out')
        self.test_view('/capture-and-recognize/', name='Capture & Recognize')
        self.test_view('/behavior-dashboard/', name='Behavior Dashboard')
        self.test_view('/student-attention/', name='Student Attention')
        self.test_view('/behavior-analytics/', name='Behavior Analytics')
        
        # Test APIs
        print("📍 TESTING API ENDPOINTS...")
        self.test_api('/config/behavior/', name='Config - Behavior')
        self.test_api('/config/optimization/', name='Config - Optimization')
        self.test_api('/config/detectors/', name='Config - Detectors')
        self.test_api('/config/thresholds/', name='Config - Thresholds')
        self.test_api('/config/audit/', name='Config - Audit')
        self.test_api('/performance/metrics/', name='Performance - Metrics')
        self.test_api('/behavior/alerts/', name='Behavior - Alerts')
        self.test_api('/behavior/events/', name='Behavior - Events')
        self.test_api('/behavior/scores/', name='Behavior - Scores')
        
        # Test Models
        print("📍 TESTING DATABASE MODELS...")
        self.test_models()
        
        # Print Results
        print("\n" + "="*70)
        print(" TEST RESULTS")
        print("="*70 + "\n")
        
        print(f"✓ PASSED: {self.passed}")
        print(f"✗ FAILED: {self.failed}")
        print(f"Total: {self.passed + self.failed}\n")
        
        if self.results['views']:
            print("📍 VIEWS:")
            for name, result in self.results['views'].items():
                print(f"  {name}: {result}")
        
        if self.results['apis']:
            print("\n📍 APIS:")
            for name, result in self.results['apis'].items():
                print(f"  {name}: {result}")
        
        if self.results['models']:
            print("\n📍 MODELS:")
            for name, result in self.results['models'].items():
                print(f"  {name}: {result}")
        
        if self.results['errors']:
            print("\n📋 ERRORS DETECTED:")
            for error in self.results['errors'][:20]:  # Show first 20
                print(f"  ⚠ {error}")
        
        print("\n" + "="*70 + "\n")
        
        return {
            'passed': self.passed,
            'failed': self.failed,
            'total': self.passed + self.failed,
            'pass_rate': f"{(self.passed / (self.passed + self.failed) * 100):.1f}%" if (self.passed + self.failed) > 0 else "N/A",
            'errors': self.results['errors']
        }

if __name__ == '__main__':
    tester = SystemTest()
    results = tester.run_all_tests()
    
    # Print summary
    print("FINAL SUMMARY:")
    print(f"  Pass Rate: {results['pass_rate']}")
    print(f"  Passed: {results['passed']}/{results['total']}")
    print(f"  Failed: {results['failed']}/{results['total']}")
