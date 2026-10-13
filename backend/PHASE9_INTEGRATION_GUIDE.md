# Phase 9: Configuration System Integration Guide

**How to Integrate Configuration Management with Phase 8 Performance Optimizer**

---

## 🎯 Overview

This guide shows how to:
1. Load Phase 9 configuration in Phase 8 optimizer
2. Apply dynamic configuration at runtime
3. Synchronize optimization settings with database
4. Create configuration change listeners

---

## 🔄 Integration Architecture

```
┌─────────────────────────────────┐
│   Phase 9: Configuration UI     │
│  (Admin, API, Forms, Audit)     │
└────────────┬────────────────────┘
             │ Stores/retrieves
             ▼
┌─────────────────────────────────┐
│  Configuration Database Models  │
│  (BehaviorConfig, etc.)         │
└────────────┬────────────────────┘
             │ Loads on startup
             ▼
┌─────────────────────────────────┐
│   Phase 8: Performance Optimizer│
│  (Frame Skip, Resolution, etc.) │
└─────────────────────────────────┘
```

---

## 📋 Integration Steps

### Step 1: Modify Performance Optimizer

Update `/backend/app1/performance_optimizer.py` to load configuration:

```python
# Add to imports
from .configuration_models import get_optimization_config

# Modify AdaptiveOptimizer.__init__()
class AdaptiveOptimizer:
    def __init__(self, enable_caching=True, load_config=True):
        self.enable_caching = enable_caching
        
        # ... existing initialization code ...
        
        # ADDED: Load configuration on startup
        if load_config:
            self._load_configuration()
    
    def _load_configuration(self):
        """Load optimization configuration from database."""
        try:
            config = get_optimization_config()
            
            # Apply frame skip configuration
            if config.frame_skip_enabled:
                self.frame_skipper.set_skip_rate(config.initial_skip_rate)
                self.frame_skipper.max_skip_rate = config.max_skip_rate
            else:
                self.frame_skipper.set_skip_rate(1)
            
            # Apply resolution adaptation configuration
            if config.resolution_adapt_enabled:
                self.resolution_adapter.enable()
                self.resolution_adapter.cpu_threshold_low = config.cpu_threshold_low
                self.resolution_adapter.cpu_threshold_mid = config.cpu_threshold_mid
                self.resolution_adapter.cpu_threshold_high = config.cpu_threshold_high
            else:
                self.resolution_adapter.disable()
            
            # Apply memory pool configuration
            if config.memory_pool_enabled:
                self.memory_pool.resize(config.memory_pool_size)
            
            # Apply CPU throttling configuration
            if config.cpu_throttle_enabled:
                self.cpu_throttler.enable()
                self.cpu_throttler.max_cpu = config.cpu_throttle_max
            else:
                self.cpu_throttler.disable()
            
            # Apply caching configuration
            if config.cache_enabled:
                self.cache_manager.enable()
                self.cache_manager.set_ttl('scores', config.cache_ttl_scores)
                self.cache_manager.set_ttl('alerts', config.cache_ttl_alerts)
                self.cache_manager.set_ttl('stats', config.cache_ttl_stats)
            else:
                self.cache_manager.disable()
            
            print(f"[OPTIMIZER] Configuration loaded successfully")
            
        except Exception as e:
            print(f"[OPTIMIZER] Failed to load configuration: {e}")
            print("[OPTIMIZER] Using default settings")
    
    def reload_configuration(self):
        """Reload configuration from database at runtime."""
        self._load_configuration()
```

### Step 2: Add Configuration Update Handler

Add this to `performance_optimizer.py`:

