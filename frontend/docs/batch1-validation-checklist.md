# Batch 1 Validation Checklist

**Date:** May 14, 2026  
**Build:** Mobile (optimized with conditional routes)  
**Device:** Android Emulator

---

## Pre-Validation Setup

### Environment
- [ ] Backend server running on `http://0.0.0.0:8000`
- [ ] Emulator running (API level 30+)
- [ ] Logcat monitoring active
- [ ] Chrome DevTools connected (for WebView inspection)

### Baseline Comparison
- [ ] Previous build metrics documented
- [ ] Previous startup time recorded
- [ ] Previous memory usage recorded

---

## 1. Startup Performance Testing

### Cold App Startup (Kill app, clear cache, restart)

**Test Steps:**
1. Force stop app
2. Clear app cache/data
3. Start app
4. Measure time to login screen
5. Login with credentials
6. Measure time to dashboard interactive

**Metrics to Capture:**
- [ ] App launch to login screen: _____ ms
- [ ] Login to dashboard visible: _____ ms
- [ ] Dashboard to interactive (can scroll): _____ ms
- [ ] **Total perceived startup:** _____ ms (Target: <2000ms)

**Logcat Commands:**
```bash
# Clear logcat
adb logcat -c

# Monitor startup
adb logcat | findstr "Displayed\|ActivityManager\|chromium"

# Measure WebView load time
adb logcat | findstr "WebView\|Console"
```

**Chrome DevTools:**
- [ ] Open chrome://inspect
- [ ] Connect to WebView
- [ ] Check Performance tab
- [ ] Record startup timeline
- [ ] Capture screenshots

---

## 2. Navigation Smoothness Testing

### Test Routes (Customer Flow)

**Dashboard → Transfer:**
- [ ] No white flash
- [ ] Smooth transition (<300ms perceived)
- [ ] No jank/stuttering
- [ ] Transfer page renders correctly

**Dashboard → Transaction History:**
- [ ] No white flash
- [ ] Smooth transition (<300ms perceived)
- [ ] List renders smoothly
- [ ] Scroll performance good

**Dashboard → QR Payment:**
- [ ] No white flash
- [ ] Smooth transition (<300ms perceived)
- [ ] QR scanner loads (may take time - expected)
- [ ] No app freeze

**Sidebar Open/Close:**
- [ ] Smooth animation
- [ ] No lag on open
- [ ] No lag on close
- [ ] Overlay renders correctly

**Repeated Navigation (10 times):**
- [ ] Dashboard → Transfer → Dashboard (x5)
- [ ] No performance degradation
- [ ] No memory leaks visible
- [ ] Navigation stays smooth

**Navigation Timing:**
- Dashboard → Transfer: _____ ms
- Dashboard → Transactions: _____ ms
- Dashboard → QR: _____ ms
- Sidebar toggle: _____ ms

---

## 3. Memory Usage Testing

### Initial Memory Footprint

**After App Launch:**
- [ ] Open Android Studio Profiler
- [ ] Attach to app process
- [ ] Record memory baseline
- [ ] Initial memory: _____ MB

**After Login:**
- [ ] Memory after login: _____ MB
- [ ] Memory delta: _____ MB

**After Dashboard Load:**
- [ ] Memory after dashboard: _____ MB
- [ ] Memory delta: _____ MB

### Memory During Navigation

**After 5 Navigations:**
- [ ] Memory: _____ MB
- [ ] Memory growth: _____ MB

**After 10 Navigations:**
- [ ] Memory: _____ MB
- [ ] Memory growth: _____ MB

**After 20 Navigations:**
- [ ] Memory: _____ MB
- [ ] Memory growth: _____ MB
- [ ] Garbage collection triggered: Yes/No

**Memory Leak Check:**
- [ ] Force GC in profiler
- [ ] Memory returns to baseline: Yes/No
- [ ] No excessive object retention: Yes/No

---

## 4. Route Validation Testing

### Customer Mobile Routes

**Verify Customer Routes Load:**
- [ ] /dashboard - Loads correctly
- [ ] /ledger - Loads correctly
- [ ] /transfer - Loads correctly
- [ ] /qr-payment - Loads correctly
- [ ] /bill-payment - Loads correctly
- [ ] /profile - Loads correctly
- [ ] /tickets - Loads correctly
- [ ] /notifications - Loads correctly

**Verify Staff Routes NOT Loaded:**
- [ ] Navigate to /staff - Should show 404 or redirect
- [ ] Navigate to /staff/users - Should show 404 or redirect
- [ ] Navigate to /staff/kyc - Should show 404 or redirect
- [ ] Navigate to /staff/risk - Should show 404 or redirect

**Check Console (Chrome DevTools):**
- [ ] No errors about missing routes
- [ ] No warnings about lazy loading failures
- [ ] Staff modules NOT in loaded chunks (check Network tab)

### Web App Validation

