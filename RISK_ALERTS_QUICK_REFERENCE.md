# Risk Alerts — Quick Reference Guide

## 🎯 What Changed

### UI Architecture
**Before:** Flat table with inline details  
**After:** 2-level investigation system (Summary → Detail Drawer)

### User Flow
**Before:** Scan cluttered table → Expand inline  
**After:** Scan clean table → Click to investigate → Full context drawer

---

## 📁 New Files

1. **`frontend/src/domains/risk/utils/risk-explanation.ts`**
   - Generates human-readable risk explanations
   - Interprets ML scores and risk levels
   - Pure utility functions (no side effects)

2. **`frontend/src/domains/risk/components/AlertDetailDrawer.tsx`**
   - Full-screen investigation drawer
   - 5 sections: Risk Explanation, AI/ML, Transaction, Device, User
   - Responsive design

3. **Documentation:**
   - `RISK_ALERTS_UI_UX_REDESIGN.md` — Full design doc
   - `RISK_ALERTS_TRANSFORMATION_SUMMARY.md` — Visual comparison
   - `RISK_ALERTS_QUICK_REFERENCE.md` — This file

---

## 🔧 Modified Files

1. **`frontend/src/domains/risk/pages/RiskAlertsPage.tsx`**
   - Simplified table (7 clean columns)
   - Removed inline details (amounts, IPs, references)
   - Added drawer integration
   - Added click handlers

---

## 🚫 What Was NOT Changed

- ❌ Backend risk engine
- ❌ ML model
- ❌ Database schema
- ❌ API contracts
- ❌ Alert generation logic
- ❌ Scoring algorithms

**100% Backward Compatible**

---

## 🎨 Level 1: Summary Table

### Columns:
1. **Alert Type** — Icon + Label (Transfer, Login, Withdrawal, etc.)
2. **User** — Name + Phone/Account
3. **Severity** — Badge (Critical, High, Medium, Low)
4. **Risk Score** — Number + Vertical bar
5. **Time** — Relative + Timestamp
6. **Status** — Badge (Open, Dismissed, Resolved)
7. **Actions** — Dismiss + Investigate buttons

### Features:
- Entire row clickable
- Hover effect
- Clean, scannable
- No clutter

---

## 🔍 Level 2: Detail Drawer

### Sections:

#### 1. Risk Explanation
- Human-readable title
- Plain language description
- Risk factors list
- Actionable recommendation

#### 2. AI / ML Intelligence
- Combined risk score (with bar)
- ML fraud probability (with bar)
- Rule-based score
- Scoring breakdown (60% ML + 40% rules)
- Rules triggered (badges)

#### 3. Transaction Context (if applicable)
- Amount + Currency
- Transaction type
- Reference number
- Account number

#### 4. Device / Network Context (if applicable)
- Device ID
- IP address
- Location (country)

#### 5. User Information
- User name
- Phone number
- Alert timestamp
- Auto-action status

---

## 🚀 How to Use

### For Risk Officers:

1. **Scan Summary Table**
   - Identify high-severity alerts
   - Check risk scores
   - Prioritize by time

2. **Click to Investigate**
   - Click any row OR "Investigate" button
   - Drawer opens with full context

3. **Review Details**
   - Read risk explanation
   - Check AI/ML scores
   - Review transaction/device context

4. **Take Action**
   - Dismiss if false positive
   - Escalate if needs senior review
   - Freeze account if critical

5. **Close Drawer**
   - Click X or outside drawer
   - Return to summary

---

## 🧪 Testing

### Functional:
- [x] Table displays all alerts
- [x] Click row opens drawer
- [x] Drawer shows correct data
- [x] Risk explanation generates
- [x] AI/ML scores display
- [x] Context sections show correctly
- [x] Close drawer works
- [x] Actions work (Dismiss, etc.)

### UX:
- [x] Table is clean and scannable
- [x] Drawer provides full context
- [x] Explanations are readable
- [x] No information overload
- [x] Smooth transitions

---

## 📊 Key Metrics

### Before:
- 7+ lines per alert in table
- No risk explanation
- ML scores hidden
- Cluttered UI

### After:
- 2 lines per alert in table
- Human-readable explanations
- ML scores transparent
- Clean, professional UI

---

## 🎓 Design Principles Applied

1. **Progressive Disclosure** — Show minimal, reveal comprehensive
2. **Separation of Concerns** — Summary vs Investigation
3. **Human-Readable** — Plain language over technical jargon
4. **Industry Standard** — SIEM/SOC/Banking patterns
5. **Backend Untouched** — Pure presentation layer

---

## 🔗 Related Docs

- **Full Design:** `RISK_ALERTS_UI_UX_REDESIGN.md`
- **Visual Comparison:** `RISK_ALERTS_TRANSFORMATION_SUMMARY.md`
- **Backend Analysis:** `RISK_ALERTS_ANALYSIS_AND_IMPROVEMENTS.md`

---

## ✅ Status

**Production Ready** — Zero backend changes, 100% backward compatible

**Deploy:** Build frontend → Deploy static assets → Done
