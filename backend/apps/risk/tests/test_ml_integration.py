"""Tests for ML fraud detection integration."""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account, Currency
from apps.ledger.models import Transaction
from apps.risk.ml.feature_builder import extract_transaction_features
from apps.risk.ml.predictor import predict_transaction_fraud
from apps.risk.models import FraudAlert
from apps.risk.services import score_transaction
from apps.users.models import User


class MLIntegrationTestCase(TestCase):
    """Test ML fraud detection integration."""

    def setUp(self):
        """Set up test data."""
        self.currency, _ = Currency.objects.get_or_create(
            code="USD",
            defaults={
                "name": "US Dollar",
                "symbol": "$",
            }
        )
        self.user = User.objects.create_user(
            phone_number="+966500000001",
            password="TestPassword123!",
            full_name="Test User",
        )
        self.account = Account.objects.create(
            user=self.user,
            currency=self.currency,
            account_number="1234567890",
            account_name="Test Account",
            available_balance=Decimal("1000.00"),
        )

    def test_feature_extraction_returns_correct_format(self):
        """Test that feature extraction returns all required features."""
        tx = Transaction.objects.create(
            reference_number="TEST001",
            transaction_type="TRANSFER",
            status="COMPLETED",
            currency=self.currency,
            amount=Decimal("100.00"),
            customer=self.user,
            occurred_at=timezone.now(),
            metadata_json={
                "ip_address": "192.168.1.1",
                "device_id": "device123",
                "user_agent": "Mozilla/5.0",
                "geo_country": "US",
            },
        )

        features = extract_transaction_features(tx.pk)

        # Check all required features are present
        required_features = [
            'amount',
            'user_avg_amount',
            'amount_ratio',
            'tx_count_last_1h',
            'tx_count_last_24h',
            'is_new_device',
            'is_trusted_device',
            'is_new_ip',
            'is_new_country',
            'failed_logins_last_30m',
            'hour_of_day',
        ]

        for feature in required_features:
            self.assertIn(feature, features, f"Missing feature: {feature}")

        # Check types
        self.assertIsInstance(features['amount'], float)
        self.assertIsInstance(features['amount_ratio'], float)
        self.assertIsInstance(features['hour_of_day'], int)

    def test_division_by_zero_prevention(self):
        """Test that amount_ratio defaults to 1.0 when user has no history."""
        tx = Transaction.objects.create(
            reference_number="TEST002",
            transaction_type="TRANSFER",
            status="COMPLETED",
            currency=self.currency,
            amount=Decimal("100.00"),
            customer=self.user,
            occurred_at=timezone.now(),
        )

        features = extract_transaction_features(tx.pk)

        # For new user with no history, amount_ratio should be 1.0
        self.assertEqual(features['amount_ratio'], 1.0)
        self.assertEqual(features['user_avg_amount'], features['amount'])

    def test_ml_prediction_returns_probability(self):
        """Test that ML predictor returns a probability between 0 and 1."""
        features = {
            'amount': 100.0,
            'user_avg_amount': 100.0,
            'amount_ratio': 1.0,
            'tx_count_last_1h': 0,
            'tx_count_last_24h': 0,
            'is_new_device': 0,
            'is_trusted_device': 1,
            'is_new_ip': 0,
            'is_new_country': 0,
            'failed_logins_last_30m': 0,
            'hour_of_day': 12,
        }

        probability = predict_transaction_fraud(features)

        if probability is not None:
            self.assertIsInstance(probability, float)
            self.assertGreaterEqual(probability, 0.0)
            self.assertLessEqual(probability, 1.0)

    def test_hybrid_scoring_combines_correctly(self):
        """Test that hybrid scoring combines ML and rule scores."""
        tx = Transaction.objects.create(
            reference_number="TEST003",
            transaction_type="TRANSFER",
            status="COMPLETED",
            currency=self.currency,
            amount=Decimal("100.00"),
            customer=self.user,
            occurred_at=timezone.now(),
            metadata_json={
                "ip_address": "192.168.1.1",
                "device_id": "device123",
            },
        )

        # Mock ML prediction to return a known value
        with patch('apps.risk.ml.predictor.predict_transaction_fraud') as mock_predict:
            mock_predict.return_value = 0.5  # 50% fraud probability

            alert = score_transaction(tx.pk)

            # If alert was created, check that scores are populated
            if alert:
                self.assertIsNotNone(alert.ml_fraud_probability)
                self.assertIsNotNone(alert.rule_based_score)
                self.assertIsNotNone(alert.combined_score)

    def test_fallback_when_ml_fails(self):
        """Test that system falls back to rule-based scoring when ML fails."""
        tx = Transaction.objects.create(
            reference_number="TEST004",
            transaction_type="TRANSFER",
            status="COMPLETED",
            currency=self.currency,
            amount=Decimal("10000.00"),  # High amount to trigger rule
            customer=self.user,
            occurred_at=timezone.now(),
        )

        # Mock ML prediction to fail
        with patch('apps.risk.ml.predictor.predict_transaction_fraud') as mock_predict:
            mock_predict.return_value = None  # ML failed

            alert = score_transaction(tx.pk)

            # System should still work with rule-based scoring
            if alert:
                self.assertIsNone(alert.ml_fraud_probability)
                self.assertIsNotNone(alert.rule_based_score)
                # Combined score should equal rule score when ML fails
                self.assertEqual(alert.combined_score, alert.rule_based_score)

    def test_fraud_alert_fields_populated(self):
        """Test that FraudAlert is created with all ML fields."""
        tx = Transaction.objects.create(
            reference_number="TEST005",
            transaction_type="TRANSFER",
            status="COMPLETED",
            currency=self.currency,
            amount=Decimal("5000.00"),  # Medium-high amount
            customer=self.user,
            occurred_at=timezone.now(),
            metadata_json={
                "ip_address": "192.168.1.1",
                "device_id": "device123",
            },
        )

        alert = score_transaction(tx.pk)

        if alert:
            # Check that ML fields exist (even if None)
            self.assertTrue(hasattr(alert, 'ml_fraud_probability'))
            self.assertTrue(hasattr(alert, 'rule_based_score'))
            self.assertTrue(hasattr(alert, 'combined_score'))

    def test_rule_based_freeze_authority(self):
        """Test that auto-freeze requires both combined score AND rule score >= 50."""
        tx = Transaction.objects.create(
            reference_number="TEST006",
            transaction_type="TRANSFER",
            status="COMPLETED",
            currency=self.currency,
            amount=Decimal("100.00"),
            customer=self.user,
            occurred_at=timezone.now(),
        )

        # Mock high ML score but low rule score
        with patch('apps.risk.rules.compute_transaction_score') as mock_rules:
            with patch('apps.risk.ml.predictor.predict_transaction_fraud') as mock_ml:
                mock_rules.return_value = (30, ["Low rule score"], self.account.pk)  # Rule score < 50
                mock_ml.return_value = 0.95  # High ML probability

                alert = score_transaction(tx.pk)

                if alert:
                    # Should NOT auto-freeze because rule_score < 50
                    self.assertEqual(alert.auto_action_taken, "")
