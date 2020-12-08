class Error(Exception):
    """ Root Exception for modlunky2.assets package. """


class FileConflict(Error):
    """ Raised when multiple assets of the same name are found across packs."""


class MultipleMatchingAssets(Error):
    """ Raised when multiple assets of the same name are found in a single pack."""


class MissingAsset(Error):
    """Returned when an expected asset is missing."""


class NonSiblingAsset(Error):
    """Returned when an asset is not a sibling of the compression dir."""
