"""
seed_demo_data — populate safet_db with verified demo users and transactions.

All users use Somali phone numbers (+252 country code).
All accounts are USD.

Usage:
    python manage.py seed_demo_data --settings=config.settings.base

The command is fully idempotent: safe to run multiple times.
"""
import logging
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

STAFF_USERS = [
    # (phone, password, full_name, role_code, is_superuser, is_staff)
    ("+252611000000", "Admin1234!",  "System Admin",   "ADMIN",            True,  True),
    ("+252611000001", "Teller1234!", "Abdi Teller",    "TELLER",           False, True),
    ("+252611000002", "Risk1234!",   "Fadumo Risk",    "RISK_OFFICER",     False, True),
    ("+252611000003", "CS1234!",     "Hassan CS",      "CUSTOMER_SERVICE", False, True),
]

CUSTOMER_USERS = [
    # (phone, password, full_name, kyc_status, initial_balance_usd)
    ("+252771000010", "Customer1234!", "Ahmed Warsame", "APPROVED",  Decimal("1500.00")),
    ("+252771000011", "Customer1234!", "Faadumo Nur",   "APPROVED",  Decimal("3200.00")),
    ("+252771000012", "Customer1234!", "Mohamed Ali",   "PENDING",   Decimal("0.00")),
]


