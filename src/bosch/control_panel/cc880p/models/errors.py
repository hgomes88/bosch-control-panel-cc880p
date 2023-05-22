"""Errors module."""


class Error(Exception):
    """Base Error."""

    def __init__(self, *args: object) -> None:
        """Init."""
        super().__init__(*args)


class TimeoutError(Error):
    """Timeout Error."""

    def __init__(self, *args: object) -> None:
        """Init."""
        super().__init__(*args)


class MessageError(Error):
    """Message Error."""

    def __init__(self, *args: object) -> None:
        """Init."""
        super().__init__(*args)


class ConnectionError(Error):
    """Connection Error."""

    def __init__(self, *args: object) -> None:
        """Init."""
        super().__init__(*args)


class ValueError(Error):
    """Value Error."""

    def __init__(self, *args: object) -> None:
        """Init."""
        super().__init__(*args)
