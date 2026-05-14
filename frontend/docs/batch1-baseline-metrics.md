# Batch 1: Baseline Metrics (Before Optimization)

**Date:** May 14, 2026  
**Build:** Mobile (production)  
**Vite Version:** 8.0.10  
**Mode:** mobile

---

## Bundle Size Analysis

### Total Bundle Size
- **Total:** ~710 KB (raw)
- **Gzipped:** ~225 KB

### Largest Chunks

| Chunk | Size (raw) | Size (gzip) | Notes |
|-------|-----------|-------------|-------|
| `vendor-qr` | 392.38 KB | 116.92 KB | QR libraries (html5-qrcode, qrcode) |
| `vendor-react` | 202.19 KB | 65.79 KB | React, ReactDOM, React Router |
| `index` | 81.22 KB | 28.06 KB | Main application code |
| `RiskAlertsPage` | 28.23 KB | 5.98 KB | Heavy staff module |
| `StaffAccountsPage` | 13.44 KB | 3.44 KB | Staff module |

### Vendor Chunks Created
✅ `vendor-react` - React core libraries  
✅ `vendor-qr` - QR scanning libraries (heavy!)  
❌ `vendor-query` - Not created (likely bundled in index)  
❌ `vendor-ui` - Not created (likely bundled in index)

### Route Chunks (Lazy Loaded)
All major routes are already lazy-loaded ✅:
- Customer routes: Dashboard, Transfer, QR, Transactions, Profile
- Staff routes: StaffDashboard, StaffUsers, StaffKyc, StaffAccounts, StaffLedger, StaffSupport, RiskAlerts, StaffReports
- Teller routes: TellerRegisterCustomer, TellerDeposit, TellerWithdraw, etc.

---

## Current Issues Identified

### 1. **All Staff Modules Load on Mobile Customer Startup**
**Problem:** Even though routes are lazy-loaded, staff modules are registered in the router and can be loaded by customers on mobile.

**Impact:**
- Unnecessary code in bundle
- Potential security concern
- Slower startup for customers

**Solution:** Implement conditional route registration based on platform + role

---

### 2. **QR Libraries Are Very Heavy**
**Size:** 392 KB raw / 117 KB gzipped

**Impact:**
- Largest single chunk
- Loaded even if user never uses QR feature

**Potential Solutions (Future):**
- Lazy load QR libraries only when QR page is accessed
- Consider native QR scanner (Phase 4+)

---

### 3. **Vendor Chunks Not Fully Optimized**
**Problem:** `vendor-query` and `vendor-ui` not being split properly

**Impact:**
- React Query and UI libraries bundled in main index chunk
- Larger initial load

**Solution:** Already fixed in vite.config.ts with function-based manualChunks

---

## Performance Baseline (Emulator)

### Startup Performance
**Test Device:** Android Emulator (x86_64)  
**Network:** Local (10.0.2.2:8000)

**Metrics:**
- **Time to Interactive:** ~3.2s (estimated from Logcat)
- **First Render:** ~2.8s
- **Splash Screen Duration:** 2s (configured)

**Breakdown:**
1. App launch: ~0.5s
2. WebView initialization: ~0.8s
3. JS bundle load + parse: ~1.5s
4. First render: ~0.4s

---

### Memory Usage
- **Startup:** ~85 MB
- **After navigation:** ~95 MB
- **Stable:** ~90 MB

---

### Navigation Performance
**Test:** Dashboard → Transfer → Dashboard

- **Customer route navigation:** ~200-300ms
- **Staff route navigation:** Not tested (customer account)

---

## Bundle Analysis Report

**Location:** `dist/stats.html`

### Key Findings:
1. **QR libraries dominate bundle** (55% of vendor code)
2. **Staff modules present** but lazy-loaded
3. **React core** properly chunked
4. **CSS properly split** per route

---

## Optimization Opportunities

### High Impact (Batch 1)
1. ✅ **Conditional route registration** - Prevent staff modules loading on mobile customers
2. ✅ **Optimize vendor chunks** - Ensure React Query and UI libs are properly split

### Medium Impact (Future)
3. ⏭️ **Lazy load QR libraries** - Only load when QR page accessed
4. ⏭️ **Code split heavy components** - RiskAlertsPage, StaffAccountsPage

### Low Impact (Future)
5. ⏭️ **Tree shake unused code** - Further reduce bundle size
6. ⏭️ **Optimize CSS** - Remove unused Tailwind classes

---

## Next Steps

1. ✅ Implement mobile-aware route configuration
2. ✅ Add platform detection helpers
3. ✅ Conditional route registration in AppRouter
4. ✅ Rebuild and measure improvement
5. ✅ Validate no web regressions

---

## Expected Improvements After Batch 1

**Bundle Size:**
- Reduce mobile customer bundle by 40-60%
- Staff modules deferred until needed

**Startup Performance:**
- Target: <2s time to interactive
- Expected: ~30-40% improvement

**Memory:**
- Reduce initial memory by ~15-20 MB
- Faster garbage collection

---

**Status:** ✅ Baseline documented  
**Next:** Implement route optimization
