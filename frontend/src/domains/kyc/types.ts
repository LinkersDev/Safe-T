export type KycStatus = 'NOT_SUBMITTED' | 'PENDING' | 'APPROVED' | 'REJECTED'
export type KycDocumentStatus = 'PENDING' | 'APPROVED' | 'REJECTED'
export type KycDocumentType =
  | 'NATIONAL_ID'
  | 'PASSPORT'
  | 'RESIDENCE_PERMIT'
  | 'SELFIE'
  | 'PROOF_OF_ADDRESS'

export type KycDocument = {
  id: number
  documentType: KycDocumentType
  fileUrl: string
  status: KycDocumentStatus
  rejectionReason: string
  createdAt: string
}

export type KycStatusResponse = {
  kycStatus: KycStatus
  documents: KycDocument[]
}
