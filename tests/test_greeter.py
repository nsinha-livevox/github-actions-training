from app.greeter import greet


def test_default_name():
    assert greet() == "Hello, world!"


def test_given_name():
    assert greet("Alice") == "Hello there, Alice!"


def test_blank_name_falls_back():
    assert greet("   ") == "Hello, world!"
