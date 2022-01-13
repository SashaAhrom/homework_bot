class TokensChatIdError(Exception):
    """Tokens or chat id mistake."""

    pass


class CheckApiKey(Exception):
    """Missing expected keys in API response."""

    pass


class CheckHomeworkStatus(Exception):
    """Wrong homework status."""

    pass


class ResponseError(Exception):
    """Wrong response."""

    pass