class Command(BaseCommand):
    help = "Seed SafeT demo data: Somali users, USD accounts, transactions, fraud alert, support ticket."

    def handle(self, *args, **options):
        self.stdout.write("==> Starting demo data seed...\n")

        with db_transaction.atomic():
            currency = self._ensure_currency()
            staff_map = self._seed_staff(currency)
            customer_map = self._seed_customers(currency)
            self._ensure_cash_account(staff_map["+252611000000"], currency)
            provider_account = self._seed_bill_provider(staff_map["+252611000000"], currency)
            self._seed_transactions(customer_map, currency)
            self._seed_fraud_alert(customer_map)
            self._seed_support_ticket(customer_map)

        self.stdout.write(self.style.SUCCESS("\n==> Demo data seed complete.\n"))
        self._print_credentials()

    # ------------------------------------------------------------------
    # Currency
    # ------------------------------------------------------------------

    def _ensure_currency(self):
        from apps.accounts.models import Currency
        currency, created = Currency.objects.get_or_create(
            code="USD",
            defaults={"name": "US Dollar", "symbol": "$", "decimal_places": 2, "is_active": True},
        )
        label = "created" if created else "already exists"
        self.stdout.write(f"  Currency USD: {label}")
        return currency

    def _ensure_cash_account(self, admin_user, currency):
        """
        Create or ensure a cash/vault account used as counterparty for teller
        deposits and withdrawals in dev/demo environments.
        """
        from apps.accounts.constants import AccountStatus
        from apps.accounts.models import Account

        cash_number = getattr(settings, "LEDGER_CASH_ACCOUNT_NUMBER", "") or "9999000000000002"

        account, created = Account.objects.get_or_create(
            account_number=cash_number,
            defaults={
                "user": admin_user,
                "currency": currency,
                "account_name": "Branch Cash Vault",
                "status": AccountStatus.ACTIVE,
                "available_balance": Decimal("100000000.00"),
                "ledger_balance": Decimal("100000000.00"),
            },
        )
        label = "created" if created else "already exists"
        self.stdout.write(f"  Cash Vault account {cash_number}: {label}")
        return account

    # ------------------------------------------------------------------
    # Staff users
    # ------------------------------------------------------------------

    def _seed_staff(self, currency):
        from apps.accounts.constants import AccountStatus
        from apps.accounts.models import Account
        from apps.users.constants import KycStatus, UserStatus
        from apps.users.models import Role, User

        staff_map = {}
        for phone, password, full_name, role_code, is_superuser, is_staff in STAFF_USERS:
            if User.objects.filter(phone_number=phone).exists():
                user = User.objects.get(phone_number=phone)
                self.stdout.write(f"  Staff already exists: {full_name} ({phone})")
            else:
                try:
                    role = Role.objects.get(code=role_code)
                except Role.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"  Role '{role_code}' not found — run migrations first."))
                    role = None

                user = User.objects.create_user(
                    phone_number=phone,
                    password=password,
                    full_name=full_name,
                    status=UserStatus.ACTIVE,
                    kyc_status=KycStatus.APPROVED,
                    is_staff=is_staff,
                    is_superuser=is_superuser,
                    is_active=True,
                    is_phone_verified=True,
                    role=role,
                )
                # Create a USD account for staff (zero balance)
                Account.objects.get_or_create(
                    user=user,
                    defaults={
                        "currency": currency,
                        "account_number": self._staff_account_number(phone),
                        "account_name": full_name,
                        "status": AccountStatus.ACTIVE,
                        "available_balance": Decimal("0.00"),
                        "ledger_balance": Decimal("0.00"),
                    },
                )
                self.stdout.write(f"  Staff created: {full_name} ({phone})")
            staff_map[phone] = user
        return staff_map

    def _staff_account_number(self, phone: str) -> str:
        """Deterministic 16-digit account number for staff from their phone suffix."""
        suffix = phone.replace("+", "").replace(" ", "")[-10:]
        return suffix.zfill(16)

    # ------------------------------------------------------------------
    # Customer users
    # ------------------------------------------------------------------

    def _seed_customers(self, currency):
        from apps.accounts.constants import AccountStatus
        from apps.accounts.models import Account
        from apps.kyc.models import KycDocument
        from apps.users.constants import KycStatus, UserStatus
        from apps.users.models import Role, User

        customer_role = Role.objects.get(code="CUSTOMER")
        customer_map = {}

        for phone, password, full_name, kyc_status, initial_balance in CUSTOMER_USERS:
            if User.objects.filter(phone_number=phone).exists():
                user = User.objects.get(phone_number=phone)
                account = Account.objects.filter(user=user).first()
                self.stdout.write(f"  Customer already exists: {full_name} ({phone})")
                customer_map[phone] = (user, account)
                continue

            user = User.objects.create_user(
                phone_number=phone,
                password=password,
                full_name=full_name,
                status=UserStatus.ACTIVE,
                kyc_status=kyc_status,
                is_staff=False,
                is_superuser=False,
                is_active=True,
                is_phone_verified=True,
                role=customer_role,
            )

            # Create USD account
            account_number = self._customer_account_number(phone)
            account = Account.objects.create(
                user=user,
                currency=currency,
                account_number=account_number,
                account_name=full_name,
                status=AccountStatus.ACTIVE,
                available_balance=initial_balance,
                ledger_balance=initial_balance,
            )

            # Seed a KYC document for approved/pending customers
            if kyc_status in ("APPROVED", "PENDING"):
                KycDocument.objects.get_or_create(
                    user=user,
                    document_type="NATIONAL_ID",
                    defaults={
                        "file": f"kyc_documents/demo/{phone.replace('+', '')}_national_id.jpg",
                        "status": "APPROVED" if kyc_status == "APPROVED" else "PENDING",
                    },
                )

            self.stdout.write(
                f"  Customer created: {full_name} ({phone}) — "
                f"KYC={kyc_status} balance=USD {initial_balance}"
            )
            customer_map[phone] = (user, account)

        return customer_map

    def _customer_account_number(self, phone: str) -> str:
        """Deterministic 16-digit account number from phone."""
        suffix = phone.replace("+", "").replace(" ", "")[-12:]
        return suffix.zfill(16)

    # ------------------------------------------------------------------
    # Bill provider
    # ------------------------------------------------------------------

    def _seed_bill_provider(self, admin_user, currency):
        from apps.accounts.constants import AccountStatus
        from apps.accounts.models import Account
        from apps.payments.models import BillProvider

        provider_account, _ = Account.objects.get_or_create(
            account_number="9999000000000001",
            defaults={
                "user": admin_user,
                "currency": currency,
                "account_name": "Somalia Electricity Corp",
                "status": AccountStatus.ACTIVE,
                "available_balance": Decimal("0.00"),
                "ledger_balance": Decimal("0.00"),
            },
        )

        provider, created = BillProvider.objects.get_or_create(
            code="ELEC-USD",
            defaults={
                "name": "Somalia Electricity",
                "service_type": "ELECTRICITY",
                "provider_account": provider_account,
                "is_active": True,
            },
        )
        label = "created" if created else "already exists"
        self.stdout.write(f"  BillProvider ELEC-USD: {label}")
        return provider_account

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def _seed_transactions(self, customer_map, currency):
        from apps.ledger.constants import TransactionChannel, TransactionStatus, TransactionType
        from apps.ledger.models import Transaction, TransactionEntry

        ahmed_user, ahmed_account = customer_map["+252771000010"]
        faadumo_user, faadumo_account = customer_map["+252771000011"]

        if not ahmed_account or not faadumo_account:
            self.stdout.write(self.style.WARNING("  Skipping transactions — accounts not found."))
            return

        completed_transfers = [
            ("TRF-DEMO-0001", Decimal("50.00"),  "Transfer to Faadumo Nur"),
            ("TRF-DEMO-0002", Decimal("120.00"), "Monthly payment to Faadumo"),
            ("TRF-DEMO-0003", Decimal("200.00"), "Business transfer"),
        ]

        for ref, amount, desc in completed_transfers:
            if not Transaction.objects.filter(reference_number=ref).exists():
                tx = Transaction.objects.create(
                    reference_number=ref,
                    transaction_type=TransactionType.TRANSFER,
                    status=TransactionStatus.COMPLETED,
                    currency=currency,
                    amount=amount,
                    description=desc,
                    channel=TransactionChannel.MOBILE,
                    customer=ahmed_user,
                    initiated_by=ahmed_user,
                    completed_at=timezone.now(),
                    metadata_json={},
                )
                TransactionEntry.objects.bulk_create([
                    TransactionEntry(transaction=tx, account=ahmed_account,   entry_type="DEBIT",  amount=amount, sequence_no=1),
                    TransactionEntry(transaction=tx, account=faadumo_account, entry_type="CREDIT", amount=amount, sequence_no=2),
                ])
                self.stdout.write(f"  Transaction {ref}: USD {amount} (TRANSFER, COMPLETED)")

        # 1 completed QR payment
        qr_ref = "QRP-DEMO-0001"
        if not Transaction.objects.filter(reference_number=qr_ref).exists():
            qr_amount = Decimal("85.00")
            tx = Transaction.objects.create(
                reference_number=qr_ref,
                transaction_type=TransactionType.QR_PAYMENT,
                status=TransactionStatus.COMPLETED,
                currency=currency,
                amount=qr_amount,
                description="QR payment at SafeT Shop",
                channel=TransactionChannel.MOBILE,
                customer=ahmed_user,
                initiated_by=ahmed_user,
                completed_at=timezone.now(),
                metadata_json={},
            )
            TransactionEntry.objects.bulk_create([
                TransactionEntry(transaction=tx, account=ahmed_account,   entry_type="DEBIT",  amount=qr_amount, sequence_no=1),
                TransactionEntry(transaction=tx, account=faadumo_account, entry_type="CREDIT", amount=qr_amount, sequence_no=2),
            ])
            self.stdout.write(f"  Transaction {qr_ref}: USD {qr_amount} (QR_PAYMENT, COMPLETED)")

        # 1 failed bill payment
        bill_ref = "BLP-DEMO-0001"
        if not Transaction.objects.filter(reference_number=bill_ref).exists():
            bill_amount = Decimal("40.00")
            tx = Transaction.objects.create(
                reference_number=bill_ref,
                transaction_type=TransactionType.BILL_PAYMENT,
                status=TransactionStatus.FAILED,
                currency=currency,
                amount=bill_amount,
                description="Electricity bill payment (failed)",
                channel=TransactionChannel.MOBILE,
                customer=ahmed_user,
                initiated_by=ahmed_user,
                metadata_json={"provider_code": "ELEC-USD", "failure_reason": "provider_timeout"},
            )
            self.stdout.write(f"  Transaction {bill_ref}: USD {bill_amount} (BILL_PAYMENT, FAILED)")

    # ------------------------------------------------------------------
    # Fraud alert
    # ------------------------------------------------------------------

    def _seed_fraud_alert(self, customer_map):
        from apps.risk.constants import AlertSeverity, AlertStatus, AlertType
        from apps.risk.models import FraudAlert

        ahmed_user, ahmed_account = customer_map["+252771000010"]

        if not FraudAlert.objects.filter(
            user=ahmed_user,
            status=AlertStatus.OPEN,
            alert_type=AlertType.TRANSACTION,
        ).exists():
            FraudAlert.objects.create(
                alert_type=AlertType.TRANSACTION,
                severity=AlertSeverity.MEDIUM,
                status=AlertStatus.OPEN,
                risk_score=Decimal("35.00"),
                user=ahmed_user,
                account=ahmed_account,
                rules_triggered=["Moderate velocity: 3 debits in last 1h"],
                auto_action_taken="",
            )
            self.stdout.write("  FraudAlert: OPEN / MEDIUM created for Ahmed Warsame")
        else:
            self.stdout.write("  FraudAlert: already exists")

    # ------------------------------------------------------------------
    # Support ticket
    # ------------------------------------------------------------------

    def _seed_support_ticket(self, customer_map):
        from apps.support.constants import TicketCategory, TicketStatus
        from apps.support.models import SupportTicket, SupportTicketMessage

        ahmed_user, _ = customer_map["+252771000010"]

        ticket, created = SupportTicket.objects.get_or_create(
            user=ahmed_user,
            subject="Transfer failed — USD 40 not returned",
            defaults={
                "category": TicketCategory.PAYMENT_ISSUE,
                "status": TicketStatus.OPEN,
            },
        )
        if created:
            SupportTicketMessage.objects.create(
                ticket=ticket,
                sender=ahmed_user,
                body=(
                    "Hello, I tried to pay my electricity bill for USD 40 but the payment failed. "
                    "The amount was not returned to my account. Please help."
                ),
                is_internal=False,
            )
            self.stdout.write("  SupportTicket: OPEN created for Ahmed Warsame")
        else:
            self.stdout.write("  SupportTicket: already exists")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _print_credentials(self):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  SafeT Demo Credentials (Somalia +252)")
        self.stdout.write("=" * 60)
        self.stdout.write("\n  STAFF USERS:")
        rows = [
            ("+252611000000", "Admin1234!",  "System Admin",   "ADMIN"),
            ("+252611000001", "Teller1234!", "Abdi Teller",    "TELLER"),
            ("+252611000002", "Risk1234!",   "Fadumo Risk",    "RISK_OFFICER"),
            ("+252611000003", "CS1234!",     "Hassan CS",      "CUSTOMER_SERVICE"),
        ]
        for phone, pwd, name, role in rows:
            self.stdout.write(f"    {phone}  /  {pwd}  ({name}, {role})")

        self.stdout.write("\n  CUSTOMER USERS:")
        cust_rows = [
            ("+252771000010", "Customer1234!", "Ahmed Warsame",  "APPROVED",  "1,500.00"),
            ("+252771000011", "Customer1234!", "Faadumo Nur",    "APPROVED",  "3,200.00"),
            ("+252771000012", "Customer1234!", "Mohamed Ali",    "PENDING",   "0.00"),
        ]
        for phone, pwd, name, kyc, bal in cust_rows:
            self.stdout.write(f"    {phone}  /  {pwd}  ({name}, KYC={kyc}, USD {bal})")

        self.stdout.write("\n  BILL PROVIDER:  ELEC-USD  (Somalia Electricity)")
        self.stdout.write("=" * 60 + "\n")
