"""Extract features from Django models for ML prediction."""
import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


def extract_transaction_features(tx_pk: int) -> Dict:
    """
    Extract 10 features from a transaction for fraud prediction.
    
    Features:
        - amount
        - user_avg_amount
        - amount_ratio (with division-by-zero prevention)
        - tx_count_last_1h
        - tx_count_last_24h
        - is_new_device
        - is_trusted_device
        - is_new_ip
        - is_new_country
        - failed_logins_last_30m
        - hour_of_day
    
    Returns:
        Dictionary with feature names and values
    """
    from apps.ledger.models import Transaction, TransactionEntry
    from apps.ledger.constants import EntryType
    from apps.security.models import LoginLog, UserDevice
    from apps.security.constants import LoginStatus
    
    try:
        tx = Transaction.objects.select_related('customer').get(pk=tx_pk)
    except Transaction.DoesNotExist:
        logger.warning(f"Transaction {tx_pk} not found for feature extraction")
        return _default_features()
    
    # Feature 1: amount
    amount = float(tx.amount)
    
    # Feature 2 & 3: user_avg_amount and amount_ratio (with division-by-zero prevention)
    user_avg_amount = amount  # default to current amount
    amount_ratio = 1.0  # default ratio
    
    if tx.customer_id:
        # Calculate average transaction amount for this user
        past_txs = Transaction.objects.filter(
            customer_id=tx.customer_id,
            status='COMPLETED',
            occurred_at__lt=tx.occurred_at
        ).exclude(pk=tx_pk)
        
        if past_txs.exists():
            avg = past_txs.aggregate(avg_amount=models.Avg('amount'))['avg_amount']
            if avg and avg > 0:
                user_avg_amount = float(avg)
                amount_ratio = amount / user_avg_amount
    
    # Feature 4 & 5: tx_count_last_1h and tx_count_last_24h
    tx_count_last_1h = 0
    tx_count_last_24h = 0
    
    if tx.customer_id:
        now = tx.occurred_at
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(hours=24)
        
        # Count recent debits from customer's accounts
        from apps.accounts.models import Account
        customer_accounts = Account.objects.filter(user_id=tx.customer_id).values_list('id', flat=True)
        
        if customer_accounts:
            tx_count_last_1h = TransactionEntry.objects.filter(
                account_id__in=customer_accounts,
                entry_type=EntryType.DEBIT,
                created_at__gte=one_hour_ago,
                created_at__lt=now
            ).exclude(transaction_id=tx_pk).count()
            
            tx_count_last_24h = TransactionEntry.objects.filter(
                account_id__in=customer_accounts,
                entry_type=EntryType.DEBIT,
                created_at__gte=one_day_ago,
                created_at__lt=now
            ).exclude(transaction_id=tx_pk).count()
    
    # Extract telemetry from metadata_json
    metadata = tx.metadata_json or {}
    device_id = metadata.get('device_id', '')
    ip_address = metadata.get('ip_address', '')
    geo_country = metadata.get('geo_country', '')
    
    # Feature 6 & 7: is_new_device and is_trusted_device
    is_new_device = 0
    is_trusted_device = 0
    
    if tx.customer_id and device_id:
        device_exists = UserDevice.objects.filter(
            user_id=tx.customer_id,
            device_uuid=device_id
        ).exists()
        
        if not device_exists:
            is_new_device = 1
        else:
            # Check if device is trusted
            device = UserDevice.objects.filter(
                user_id=tx.customer_id,
                device_uuid=device_id
            ).first()
            if device and device.is_trusted:
                is_trusted_device = 1
    
    # Feature 8: is_new_ip
    is_new_ip = 0
    
    if tx.customer_id and ip_address:
        # Check if this IP has been seen in successful logins
        ip_seen = LoginLog.objects.filter(
            user_id=tx.customer_id,
            status=LoginStatus.SUCCESS,
            ip_address=ip_address,
            attempted_at__lt=tx.occurred_at
        ).exists()
        
        if not ip_seen:
            is_new_ip = 1
    
    # Feature 9: is_new_country
    is_new_country = 0
    
    if tx.customer_id and geo_country:
        # Check if this country has been seen in successful logins
        country_seen = LoginLog.objects.filter(
            user_id=tx.customer_id,
            status=LoginStatus.SUCCESS,
            location_country=geo_country,
            attempted_at__lt=tx.occurred_at
        ).exists()
        
        if not country_seen:
            is_new_country = 1
    
    # Feature 10: failed_logins_last_30m
    failed_logins_last_30m = 0
    
    if tx.customer_id:
        thirty_min_ago = tx.occurred_at - timedelta(minutes=30)
        failed_logins_last_30m = LoginLog.objects.filter(
            user_id=tx.customer_id,
            status=LoginStatus.FAILED,
            attempted_at__gte=thirty_min_ago,
            attempted_at__lt=tx.occurred_at
        ).count()
    
    # Feature 11: hour_of_day
    hour_of_day = tx.occurred_at.hour
    
    features = {
        'amount': amount,
        'user_avg_amount': user_avg_amount,
        'amount_ratio': amount_ratio,
        'tx_count_last_1h': tx_count_last_1h,
        'tx_count_last_24h': tx_count_last_24h,
        'is_new_device': is_new_device,
        'is_trusted_device': is_trusted_device,
        'is_new_ip': is_new_ip,
        'is_new_country': is_new_country,
        'failed_logins_last_30m': failed_logins_last_30m,
        'hour_of_day': hour_of_day,
    }
    
    logger.debug(f"Extracted features for tx {tx_pk}: {features}")
    return features


def _default_features() -> Dict:
    """Return default feature values when extraction fails."""
    return {
        'amount': 0.0,
        'user_avg_amount': 0.0,
        'amount_ratio': 1.0,
        'tx_count_last_1h': 0,
        'tx_count_last_24h': 0,
        'is_new_device': 0,
        'is_trusted_device': 0,
        'is_new_ip': 0,
        'is_new_country': 0,
        'failed_logins_last_30m': 0,
        'hour_of_day': 12,
    }
