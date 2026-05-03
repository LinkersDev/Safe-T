import { AxiosError } from 'axios'

export type NormalizedApiError = {
  status: number | null
  detail: string
  code?: string
  fieldErrors?: Record<string, string[]>
}

export function normalizeApiError(error: unknown): NormalizedApiError {
  const fallback: NormalizedApiError = {
    status: null,
    detail: 'Something went wrong. Please try again.',
  }

  if (!(error instanceof AxiosError)) {
    return fallback
  }

  const payload = (error.response?.data ?? {}) as {
    detail?: string
    code?: string
    errors?: Record<string, string[]>
  }

  return {
    status: error.response?.status ?? null,
    detail: payload.detail ?? fallback.detail,
    code: payload.code,
    fieldErrors: payload.errors,
  }
}
