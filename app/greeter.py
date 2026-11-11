"""A tiny app for the GitHub Actions training: it only builds a greeting."""
import sys


def greet(name: str = "world") -> str:
    """Return a greeting. An empty name falls back to 'world'."""
    return f"Hello, {name.strip() or 'world'}!"


if __name__ == "__main__":
    # python -m app.greeter Alice   ->   Hello, Alice!
    print(greet(*sys.argv[1:2]))
