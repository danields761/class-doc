# Class doc

Small set of helpers aimed to extract class attributes documentation from a class definition, closely mimicking [sphinx-autodoc behaviour](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#directive-autoattribute) (except instance attributes defined inside `__init__` function).

The main motivation for this project is undesirable integration of really heavy [sphinx-autodoc] dependency, also *sphinx* is usually used for development purposes. As opposite *class-doc* is light, serves a specific purpose and might be easily integrated in any project.

## Installation

This package available on [PyPI]

```bash
pip install class-doc
```

Or using [Poetry]

```bash
poetry add class-doc
```

## Examples

Shamely stolen from [sphinx-autodoc] docs

```python
class Foo:
    """Docstring for class Foo."""

    #: Doc comment for class attribute Foo.bar.
    #: It can have multiple lines.
    bar = 1

    flox = 1.5   #: Doc comment for Foo.flox. One line only.

    baz = 2
    """Docstring for class attribute Foo.baz."""


import class_doc
assert class_doc.extract_docs_from_cls_obj(Foo) == {
    "bar": ["Doc comment for class attribute Foo.bar.", "It can have multiple lines."],
    "flox": ["Doc comment for Foo.flox. One line only."],
    "baz": ["Docstring for class attribute Foo.baz."],
}
```

## Development setup

Project requires [Poetry] for development setup.

* If you aren't have it already

```sh
pip install poetry
``` 

* Install project dependencies

```sh
poetry install
```

* Run tests

```sh
poetry run pytest .
```

* Great, all works!

<!-- Links -->
[PyPI]: http://pypi.org
[Poetry]: https://poetry.eustace.io/
[sphinx-autodoc]: https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#directive-autoattribute