"""Domain exceptions for the payments app."""


class MerchantNotFoundError(Exception):
    pass


class MerchantNotActiveError(Exception):
    pass


class QRTokenNotFoundError(Exception):
    pass


class QRTokenExpiredError(Exception):
    pass


class QRTokenAlreadyPaidError(Exception):
    pass


class BillProviderNotFoundError(Exception):
    pass


class BillProviderNotActiveError(Exception):
    pass


class TransferSameAccountError(Exception):
    pass
