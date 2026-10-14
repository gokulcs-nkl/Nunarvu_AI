# Django Project Issues - QUICK REFERENCE

## 🔴 CRITICAL ISSUES (Must Fix Immediately)

| Issue | Location | Error | Fix Time |
|-------|----------|-------|----------|
| **Missing base.html** | `backend/templates/` (MISSING) | TemplateDoesNotExist | 30 min |
| **Config migrations** | `backend/app1/configuration_models.py` | OperationalError: no such table | 10 min |
| **psutil missing** | `backend/app1/performance_api.py:14` | ModuleNotFoundError | 5 min |
| **behavior_thread import** | `backend/app1/behavior_thread.py:17-20` | ModuleNotFoundError | 20 min |

**Impact:** All dashboard pages + 9 API endpoints fail

---

## 🟠 HIGH PRIORITY (Fix Next)

| Issue | Location | Problem | Fix Time |
|-------|----------|---------|----------|
| **AttentionScore query bug** | `behavior_api_views.py:125-140` | Returns no data | 15 min |
| **BehaviourAlert incomplete** | `models.py:200-225` | Missing fields | 15 min |
| **Config API incomplete** | `configuration_api.py` | Stub methods | 45 min |
| **No object permissions** | `behavior_api_views.py` | SECURITY RISK | 45 min |
| **PDF export dependency** | `behavior_dashboard_views.py:101` | wkhtmltopdf missing | 20 min |
| **behavior_thread_optimized import** | `behavior_thread_optimized.py:21-24` | Import path issue | 10 min |

**Impact:** API data incorrect + security risk + feature failures

---

## ✅ WORKING COMPONENTS

- ✓ Database models (all 8 models defined correctly)
- ✓ API serializers (all defined)
- ✓ URL routing (mostly correct)
- ✓ Behavior detection modules (all 11 modules exist)
- ✓ Settings configuration (mostly correct)

---

## 🛠️ QUICK FIX COMMANDS

```bash
# 1. Create base.html
touch backend/templates/base.html
# [Add Bootstrap 5 + blocks]

# 2. Run migrations
cd backend
python manage.py makemigrations app1
python manage.py migrate

# 3. Add psutil
echo "psutil>=5.9.0" >> requirements.txt
pip install -r requirements.txt

# 4. Fix imports in behavior_thread.py (lines 17-20)
# Change: from behaviour.behavior_analyzer import ...
# To:     import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
#         from behaviour.behavior_analyzer import ...

# 5. Install wkhtmltopdf
# Linux: sudo apt-get install wkhtmltopdf
# macOS: brew install --cask wkhtmltopdf
# Windows: Download from wkhtmltopdf.org
```

---

## 📊 ISSUES BY IMPACT

**3 Dashboard Pages Broken:** ❌
- `/behavior-dashboard/` → 500 Error (needs base.html)
- `/student-attention/` → 500 Error (needs base.html)
- `/behavior-analytics/` → 500 Error (needs base.html)

**9 API Endpoints Fail:** ❌
- `/api/config/behavior/` → 500 (no migration)
- `/api/config/optimization/` → 500 (no migration)
- `/api/config/detectors/` → 500 (no migration)
- `/api/config/thresholds/` → 500 (no migration)
- `/api/config/audit/` → 500 (no migration)
- `/api/performance/metrics/` → 500 (psutil missing)
- `/api/performance/optimization/` → 500 (psutil missing)
- `/api/performance/cache-stats/` → 500 (psutil missing)
- `/api/performance/thread-status/` → 500 (psutil missing)

**3 Features Broken:** ⚠️
- Video capture with behavior analysis (import error)
- Latest attention scores API (query bug)
- PDF export (dependency missing)

**1 Security Risk:** 🔒
- All behavior data endpoints (no object-level permissions)

---

## ⏱️ TOTAL FIX TIME ESTIMATE

| Phase | Tasks | Time | Status |
|-------|-------|------|--------|
| **Phase 1: Critical** | 4 issues | 1 hour | URGENT |
| **Phase 2: High Priority** | 6 issues | 2 hours | URGENT |
| **Phase 3: Medium** | 6 issues | 1.5 hours | Soon |
| **Phase 4: Low Priority** | 3 issues | 30 min | Later |
| **Testing & Deploy** | Full validation | 2-4 hours | After fixes |

**Total:** 6.5-8.5 hours to full resolution

---

## 📋 TEST CHECKLIST AFTER FIXES

- [ ] Dashboard pages load (200 OK)
- [ ] All API endpoints return 200/201 OK
- [ ] Behavior analysis starts without errors
- [ ] Video capture works end-to-end
- [ ] Attention scores update correctly
- [ ] Alerts generate on threshold breach
- [ ] PDF export works (if enabled)
- [ ] Static files load (CSS/JS)
- [ ] 50+ concurrent students tested
- [ ] Database queries optimized

---

## 🚀 DEPLOYMENT CHECKLIST

- [ ] All critical issues fixed
- [ ] All high priority issues fixed
- [ ] Tests passing
- [ ] Static files collected
- [ ] Migrations applied
- [ ] Security review done
- [ ] Load testing passed
- [ ] Monitoring configured
- [ ] Backup procedure ready

---

**See PROJECT_ISSUES_AND_DEFECTS.md for detailed analysis with line numbers, code samples, and solutions.**
