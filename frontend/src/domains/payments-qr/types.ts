export type P2PReceiveQrIssueResponse = {
  qr_payload: string
  expires_in_seconds: number
}

export type P2PReceiveQrIssueWithImage = P2PReceiveQrIssueResponse & {
  image_data_url: string
}

export type P2PReceiveQrResolveResponse = {
  full_name: string
  phone_number: string
  account_number: string
  currency_code: string
}