```python
def apply_optimization_config(self, config):
    """Apply optimization configuration object."""
    # Frame skipping
    self.frame_skipper.enabled = config.frame_skip_enabled
    self.frame_skipper.set_skip_rate(config.initial_skip_rate)
    self.frame_skipper.max_skip_rate = config.max_skip_rate
    
    # Resolution adaptation
    self.resolution_adapter.enabled = config.resolution_adapt_enabled
    self.resolution_adapter.cpu_threshold_low = config.cpu_threshold_low
    self.resolution_adapter.cpu_threshold_mid = config.cpu_threshold_mid
    self.resolution_adapter.cpu_threshold_high = config.cpu_threshold_high
    
    # Memory pooling
    if config.memory_pool_enabled:
        self.memory_pool.resize(config.memory_pool_size)
    
    # CPU throttling
    self.cpu_throttler.enabled = config.cpu_throttle_enabled
    self.cpu_throttler.max_cpu = config.cpu_throttle_max
    
    # Caching
    self.cache_manager.enabled = config.cache_enabled
    if config.cache_enabled:
        self.cache_manager.set_ttl('scores', config.cache_ttl_scores)
        self.cache_manager.set_ttl('alerts', config.cache_ttl_alerts)
        self.cache_manager.set_ttl('stats', config.cache_ttl_stats)
```

### Step 3: Modify Behavior Thread

Update `/backend/app1/behavior_thread_optimized.py`:

```python
# Add to imports
from .configuration_models import (
    get_behavior_config,
    get_optimization_config,
    get_detector_config,
)

# In start_behavior_analysis() function, add:
def start_behavior_analysis():
    """Start behavior analysis thread with configuration."""
    
    # Load behavior configuration
    behavior_config = get_behavior_config()
    
    if not behavior_config.system_enabled:
        print("[BEHAVIOR] System disabled in configuration")
        return
    
    # Load optimization configuration and apply to optimizer
    optimizer = get_optimizer()
    optimizer.reload_configuration()
    
    # Continue with existing code
    # ...
```

### Step 4: Create Configuration Change Listener

Create `/backend/app1/configuration_listener.py`:

```python
"""
Configuration Change Listener
==============================

Django signals to react to configuration changes in real-time.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .configuration_models import (
    OptimizationConfig,
    BehaviorConfig,
    DetectorConfig,
)


@receiver(post_save, sender=OptimizationConfig)
def on_optimization_config_changed(sender, instance, created, **kwargs):
    """
    React to optimization configuration changes.
    
    Automatically applies new settings to running optimizer.
    """
    if created:
        return  # Skip on initial creation
    
    print(f"[CONFIG_LISTENER] Optimization config changed")
    
    try:
        # Import here to avoid circular imports
        from .performance_optimizer import get_optimizer
        
        optimizer = get_optimizer()
        
        # Apply new configuration
        optimizer.apply_optimization_config(instance)
        
        print(f"[CONFIG_LISTENER] Optimizer updated with new configuration")
        
    except Exception as e:
        print(f"[CONFIG_LISTENER] Error updating optimizer: {e}")


@receiver(post_save, sender=BehaviorConfig)
def on_behavior_config_changed(sender, instance, created, **kwargs):
    """
    React to behavior configuration changes.
    """
    if created:
        return
    
    print(f"[CONFIG_LISTENER] Behavior config changed")
    
    if not instance.system_enabled:
        print(f"[CONFIG_LISTENER] System disabled - stopping analysis")
        # Could add code to gracefully stop behavior analysis
    else:
        print(f"[CONFIG_LISTENER] System enabled - ready for analysis")


@receiver(post_save, sender=DetectorConfig)
def on_detector_config_changed(sender, instance, created, **kwargs):
    """
    React to detector configuration changes.
    """
    if created:
        return
    
    detector_type = instance.get_detector_type_display()
    print(f"[CONFIG_LISTENER] {detector_type} detector config changed")
    
    try:
        # Could add code to update specific detector at runtime
        # from .behavior_analyzer import get_detector
        # detector = get_detector(instance.detector_type)
        # detector.update_config(instance)
        
        print(f"[CONFIG_LISTENER] {detector_type} configuration applied")
        
    except Exception as e:
        print(f"[CONFIG_LISTENER] Error updating detector: {e}")


# Register signal handlers in apps.py
def register_listeners():
    """Call this in apps.py ready() method to register listeners."""
    pass  # Signals auto-register with @receiver decorator
```

