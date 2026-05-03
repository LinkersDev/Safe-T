"""String choices for the KYC app."""


class KycDocumentType:
    NATIONAL_ID     = "NATIONAL_ID"
    PASSPORT        = "PASSPORT"
    RESIDENCE_PERMIT= "RESIDENCE_PERMIT"
    SELFIE          = "SELFIE"
    PROOF_OF_ADDRESS= "PROOF_OF_ADDRESS"

    CHOICES = [
        (NATIONAL_ID,      "National ID"),
        (PASSPORT,         "Passport"),
        (RESIDENCE_PERMIT, "Residence Permit"),
        (SELFIE,           "Selfie / Liveness Photo"),
        (PROOF_OF_ADDRESS, "Proof of Address"),
    ]


class KycDocumentStatus:
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

    CHOICES = [
        (PENDING,  "Pending Review"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]
