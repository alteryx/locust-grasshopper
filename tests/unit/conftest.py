"""Module: Conftest."""
pytest_plugins = ["pytester"]


class MockConfig(dict):
    """Mock config object that can be loaded with a dict instead of a Config."""

    def getoption(self, value):
        """Retrieve a value from the dictionary, the way a Config object supports."""
        return self.get(value)
