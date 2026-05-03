import { apiClient } from '../../../core/api/client'
import { addMockKycDocument, getMockKycState } from '../../../core/mock/seed-bank-data'
import { isMockModeEnabled } from '../../../core/mock/mode'
import { getSessionState } from '../../../core/state/auth-state'
import type { KycDocument, KycDocumentType, KycStatusResponse } from '../types'

type BackendKycDocument = {
  id: number
  document_type: KycDocumentType
  file: string
  status: KycDocument['status']
  rejection_reason: string
  created_at: string
}

type BackendKycStatusResponse = {
  kyc_status: KycStatusResponse['kycStatus']
  documents: BackendKycDocument[]
}

function mapDocument(document: BackendKycDocument): KycDocument {
  return {
    id: document.id,
    documentType: document.document_type,
    fileUrl: document.file,
    status: document.status,
    rejectionReason: document.rejection_reason,
    createdAt: document.created_at,
  }
}

export async function getKycStatus() {
  const userId = getSessionState().user?.id
  if (isMockModeEnabled()) {
    const mockState = getMockKycState(userId)
    return {
      kycStatus: mockState.kycStatus,
      documents: mockState.documents,
    } satisfies KycStatusResponse
  }

  const response = await apiClient.get<BackendKycStatusResponse>('/api/kyc/status/')
  return {
    kycStatus: response.data.kyc_status,
    documents: response.data.documents.map(mapDocument),
  } satisfies KycStatusResponse
}

export async function uploadKycDocument(documentType: KycDocumentType, file: File) {
  const userId = getSessionState().user?.id
  if (isMockModeEnabled()) {
    addMockKycDocument(userId, {
      documentType,
      fileUrl: URL.createObjectURL(file),
      status: 'PENDING',
      rejectionReason: '',
    })
    return getMockKycState(userId).documents[0]
  }

  const formData = new FormData()
  formData.append('document_type', documentType)
  formData.append('file', file)

  const response = await apiClient.post<BackendKycDocument>('/api/kyc/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return mapDocument(response.data)
}
