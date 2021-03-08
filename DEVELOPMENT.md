Development
===========

To install in development mode with all required development and testing
dependencies:

    python3 -m venv venv
    source venv/bin/activate
    pip install -e '.[dev]'

To run the tests:

    ./test


Packaging
---------

To build the wheel, first install in development mode with `[dev]` extras. This
will ensure that pep517 and twine are installed.

Build the wheel with pep517's build command:

    python3 -m pep517.build .

Upload new the version to PyPI:

    python3 -m twine upload dist/*