### Step 5: Update Django Apps Configuration

Update `/backend/app1/apps.py`:

```python
from django.apps import AppConfig


class App1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app1'
    
    def ready(self):
        """Initialize app and register signal listeners."""
        # Register configuration change listeners
        from . import configuration_listener  # noqa
        
        print("[APP1] Configuration change listeners registered")
```

### Step 6: Create Configuration Management Service

Create `/backend/app1/configuration_service.py`:

```python
"""
Configuration Service
====================

High-level service for managing configuration at runtime.
"""

from django.core.cache import cache
from .configuration_models import (
    get_optimization_config,
    get_behavior_config,
    get_threshold_config,
    get_detector_config,
    ConfigurationAudit,
)


class ConfigurationService:
    """Service for managing system configuration."""
    
    CACHE_KEY_PREFIX = 'config_'
    CACHE_TTL = 300  # 5 minutes
    
    @staticmethod
    def get_cached_config(config_type):
        """Get cached configuration."""
        cache_key = f'{ConfigurationService.CACHE_KEY_PREFIX}{config_type}'
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        # Get from database and cache
        if config_type == 'behavior':
            config = get_behavior_config()
        elif config_type == 'optimization':
            config = get_optimization_config()
        elif config_type == 'thresholds':
            config = get_threshold_config()
        else:
            return None
        
        cache.set(cache_key, config, ConfigurationService.CACHE_TTL)
        return config
    
    @staticmethod
    def invalidate_cache(config_type):
        """Invalidate cached configuration."""
        cache_key = f'{ConfigurationService.CACHE_KEY_PREFIX}{config_type}'
        cache.delete(cache_key)
    
    @staticmethod
    def get_current_status():
        """Get comprehensive system configuration status."""
        behavior = get_behavior_config()
        optimization = get_optimization_config()
        
        return {
            'system_enabled': behavior.system_enabled,
            'processing_mode': behavior.processing_mode,
            'target_fps': behavior.target_fps,
            'optimizations_active': sum([
                optimization.frame_skip_enabled,
                optimization.resolution_adapt_enabled,
                optimization.memory_pool_enabled,
                optimization.cpu_throttle_enabled,
                optimization.cache_enabled,
            ]),
            'cache_hit_rate': optimization.cache_enabled,
        }
    
    @staticmethod
    def apply_preset(preset_name):
        """Apply optimization preset."""
        config = get_optimization_config()
        
        presets = {
            'conservative': {
                'frame_skip_enabled': True,
                'initial_skip_rate': 1,
                'max_skip_rate': 2,
                'resolution_adapt_enabled': False,
                'cpu_throttle_enabled': False,
            },
            'balanced': {
                'frame_skip_enabled': True,
                'initial_skip_rate': 1,
                'max_skip_rate': 5,
                'resolution_adapt_enabled': True,
                'cpu_throttle_enabled': True,
                'cpu_throttle_max': 80.0,
            },
            'aggressive': {
                'frame_skip_enabled': True,
                'initial_skip_rate': 2,
                'max_skip_rate': 5,
                'resolution_adapt_enabled': True,
                'cpu_threshold_high': 70.0,
                'cpu_throttle_enabled': True,
                'cpu_throttle_max': 85.0,
                'memory_pool_size': 20,
            },
        }
        
        if preset_name not in presets:
            raise ValueError(f"Unknown preset: {preset_name}")
        
        # Apply preset settings
        for field, value in presets[preset_name].items():
            setattr(config, field, value)
        
        config.save()
        
        # Invalidate cache
        ConfigurationService.invalidate_cache('optimization')
        
        return config
    
    @staticmethod
    def get_recent_changes(limit=10):
        """Get recent configuration changes."""
        return ConfigurationAudit.objects.all().order_by('-created_at')[:limit]


# Convenience functions
def get_current_status():
    """Get system configuration status."""
    return ConfigurationService.get_current_status()


def apply_optimization_preset(preset_name):
    """Apply optimization preset by name."""
    return ConfigurationService.apply_preset(preset_name)
```

