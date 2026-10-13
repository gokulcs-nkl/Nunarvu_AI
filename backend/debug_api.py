"""
Detailed API Endpoint Testing Script
====================================
Tests each API endpoint and shows specific errors
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project101.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.urls import get_resolver, URLPattern
import traceback

def test_url_patterns():
    """Test if all URL patterns are registered"""
    print("\n" + "="*70)
    print(" URL PATTERN ANALYSIS")
    print("="*70 + "\n")
    
    resolver = get_resolver()
    
    # Find API patterns
    api_patterns = []
    for pattern in resolver.url_patterns:
        pattern_str = str(pattern.pattern)
        if 'api' in pattern_str:
            api_patterns.append(pattern_str)
    
    print(f"Found {len(api_patterns)} API-related URL patterns:\n")
    for pattern in api_patterns:
        print(f"  ✓ {pattern}")
    
    return api_patterns

def test_specific_endpoints():
    """Test specific endpoints"""
    print("\n" + "="*70)
    print(" ENDPOINT TESTS")
    print("="*70 + "\n")
    
    client = Client()
    
    endpoints = [
        ('/api/', 'API Root'),
        ('/api/students/', 'Students'),
        ('/api/attendance/', 'Attendance'),
        ('/api/cameras/', 'Cameras'),
        ('/api/behaviour-events/', 'Behaviour Events'),
        ('/api/attention-scores/', 'Attention Scores'),
        ('/api/behaviour-alerts/', 'Behaviour Alerts'),
        ('/api/config/behavior/', 'Config - Behavior'),
        ('/api/config/optimization/', 'Config - Optimization'),
        ('/api/config/detectors/', 'Config - Detectors'),
        ('/api/config/thresholds/', 'Config - Thresholds'),
        ('/api/config/audit/', 'Config - Audit'),
        ('/api/schema/', 'API Schema'),
        ('/api/docs/', 'API Docs (Swagger)'),
    ]
    
    for url, name in endpoints:
        try:
            response = client.get(url, HTTP_ACCEPT='application/json')
            status_icon = '✓' if 200 <= response.status_code < 400 else '✗'
            print(f"{status_icon} {name:30} {url:40} [{response.status_code}]")
            
            if response.status_code >= 400:
                # Try to parse error
                try:
                    error_data = response.json()
                    print(f"    Error: {error_data}")
                except:
                    print(f"    Body: {response.content[:100]}")
        except Exception as e:
            print(f"✗ {name:30} {url:40} [ERROR]")
            print(f"    Exception: {str(e)}")

def test_imports():
    """Test if all API modules import correctly"""
    print("\n" + "="*70)
    print(" IMPORT TESTS")
    print("="*70 + "\n")
    
    import_tests = [
        ('app1.api_views', 'Main API Views'),
        ('app1.behavior_api_views', 'Behavior API Views'),
        ('app1.configuration_api', 'Configuration API'),
        ('app1.configuration_models', 'Configuration Models'),
    ]
    
    for module_name, desc in import_tests:
        try:
            __import__(module_name)
            print(f"✓ {desc:40} ({module_name})")
        except Exception as e:
            print(f"✗ {desc:40} ({module_name})")
            print(f"    Error: {str(e)}")
            traceback.print_exc()

def test_model_count():
    """Check if configuration models have data"""
    print("\n" + "="*70)
    print(" DATABASE CHECKS")
    print("="*70 + "\n")
    
    try:
        from app1.configuration_models import (
            BehaviorConfig, OptimizationConfig, DetectorConfig,
            ThresholdConfig, ConfigurationAudit
        )
        
        print(f"BehaviorConfig records: {BehaviorConfig.objects.count()}")
        print(f"OptimizationConfig records: {OptimizationConfig.objects.count()}")
        print(f"DetectorConfig records: {DetectorConfig.objects.count()}")
        print(f"ThresholdConfig records: {ThresholdConfig.objects.count()}")
        print(f"ConfigurationAudit records: {ConfigurationAudit.objects.count()}")
    except Exception as e:
        print(f"Error accessing configuration models: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    print("\n" + "🔍 COMPREHENSIVE API DEBUGGING" + "\n")
    
    test_imports()
    test_url_patterns()
    test_model_count()
    test_specific_endpoints()
    
    print("\n" + "="*70 + "\n")
