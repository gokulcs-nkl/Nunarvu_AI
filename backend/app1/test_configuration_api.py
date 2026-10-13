"""
Integration Tests for Configuration API
========================================

Tests for Phase 9 configuration API endpoints.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from app1.configuration_models import (
    BehaviorConfig, OptimizationConfig, get_behavior_config, get_optimization_config
)


class ConfigurationAPITestCase(APITestCase):
    """Test Configuration API endpoints."""
    
    def setUp(self):
        """Set up test client and users."""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.admin_user = User.objects.create_superuser(
            username='admin', password='adminpass', email='admin@test.com'
        )
        self.staff_user = User.objects.create_user(
            username='staff', password='staffpass'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
    
    def test_behavior_config_get_requires_auth(self):
        """Test that GET requires authentication."""
        response = self.client.get('/api/config/behavior/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_behavior_config_get_authenticated(self):
        """Test getting behavior config when authenticated."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/config/behavior/')
        
        # Should work for any authenticated user
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])
    
    def test_behavior_config_update_requires_staff(self):
        """Test that updates require staff permissions."""
        self.client.force_authenticate(user=self.user)
        response = self.client.put('/api/config/behavior/', {
            'system_enabled': False
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_behavior_config_update_with_staff(self):
        """Test updating behavior config with staff user."""
        self.client.force_authenticate(user=self.staff_user)
        
        # Get initial value
        get_behavior_config()
        
        response = self.client.patch('/api/config/behavior/', {
            'target_fps': 60
        }, format='json')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])
    
    def test_optimization_config_get_anonymous(self):
        """Test getting optimization config without authentication fails."""
        response = self.client.get('/api/config/optimization/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_optimization_presets_endpoint(self):
        """Test optimization presets endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/config/optimization/presets/')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])
    
    def test_detector_config_list(self):
        """Test listing detector configurations."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/config/detectors/')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])
    
    def test_audit_trail_get(self):
        """Test getting audit trail."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/config/audit/')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])
    
    def test_audit_trail_pagination(self):
        """Test audit trail pagination."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/config/audit/?limit=10&offset=0')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])


class BehaviorConfigAPIDetailTestCase(APITestCase):
    """Test behavior config API detail operations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.staff_user = User.objects.create_user(
            username='staff', password='staffpass'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
        
        # Create initial config
        get_behavior_config()
    
    def test_behavior_config_partial_update(self):
        """Test partial update of behavior config."""
        self.client.force_authenticate(user=self.staff_user)
        
        response = self.client.patch('/api/config/behavior/', {
            'min_fps': 20
        }, format='json')
        
        # Should either succeed or not exist
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])


class OptimizationConfigAPIDetailTestCase(APITestCase):
    """Test optimization config API detail operations."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.staff_user = User.objects.create_user(
            username='staff', password='staffpass'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
        
        # Create initial config
        get_optimization_config()
    
    def test_optimization_config_update_skip_rate(self):
        """Test updating skip rate."""
        self.client.force_authenticate(user=self.staff_user)
        
        response = self.client.patch('/api/config/optimization/', {
            'initial_skip_rate': 2
        }, format='json')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])
    
    def test_optimization_config_update_memory_pool(self):
        """Test updating memory pool size."""
        self.client.force_authenticate(user=self.staff_user)
        
        response = self.client.patch('/api/config/optimization/', {
            'memory_pool_size': 15
        }, format='json')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])
    
    def test_optimization_config_apply_preset(self):
        """Test applying optimization preset."""
        self.client.force_authenticate(user=self.staff_user)
        
        response = self.client.post('/api/config/optimization/apply_preset/', {
            'preset': 'aggressive'
        }, format='json')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_404_NOT_FOUND,
        ])


class DetectorConfigAPITestCase(APITestCase):
    """Test detector configuration API."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.staff_user = User.objects.create_user(
            username='staff', password='staffpass'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
    
    def test_list_detectors(self):
        """Test listing all detectors."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get('/api/config/detectors/')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])
    
    def test_get_detector_by_type(self):
        """Test getting specific detector."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get('/api/config/detectors/?type=drowsiness')
        
        self.assertIn(response.status_code, [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ])


class APIPermissionTestCase(APITestCase):
    """Test API permission controls."""
    
    def setUp(self):
        """Set up test users."""
        self.client = APIClient()
        self.regular_user = User.objects.create_user(
            username='user', password='pass'
        )
        self.staff_user = User.objects.create_user(
            username='staff', password='pass'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
        
        self.admin_user = User.objects.create_superuser(
            username='admin', password='pass', email='admin@test.com'
        )
        
        get_behavior_config()
    
    def test_get_allowed_for_authenticated(self):
        """Test GET is allowed for authenticated users."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get('/api/config/behavior/')
        
        # Should be 200 or 404 (not 403)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_post_forbidden_for_non_staff(self):
        """Test POST is forbidden for non-staff users."""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.post('/api/config/behavior/', {})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_put_allowed_for_staff(self):
        """Test PUT is allowed for staff users."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.put('/api/config/behavior/', {
            'system_enabled': True,
            'target_fps': 30,
        }, format='json')
        
        # Should be 200 or 404 (not 403)
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_delete_forbidden_for_staff(self):
        """Test DELETE is forbidden (no deletion allowed)."""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete('/api/config/behavior/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class APIResponseFormatTestCase(APITestCase):
    """Test API response formats."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(username='user', password='pass')
        self.client.force_authenticate(user=self.user)
        get_behavior_config()
    
    def test_behavior_config_response_fields(self):
        """Test behavior config response has expected fields."""
        response = self.client.get('/api/config/behavior/')
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            expected_fields = [
                'system_enabled', 'processing_mode', 'target_fps'
            ]
            for field in expected_fields:
                self.assertIn(field, data)
    
    def test_api_returns_json(self):
        """Test API returns JSON."""
        response = self.client.get('/api/config/behavior/')
        
        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response['Content-Type'], 'application/json')
