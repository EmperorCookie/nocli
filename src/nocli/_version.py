"""Version information for nocli package."""

try:
    # Try to get version from installed package metadata
    from importlib.metadata import version
except ImportError:
    # If no metadata available, fall back to hardcoded version
    __version__ = "0.0.1"
else:
    __version__ = version("nocli")
