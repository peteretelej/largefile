"""Test fixture with nested class/method structures."""


def helper():
    """Standalone function outside any class."""
    return 42


class DataProcessor:
    """A class with two methods for testing enclosing definition lookup."""

    def process(self, data):
        """Process the given data."""
        result = []
        for item in data:
            result.append(item * 2)
        return result

    def validate(self, data):
        """Validate the given data."""
        if not data:
            return False
        return all(isinstance(item, int) for item in data)


# Top-level code (not inside any definition)
x = 1