### Step 7: Use Configuration Service

Now you can use configuration anywhere in your code:

```python
# In views.py
from .configuration_service import get_current_status

def behavior_dashboard(request):
    status = get_current_status()
    return render(request, 'dashboard.html', {'status': status})

# In API responses
from rest_framework.response import Response
from .configuration_service import get_current_status

@api_view(['GET'])
def system_status(request):
    return Response(get_current_status())

# In optimization code
from .configuration_service import ConfigurationService

def process_frame():
    config = ConfigurationService.get_cached_config('optimization')
    skip_rate = config.initial_skip_rate
    # Use skip_rate
```

---

## 🚀 Runtime Configuration Changes

### Scenario: User Changes Setting in Admin

1. **User changes** OptimizationConfig in Django admin
2. **Django signal** triggers `on_optimization_config_changed()`
3. **Signal handler** calls `optimizer.apply_optimization_config()`
4. **Optimizer** updates its internal settings
5. **Next frame** processed with new settings
6. **ConfigurationAudit** record created automatically

### Example: Apply Aggressive Optimization

```bash
# Step 1: Via Admin
# Navigate to: http://localhost:8000/admin/app1/optimizationconfig/
# Select "Apply preset: aggressive"
# Click Save

# OR Step 1: Via API
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"preset": "aggressive"}' \
  http://localhost:8000/api/config/optimization/apply_preset/

# Step 2: Configuration automatically applied to running optimizer
# Step 3: System uses new settings immediately
```

---

## 📊 Monitoring Configuration Changes

### View Configuration Status

```python
from app1.configuration_service import get_current_status

status = get_current_status()
print(f"Optimizations active: {status['optimizations_active']}/5")
print(f"Target FPS: {status['target_fps']}")
```

### View Change History

```python
from app1.configuration_service import ConfigurationService

recent_changes = ConfigurationService.get_recent_changes(limit=20)
for change in recent_changes:
    print(f"{change.changed_by}: {change.changed_field} changed")
```

### Subscribe to Configuration Changes

```python
from django.db.models.signals import post_save
from app1.configuration_models import OptimizationConfig

@receiver(post_save, sender=OptimizationConfig)
def my_config_handler(sender, instance, **kwargs):
    print("Configuration changed!")
    # Do something with instance
```

---

## 🔧 Advanced Integration

### Custom Configuration Handlers

Create `/backend/app1/custom_config_handlers.py`:

```python
"""
Custom Configuration Handlers
=============================

Application-specific configuration handling.
"""


class ResolutionConfigHandler:
    """Handle resolution adaptation configuration."""
    
    @staticmethod
    def apply(config):
        """Apply resolution configuration."""
        from .performance_optimizer import get_optimizer
        
        optimizer = get_optimizer()
        adapter = optimizer.resolution_adapter
        
        adapter.cpu_threshold_low = config.cpu_threshold_low
        adapter.cpu_threshold_mid = config.cpu_threshold_mid
        adapter.cpu_threshold_high = config.cpu_threshold_high
        
        if not config.resolution_adapt_enabled:
            adapter.disable()
        else:
            adapter.enable()


class FrameSkipConfigHandler:
    """Handle frame skip configuration."""
    
    @staticmethod
    def apply(config):
        """Apply frame skip configuration."""
        from .performance_optimizer import get_optimizer
        
        optimizer = get_optimizer()
        skipper = optimizer.frame_skipper
        
        skipper.set_skip_rate(config.initial_skip_rate)
        skipper.max_skip_rate = config.max_skip_rate
        
        if not config.frame_skip_enabled:
            skipper.disable()
        else:
            skipper.enable()
```

### Configuration Validation

