"""
Custom exceptions related to document uploads.

Using domain-specific exceptions makes the service layer
independent of HTTP while providing clearer error handling.
"""


class UploadError(Exception):
    """
    Base exception for upload-related errors.
    """
    pass


class UnsupportedDocumentTypeError(UploadError):
    """
    Raised when a user uploads an unsupported document type.
    """
    pass


class EmptyFilenameError(UploadError):
    """
    Raised when an uploaded file has no filename.
    """
    pass
