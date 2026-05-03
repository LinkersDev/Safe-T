"""
Enumerations and string choices for the users app.
"""


class RoleCode:
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"
    TELLER = "TELLER"
    TELLER_ADMIN = "TELLER_ADMIN"
    MERCHANT_CUSTOMER = "MERCHANT_CUSTOMER"
    CUSTOMER_SERVICE = "CUSTOMER_SERVICE"
    RISK_OFFICER = "RISK_OFFICER"

    CHOICES = [
        (CUSTOMER, "Customer"),
        (ADMIN, "Admin"),
        (TELLER, "Teller"),
        (TELLER_ADMIN, "Teller Admin"),
        (MERCHANT_CUSTOMER, "Merchant Customer"),
        (CUSTOMER_SERVICE, "Customer Service"),
        (RISK_OFFICER, "Risk Officer"),
    ]

    STAFF_ROLES = {ADMIN, TELLER, TELLER_ADMIN, CUSTOMER_SERVICE, RISK_OFFICER}


class UserStatus:
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"

    CHOICES = [
        (PENDING_VERIFICATION, "Pending Verification"),
        (ACTIVE, "Active"),
        (REJECTED, "Rejected"),
        (BLOCKED, "Blocked"),
    ]


class KycStatus:
    NOT_SUBMITTED = "NOT_SUBMITTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

    CHOICES = [
        (NOT_SUBMITTED, "Not Submitted"),
        (PENDING, "Pending Review"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]


class PhoneLabel:
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    WHATSAPP = "WHATSAPP"

    CHOICES = [
        (PRIMARY, "Primary"),
        (SECONDARY, "Secondary"),
        (WHATSAPP, "WhatsApp"),
    ]


# Seed data: list of (code, name, description, is_staff_role, is_system_role)
SEED_ROLES = [
    (RoleCode.CUSTOMER, "Customer", "Mobile banking customer", False, True),
    (RoleCode.ADMIN, "Admin", "System administrator", True, True),
    (RoleCode.TELLER, "Teller", "Branch teller", True, True),
    (RoleCode.TELLER_ADMIN, "Teller Admin", "Teller manager", True, True),
    (RoleCode.MERCHANT_CUSTOMER, "Merchant Customer", "Business account holder", False, True),
    (RoleCode.CUSTOMER_SERVICE, "Customer Service", "Support staff", True, True),
    (RoleCode.RISK_OFFICER, "Risk Officer", "Fraud and risk reviewer", True, True),
]

# Seed data: list of (code, name, module, description)
SEED_PERMISSIONS = [
    # User management
    ("approve_user", "Approve User", "users", "Can approve pending users"),
    ("reject_user", "Reject User", "users", "Can reject pending users"),
    ("block_user", "Block User", "users", "Can block users"),
    ("view_all_users", "View All Users", "users", "Can list all users"),
    # Account management
    ("freeze_account", "Freeze Account", "accounts", "Can freeze accounts"),
    ("block_account", "Block Account", "accounts", "Can block accounts"),
    ("unfreeze_account", "Unfreeze Account", "accounts", "Can unfreeze accounts"),
    ("view_all_accounts", "View All Accounts", "accounts", "Can view all accounts"),
    # Teller operations
    ("staff_register_customer", "Register Customer", "teller", "Can register new customer accounts"),
    ("staff_deposit", "Deposit", "teller", "Can deposit money into customer accounts"),
    ("staff_withdraw", "Withdraw", "teller", "Can withdraw money from customer accounts"),
    ("staff_view_account_transactions", "View Account Transactions", "teller", "Can view transactions for a customer account"),
    # Transaction
    ("view_all_transactions", "View All Transactions", "ledger", "Can view all transactions"),
    ("reverse_transaction", "Reverse Transaction", "ledger", "Can reverse transactions"),
    ("manage_system", "Manage System", "ledger", "Can archive transactions and system-level ledger ops"),
    # KYC
    ("review_kyc", "Review KYC", "kyc", "Can approve/reject KYC documents"),
    # Risk
    ("review_fraud_alert", "Review Fraud Alert", "risk", "Can review fraud alerts"),
    # Support
    ("manage_support_tickets", "Manage Support Tickets", "support", "Can assign/resolve tickets"),
    ("unlock_user", "Unlock User", "security", "Can unlock locked user accounts"),
    ("reset_user_credentials", "Reset User Credentials", "security", "Can reset password/PIN"),
]

# Explicit permission strategy for ADMIN role assignment.
ADMIN_DEFAULT_PERMISSION_CODES = [
    "approve_user",
    "reject_user",
    "block_user",
    "view_all_users",
    "freeze_account",
    "block_account",
    "unfreeze_account",
    "view_all_accounts",
    "view_all_transactions",
    "reverse_transaction",
    "manage_system",
    "review_kyc",
    "review_fraud_alert",
    "manage_support_tickets",
    "unlock_user",
    "reset_user_credentials",
    "staff_deposit",
    "staff_withdraw",
]
