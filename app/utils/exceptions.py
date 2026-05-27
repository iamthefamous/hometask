class ProcessingError(Exception):
    """Raised when article processing fails."""


class ExtractionError(ProcessingError):
    """Raised when article extraction fails."""


class LLMValidationError(ProcessingError):
    """Raised when LLM output is invalid."""