```python
from django.core.exceptions import ValidationError

def validate_optimization_config(config):
    """Validate optimization configuration."""
    errors = []
    
    if config.initial_skip_rate > config.max_skip_rate:
        errors.append("Initial skip rate cannot exceed max skip rate")
    
    if config.cpu_threshold_low > config.cpu_threshold_mid:
        errors.append("CPU thresholds must be in ascending order")
    
    if config.cpu_threshold_mid > config.cpu_threshold_high:
        errors.append("CPU thresholds must be in ascending order")
    
    if errors:
        raise ValidationError(errors)
```

---

## 🎯 Use Cases

### Use Case 1: Dynamic Performance Tuning

**Scenario:** System load increases during peak hours

```python
# Automatic response
def monitor_system_load():
    config = get_optimization_config()
    if cpu_usage > 85:
        # Increase frame skipping
        config.initial_skip_rate = min(5, config.initial_skip_rate + 1)
        config.save()
```

### Use Case 2: Preset Switching

**Scenario:** Admin needs to reduce load on low-end hardware

```bash
# Apply conservative preset
curl -X POST /api/config/optimization/apply_preset/ \
  -d '{"preset": "conservative"}'

# Result: Minimal frame skipping, better accuracy
```

### Use Case 3: Detector Fine-Tuning

**Scenario:** Drowsiness detection too sensitive

```bash
# Increase threshold in admin or via API
curl -X PATCH /api/config/detectors/drowsiness/ \
  -d '{"confidence_threshold": 0.9}'
```

### Use Case 4: Alert Calibration

**Scenario:** False positives from attention system

```bash
# Adjust alert thresholds
curl -X PUT /api/config/thresholds/ \
  -d '{"attention_poor_threshold": 25}'
```

---

## ✅ Integration Checklist

- [ ] Modified `performance_optimizer.py` to load configuration
- [ ] Added `_load_configuration()` method
- [ ] Added `apply_optimization_config()` method
- [ ] Created `configuration_listener.py` with signal handlers
- [ ] Updated `apps.py` ready() method
- [ ] Created `configuration_service.py`
- [ ] Tested configuration loading on startup
- [ ] Tested configuration changes at runtime
- [ ] Verified signal handlers fire correctly
- [ ] Tested preset application
- [ ] Verified audit trail captures changes

---

## 🐛 Troubleshooting

### Issue: Configuration not loading on startup

**Solution:** Ensure database migrations run before starting optimizer

```bash
python manage.py migrate
python manage.py runserver
```

### Issue: Configuration changes not applied

**Solution:** Verify signal handlers registered in apps.py

```python
# In apps.py
def ready(self):
    from . import configuration_listener
```

### Issue: Cache preventing config updates

**Solution:** Clear cache after config changes

```python
from app1.configuration_service import ConfigurationService
ConfigurationService.invalidate_cache('optimization')
```

### Issue: Circular imports

**Solution:** Import inside functions, not at module level

```python
# Good
def apply_config():
    from .performance_optimizer import get_optimizer
    optimizer = get_optimizer()

# Bad
from .performance_optimizer import get_optimizer  # May cause circular import
```

---

## 📝 Complete Integration Example

```python
# backend/app1/apps.py
from django.apps import AppConfig

class App1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app1'
    
    def ready(self):
        # Register configuration listeners
        from . import configuration_listener  # noqa
        
        # Load configuration on startup
        from .performance_optimizer import get_optimizer
        from .configuration_models import get_optimization_config
        
        try:
            optimizer = get_optimizer()
            config = get_optimization_config()
            optimizer.apply_optimization_config(config)
            print("[APP1] Optimizer loaded with configuration")
        except Exception as e:
            print(f"[APP1] Failed to load optimizer config: {e}")
```

---

## 🎉 Result

After integration:

✅ Configuration loads on startup  
✅ Changes apply at runtime  
✅ All changes audited  
✅ Presets available  
✅ Web UI + API for management  
✅ Full backwards compatibility  

**Phase 8 + Phase 9 = Complete system!** 🚀

