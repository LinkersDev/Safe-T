"""Domain exceptions for the KYC app."""


class KYCNotApprovedError(Exception):
    """Raised when a user without APPROVED kyc_status attempts a financial operation."""
    pass


class KycDocumentNotFoundError(Exception):
    pass


class KycAlreadyApprovedError(Exception):
    """Raised when staff tries to approve KYC that is already APPROVED."""
    pass


class KycNotPendingError(Exception):
    """Raised when staff tries to review KYC that is not in PENDING state."""
    pass


class KycIncompleteError(Exception):
    """
    Raised when staff attempts to approve a user without complete KYC:
    missing required profile fields and/or missing required documents.
    """

    def __init__(self, *, missing_fields: list[str], missing_documents: list[str]):
        self.missing_fields = missing_fields
        self.missing_documents = missing_documents
        super().__init__("KYC is incomplete.")
