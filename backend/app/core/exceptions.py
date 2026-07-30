class FaceProcessingError(Exception):
    """Base error for a face image that cannot be processed."""


class FaceNotFoundError(FaceProcessingError):
    """Raised when no face can be detected."""


class MultipleFacesError(FaceProcessingError):
    """Raised when enrollment receives an image with more than one face."""


class FaceModelsMissingError(FaceProcessingError):
    """Raised when the required ONNX model files have not been installed."""

