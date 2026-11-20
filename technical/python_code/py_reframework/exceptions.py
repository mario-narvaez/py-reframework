"""Failure categories used by the automation."""


class BusinessRuleError(Exception):
    """A transaction cannot be processed because it violates a business rule."""


class SystemFailure(Exception):
    """The automation cannot proceed because of a technical problem."""


class ConfigurationError(SystemFailure):
    """The automation's settings are missing or invalid."""


class TransientSystemError(SystemFailure):
    """A technical failure that may be retried under the recovery policy."""
