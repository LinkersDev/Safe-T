"""
Ledger API views.

Customer-facing:
  GET /api/ledger/transactions/          — list own transactions
  GET /api/ledger/transactions/{ref}/    — detail with entries

Staff-facing:
  GET  /api/staff/ledger/transactions/          — all transactions with filters
  GET  /api/staff/ledger/transactions/{ref}/    — detail view
  POST /api/staff/ledger/transactions/{ref}/reverse/  — initiate reversal
  GET  /api/staff/ledger/fee-rules/             — list active fee rules
"""
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.users.permissions import HasPermission
from apps.users.validators import normalize_phone

from .exceptions import (
    TransactionAlreadyReversedError,
    TransactionNotFoundError,
    TransactionNotReversibleError,
)
from .models import FeeRule, Transaction
from .permissions import IsUserFullyActive
from .selectors import (
    get_all_transactions_staff,
    get_transaction_by_reference,
    get_transaction_history,
    get_transactions_for_customer,
)
from .serializers import (
    FeeRuleSerializer,
    ReverseTransactionSerializer,
    TransactionHistorySerializer,
    TransactionListSerializer,
    TransactionSerializer,
)
from .services import archive_transaction, reverse_transaction


# ---------------------------------------------------------------------------
# Customer views
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
def transaction_list(request):
    """List the authenticated user's transactions."""
    tx_type = request.query_params.get("type")
    tx_status = request.query_params.get("status")
    try:
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        return Response({"detail": "Invalid pagination params."}, status=status.HTTP_400_BAD_REQUEST)

    transactions = get_transactions_for_customer(
        request.user,
        status=tx_status,
        transaction_type=tx_type,
        limit=limit,
        offset=offset,
    )
    serializer = TransactionListSerializer(transactions, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsUserFullyActive])
def transaction_detail(request, reference_number):
    """Retrieve a single transaction with all entries."""
    transaction = get_transaction_by_reference(reference_number)
    if transaction is None or transaction.customer != request.user:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = TransactionSerializer(transaction)
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# Staff views
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_transaction_list(request):
    """List all transactions with optional filters (staff only)."""
    if not HasPermission.user_has_perm(request.user, "view_all_transactions"):
        return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    q = (request.query_params.get("q") or "").strip() or None
    tx_type = request.query_params.get("type")
    tx_status = request.query_params.get("status")
    currency = request.query_params.get("currency")
    occurred_from_raw = (request.query_params.get("from") or "").strip()
    occurred_to_raw = (request.query_params.get("to") or "").strip()

    occurred_from = parse_datetime(occurred_from_raw) if occurred_from_raw else None
    occurred_to = parse_datetime(occurred_to_raw) if occurred_to_raw else None

    if (occurred_from_raw and occurred_from is None) or (occurred_to_raw and occurred_to is None):
        return Response(
            {"detail": "Invalid datetime range. Use ISO format like 2026-04-30T10:00:00Z."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # If q looks like a phone number, normalize for better matching
    if q and q.startswith("+"):
        try:
            q = normalize_phone(q)
        except ValueError:
            # Keep raw q; selector still tries icontains matches.
            pass

    try:
        limit = int(request.query_params.get("limit", 100))
        offset = int(request.query_params.get("offset", 0))
    except ValueError:
        return Response({"detail": "Invalid pagination params."}, status=status.HTTP_400_BAD_REQUEST)

    transactions = get_all_transactions_staff(
        status=tx_status,
        transaction_type=tx_type,
        currency_code=currency,
        q=q,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
        offset=offset,
    )
    serializer = TransactionListSerializer(transactions, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def staff_transaction_detail(request, reference_number):
    """Full transaction detail including entries (staff only)."""
    if not HasPermission.user_has_perm(request.user, "view_all_transactions"):
        return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    transaction = get_transaction_by_reference(reference_number)
    if transaction is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = TransactionSerializer(transaction)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reverse_transaction_view(request, reference_number):
    """Reverse a completed transaction (Admin / Compliance only)."""
    if not HasPermission.user_has_perm(request.user, "reverse_transaction"):
        return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    serializer = ReverseTransactionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        reversal = reverse_transaction(
            reference_number=reference_number,
            reason=serializer.validated_data["reason"],
            initiated_by=request.user,
        )
    except TransactionNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    except (TransactionNotReversibleError, TransactionAlreadyReversedError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    # Archive the original right away
    original = Transaction.objects.get(reference_number=reference_number)
    archive_transaction(original)

    return Response(
        TransactionSerializer(reversal).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def archive_transaction_view(request, reference_number):
    """Manually archive a completed transaction (Admin only)."""
    if not HasPermission.user_has_perm(request.user, "manage_system"):
        return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    transaction = get_transaction_by_reference(reference_number)
    if transaction is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    history = archive_transaction(transaction)
    return Response(
        TransactionHistorySerializer(history).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fee_rule_list(request):
    """List all active fee rules (staff only)."""
    if not HasPermission.user_has_perm(request.user, "view_all_transactions"):
        return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

    rules = FeeRule.objects.filter(is_active=True).select_related("currency").order_by(
        "transaction_type", "priority"
    )
    serializer = FeeRuleSerializer(rules, many=True)
    return Response(serializer.data)
