# Testing

UHI has some testing helpers for use in test suites. This is primarily for
library authors.

## Indexing

You can see if your library passes the indexing test suite. We provide
three sets of tests: 1D, 2D, and 3D tests. These can be implemented on
your own library (`my.Histogram` in this example) like this:

```python
import uhi.testing.indexing

class TestAccess1D(uhi.testing.indexing.Indexing1D[my.Histogram]):
    @classmethod
    def make_histogram(cls) -> my.Histogram:
        return my.Histogram(cls.get_uhi())

class TestAccess1D(uhi.testing.indexing.Indexing2D[my.Histogram]):
    @classmethod
    def make_histogram(cls) -> my.Histogram:
        return my.Histogram(cls.get_uhi())

class TestAccess1D(uhi.testing.indexing.Indexing3D[my.Histogram]):
    @classmethod
    def make_histogram(cls) -> my.Histogram:
        return my.Histogram(cls.get_uhi())
```

If you don't support serialization, then you can manually set the values with
the UHI item, or check the docstrings to see what the correct parameters are.

Make sure you don't import from `uhi.testing.indexing`, as some runners (unittest)
will pick the base classes up and try to run those too.
