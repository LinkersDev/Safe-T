"""
Generate test risk alerts to demonstrate the system works for both LOGIN and TRANSACTION events.

Usage:
    python manage.py shell < scripts/generate_test_risk_alerts.py

This script creates:
1. High-value transaction alerts (USD 5,000+)
2. Velocity-based transaction alerts
3. Login alerts (new device, failed logins)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from apps.users.models import User
from apps.ledger.models import Account, Transaction
from apps.ledger.services import post_transaction
from apps.ledger.constants import TransactionType, TransactionStatus
from apps.security.services import record_login
from apps.security.constants import LoginStatus
from apps.risk.models import FraudAlert
from apps.risk.constants import AlertType

print("=" * 80)
print("RISK ALERTS TEST DATA GENERATOR")
print("=" * 80)

# Get or create test users
try:
    sender = User.objects.filter(role__name='CUSTOMER').first()
    receiver = User.objects.filter(role__name='CUSTOMER').exclude(pk=sender.pk).first()
    
    if not sender or not receiver:
        print("❌ ERROR: Need at least 2 CUSTOMER users in database")
        print("   Please create users first via admin or seed script")
        exit(1)
    
    sender_account = Account.objects.filter(user=sender, currency_id='USD').first()
    receiver_account = Account.objects.filter(user=receiver, currency_id='USD').first()
    
    if not sender_account or not receiver_account:
        print("❌ ERROR: Users need USD accounts")
        exit(1)
    
    print(f"✅ Using sender: {sender.full_name} ({sender.phone_number})")
    print(f"✅ Using receiver: {receiver.full_name} ({receiver.phone_number})")
    print()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    exit(1)

# Clear existing test alerts (optional)
print("Clearing existing alerts...")
deleted_count = FraudAlert.objects.all().delete()[0]
print(f"✅ Deleted {deleted_count} existing alerts")
print()

# ============================================================================
# TEST 1: High-Value Transaction Alert (USD 5,000)
# ============================================================================
print("TEST 1: High-Value Transaction (USD 5,000)")
print("-" * 80)

try:
    tx1 = post_transaction(
        transaction_type=TransactionType.TRANSFER,
        source_account=sender_account,
        destination_account=receiver_account,
        amount=Decimal("5000.00"),
        currency_code='USD',
        description="High-value test transfer",
        initiated_by=sender,
    )
    print(f"✅ Created transaction: {tx1.reference_number}")
    print(f"   Amount: USD 5,000.00")
    print(f"   Expected: MEDIUM alert (rule score ~40, ML adds more)")
    
    # Wait for on_commit hook
    import time
    time.sleep(1)
    
    # Check if alert was created
    alert = FraudAlert.objects.filter(transaction=tx1).first()
    if alert:
        print(f"   ✅ Alert created: ID={alert.id}, Severity={alert.severity}, Score={alert.combined_score}")
        print(f"      ML Probability: {alert.ml_fraud_probability}")
        print(f"      Rule Score: {alert.rule_based_score}")
    else:
        print(f"   ⚠️  No alert created (score < 25)")
        tx1.refresh_from_db()
        print(f"      Transaction risk_score: {tx1.risk_score}")
    print()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

# ============================================================================
# TEST 2: Critical Transaction Alert (USD 10,000)
# ============================================================================
print("TEST 2: Critical Transaction (USD 10,000)")
print("-" * 80)

try:
    tx2 = post_transaction(
        transaction_type=TransactionType.TRANSFER,
        source_account=sender_account,
        destination_account=receiver_account,
        amount=Decimal("10000.00"),
        currency_code='USD',
        description="Critical high-value test transfer",
        initiated_by=sender,
    )
    print(f"✅ Created transaction: {tx2.reference_number}")
    print(f"   Amount: USD 10,000.00")
    print(f"   Expected: CRITICAL alert (rule score 75+)")
    
    import time
    time.sleep(1)
    
    alert = FraudAlert.objects.filter(transaction=tx2).first()
    if alert:
        print(f"   ✅ Alert created: ID={alert.id}, Severity={alert.severity}, Score={alert.combined_score}")
        print(f"      ML Probability: {alert.ml_fraud_probability}")
        print(f"      Rule Score: {alert.rule_based_score}")
        print(f"      Auto Action: {alert.auto_action_taken or 'None'}")
    else:
        print(f"   ⚠️  No alert created")
    print()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

# ============================================================================
# TEST 3: Velocity-Based Alert (Multiple Transactions)
# ============================================================================
print("TEST 3: Velocity Pattern (5 transactions in 1 hour)")
print("-" * 80)

try:
    for i in range(5):
        tx = post_transaction(
            transaction_type=TransactionType.TRANSFER,
            source_account=sender_account,
            destination_account=receiver_account,
            amount=Decimal("1000.00"),
            currency_code='USD',
            description=f"Velocity test transfer #{i+1}",
            initiated_by=sender,
        )
        print(f"   Created transaction {i+1}/5: {tx.reference_number}")
    
    print(f"✅ Created 5 transactions")
    print(f"   Expected: Later transactions should get velocity bonus (+25 points)")
    
    import time
    time.sleep(1)
    
    velocity_alerts = FraudAlert.objects.filter(
        transaction__customer=sender,
        alert_type=AlertType.TRANSACTION
    ).order_by('-created_at')[:5]
    
    print(f"   ✅ Found {velocity_alerts.count()} transaction alerts")
    for alert in velocity_alerts:
        print(f"      Alert ID={alert.id}, Score={alert.combined_score}, Rules={alert.rules_triggered}")
    print()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

# ============================================================================
# TEST 4: Login Alert (New Device)
# ============================================================================
print("TEST 4: Login Alert (New Device)")
print("-" * 80)

try:
    login_log = record_login(
        user=sender,
        phone_number=sender.phone_number,
        status=LoginStatus.SUCCESS,
        device_id=f"test-device-{timezone.now().timestamp()}",
        ip_address="192.168.1.100",
        user_agent="Test Browser",
    )
    print(f"✅ Created login event: {login_log.id}")
    print(f"   Device: {login_log.device_id}")
    print(f"   Expected: MEDIUM alert (new device = 25 points)")
    
    import time
    time.sleep(1)
    
    alert = FraudAlert.objects.filter(login_log=login_log).first()
    if alert:
        print(f"   ✅ Alert created: ID={alert.id}, Severity={alert.severity}, Score={alert.risk_score}")
        print(f"      Rules: {alert.rules_triggered}")
    else:
        print(f"   ⚠️  No alert created")
    print()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

# ============================================================================
# TEST 5: Login Alert (Failed Logins)
# ============================================================================
print("TEST 5: Login Alert (Failed Login Attempts)")
print("-" * 80)

try:
    # Create 3 failed logins
    for i in range(3):
        record_login(
            user=sender,
            phone_number=sender.phone_number,
            status=LoginStatus.FAILED,
            device_id="test-device-failed",
            ip_address="10.0.0.1",
            user_agent="Test Browser",
        )
    
    # Then a successful login
    login_log = record_login(
        user=sender,
        phone_number=sender.phone_number,
        status=LoginStatus.SUCCESS,
        device_id="test-device-failed",
        ip_address="10.0.0.1",
        user_agent="Test Browser",
    )
    
    print(f"✅ Created 3 failed + 1 success login")
    print(f"   Expected: MEDIUM/HIGH alert (failed logins = 30 points)")
    
    import time
    time.sleep(1)
    
    alert = FraudAlert.objects.filter(login_log=login_log).first()
    if alert:
        print(f"   ✅ Alert created: ID={alert.id}, Severity={alert.severity}, Score={alert.risk_score}")
        print(f"      Rules: {alert.rules_triggered}")
    else:
        print(f"   ⚠️  No alert created")
    print()
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("SUMMARY")
print("=" * 80)

total_alerts = FraudAlert.objects.count()
transaction_alerts = FraudAlert.objects.filter(alert_type=AlertType.TRANSACTION).count()
login_alerts = FraudAlert.objects.filter(alert_type=AlertType.LOGIN).count()

print(f"Total Alerts Created: {total_alerts}")
print(f"  - Transaction Alerts: {transaction_alerts}")
print(f"  - Login Alerts: {login_alerts}")
print()

if transaction_alerts > 0 and login_alerts > 0:
    print("✅ SUCCESS: Both TRANSACTION and LOGIN alerts are working!")
    print("   The Risk Alerts system is functioning correctly.")
elif transaction_alerts > 0:
    print("✅ Transaction alerts created")
    print("⚠️  No login alerts (may need more suspicious login patterns)")
elif login_alerts > 0:
    print("⚠️  No transaction alerts (amounts may be too low)")
    print("✅ Login alerts created")
else:
    print("⚠️  No alerts created")
    print("   This is expected if all scores < 25 (LOW risk)")
    print("   Try higher transaction amounts or more suspicious patterns")

print()
print("View alerts in Risk Alerts page or Django admin:")
print("  http://localhost:8000/admin/risk/fraudalert/")
print("=" * 80)
