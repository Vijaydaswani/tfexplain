class TfExplainError(Exception):
    """Base exception for expected tfexplain errors."""


class AnalysisError(TfExplainError):
    """Raised when input cannot be analyzed."""
