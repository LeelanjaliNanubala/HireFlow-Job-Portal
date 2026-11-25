"""Business-rule errors raised by service functions."""


class ServiceError(Exception):
    """Raised when a business rule is broken (for example: applying twice).

    Web views show `message` to the user; the REST API turns it into a JSON error
    with the given HTTP `status`.
    """

    def __init__(self, message, code='error', status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