**Open in Browser (http://localhost:3000):**
- [ ] All customer routes work
- [ ] All staff routes work (if logged in as staff)
- [ ] No console errors
- [ ] No visual regressions

---

## 5. Bundle Validation Testing

### Chunk Loading Analysis

**Chrome DevTools Network Tab:**
- [ ] Record network activity during startup
- [ ] Identify chunks loaded on startup
- [ ] Verify staff chunks NOT loaded initially
- [ ] Verify vendor chunks load correctly

**Initial Chunks Loaded:**
- [ ] index.js (main app)
- [ ] vendor-react.js
- [ ] vendor-qr.js (if QR page accessed)
- [ ] DashboardPage.js
- [ ] LoginPage.js

**Staff Chunks NOT Loaded:**
- [ ] StaffDashboardPage.js - NOT loaded
- [ ] StaffUsersPage.js - NOT loaded
- [ ] StaffKycPage.js - NOT loaded
- [ ] RiskAlertsPage.js - NOT loaded
- [ ] StaffAccountsPage.js - NOT loaded

**Chunk Waterfall:**
- [ ] No excessive sequential loading
- [ ] Parallel chunk loading working
- [ ] No noticeable lazy-loading delays

---

## 6. Regression Testing

### Login Flow
- [ ] Login screen renders
- [ ] Phone number input works
- [ ] OTP request works
- [ ] OTP input works
- [ ] Login successful
- [ ] Redirect to dashboard works

### Auth Persistence
- [ ] Close app
- [ ] Reopen app
- [ ] User still logged in
- [ ] Dashboard loads directly
- [ ] Token refresh works (if expired)

### React Query Behavior
- [ ] Dashboard fetches accounts
- [ ] Dashboard fetches transactions
- [ ] Loading states show correctly
- [ ] Error states show correctly (if backend down)
- [ ] Retry logic works

### Navigation Guards
- [ ] Unauthenticated user redirected to login
- [ ] Customer can access customer routes
- [ ] Customer cannot access staff routes (404/redirect)
- [ ] Role guards working correctly

### Refresh Behavior
- [ ] Pull down on dashboard (if implemented)
- [ ] Data refreshes correctly
- [ ] No duplicate requests
- [ ] Loading indicator shows

### Android Back Button
- [ ] Back from dashboard → exits app (or shows exit dialog)
- [ ] Back from transfer → returns to dashboard
- [ ] Back from transaction detail → returns to transaction list
- [ ] Back from sidebar → closes sidebar (not navigation)

---

## 7. Before/After Comparison

### Startup Time Comparison

| Metric | Before (Baseline) | After (Optimized) | Improvement |
|--------|------------------|-------------------|-------------|
| Cold startup | _____ ms | _____ ms | _____ % |
| Login to dashboard | _____ ms | _____ ms | _____ % |
| Time to interactive | _____ ms | _____ ms | _____ % |

**Target:** <2000ms total perceived startup

### Memory Comparison

| Metric | Before (Baseline) | After (Optimized) | Improvement |
|--------|------------------|-------------------|-------------|
| Initial memory | _____ MB | _____ MB | _____ MB |
| After dashboard | _____ MB | _____ MB | _____ MB |
| After 10 nav | _____ MB | _____ MB | _____ MB |

**Target:** 15-20 MB reduction

### Navigation Feel Comparison

| Route | Before | After | Notes |
|-------|--------|-------|-------|
| Dashboard → Transfer | _____ ms | _____ ms | |
| Dashboard → Transactions | _____ ms | _____ ms | |
| Dashboard → QR | _____ ms | _____ ms | |
| Sidebar toggle | _____ ms | _____ ms | |

**Target:** <300ms perceived delay

---

## 8. Issues Found

### Critical Issues (Block Batch 1)
- [ ] None found

**List:**
1. 
2. 
3. 

### Non-Critical Issues (Fix Later)
- [ ] None found

**List:**
1. 
2. 
3. 

---

## 9. Performance Profiling

### Chrome DevTools Performance Profile

**Startup Profile:**
- [ ] Record performance during startup
- [ ] Identify long tasks (>50ms)
- [ ] Check JavaScript execution time
- [ ] Check rendering time
- [ ] Export profile for analysis

**Navigation Profile:**
- [ ] Record performance during navigation
- [ ] Identify jank (dropped frames)
- [ ] Check layout thrashing
- [ ] Check paint operations

### Android Profiler

**CPU Profiling:**
- [ ] Record CPU during startup
- [ ] Identify hot methods
- [ ] Check WebView overhead
- [ ] Export CPU trace

**Memory Profiling:**
- [ ] Record memory allocations
- [ ] Check for leaks
- [ ] Verify GC behavior
- [ ] Export heap dump

---

## 10. Final Validation

### Success Criteria

**Startup Performance:**
- [ ] ✅ Cold startup <2s (perceived)
- [ ] ✅ 30-40% improvement over baseline
- [ ] ✅ No startup errors

**Navigation Smoothness:**
- [ ] ✅ All transitions <300ms (perceived)
- [ ] ✅ No white flashes
- [ ] ✅ No jank/stuttering

**Memory Usage:**
- [ ] ✅ 15-20 MB reduction
- [ ] ✅ No memory leaks
- [ ] ✅ Stable memory over time

**Route Validation:**
- [ ] ✅ Customer routes work
- [ ] ✅ Staff routes not loaded on mobile
- [ ] ✅ Web app unchanged

**Bundle Validation:**
- [ ] ✅ Chunks load correctly
- [ ] ✅ No excessive waterfalls
- [ ] ✅ No lazy-loading delays

**Regression Testing:**
- [ ] ✅ All features working
- [ ] ✅ No broken flows
- [ ] ✅ No console errors

---

## Validation Status

- [ ] **PASS** - All criteria met, ready to commit Batch 1
- [ ] **FAIL** - Issues found, need fixes before proceeding
- [ ] **PARTIAL** - Some improvements, but not meeting targets

---

## Next Steps

### If PASS:
1. Document final metrics
2. Commit Batch 1 changes
3. Proceed to Batch 2

### If FAIL:
1. Document issues
2. Fix critical issues
3. Re-validate
4. Do NOT proceed to Batch 2

### If PARTIAL:
1. Document findings
2. Decide if acceptable
3. Fix or defer issues
4. Re-validate if needed

---

**Validation Date:** _____  
**Validated By:** _____  
**Status:** _____  
**Notes:** _____
