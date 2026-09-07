from __future__ import annotations

import json
import re
import typing
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import boost_histogram as bh
import numpy as np
import pytest

import uhi.io
import uhi.io.json
import uhi.io.zip
from uhi.__main__ import main
from uhi.io import ARRAY_KEYS, to_sparse
from uhi.io.ops import add
from uhi.typing.serialization import AnyHistogramIR

STORAGES = [
    bh.storage.Int64(),
    bh.storage.Double(),
    bh.storage.Weight(),
    bh.storage.Mean(),
    bh.storage.WeightedMean(),
]

RNG = np.random.default_rng(42)


def _ir(h: bh.Histogram[Any]) -> AnyHistogramIR:
    return typing.cast(AnyHistogramIR, h._to_uhi_())


def _fill(h: bh.Histogram[Any], n: int) -> bh.Histogram[Any]:
    x = RNG.normal(size=n)
    y = RNG.normal(size=n)
    kwargs: dict[str, Any] = {}
    if h.kind == bh.Kind.MEAN:
        kwargs["sample"] = RNG.normal(size=n)
    if h.storage_type in {bh.storage.Weight, bh.storage.WeightedMean}:
        kwargs["weight"] = RNG.uniform(0.5, 2, size=n)
    h.fill(x, y, **kwargs)
    return h


def _defined_variance(storage: Mapping[str, Any]) -> Any:
    """
    Mask of bins where the variance of a mean storage is well defined. With a
    single entry the variance is 0/0, and rounding in boost-histogram's
    incremental update turns that into arbitrary values (inf, nan, or finite
    garbage), so those bins are not compared.
    """
    match storage["type"]:
        case "mean":
            return storage["counts"] > 1
        case "weighted_mean":
            w = storage["sum_of_weights"]
            with np.errstate(divide="ignore", invalid="ignore"):
                return w - storage["sum_of_weights_squared"] / w > 1e-9 * w
        case _:
            return np.ones_like(storage["values"], dtype=bool)


def _assert_storage_equal(a: Mapping[str, Any], b: Mapping[str, Any]) -> None:
    assert a["type"] == b["type"]
    assert a.keys() == b.keys()
    mask = _defined_variance(b)
    for key in ARRAY_KEYS & a.keys():
        if key == "variances":
            np.testing.assert_allclose(a[key][mask], b[key][mask], equal_nan=True)
        else:
            np.testing.assert_allclose(a[key], b[key], equal_nan=True)


@pytest.mark.parametrize("storage", STORAGES, ids=lambda s: type(s).__name__)
@pytest.mark.parametrize("n", [0, 1, 2, 50])
def test_add_matches_boost_histogram(storage: bh.storage.Storage, n: int) -> None:
    axes = (bh.axis.Regular(3, -1, 1), bh.axis.Regular(4, -2, 2))
    h1 = _fill(bh.Histogram(*axes, storage=storage), 100)
    h2 = _fill(bh.Histogram(*axes, storage=storage), n)
    h3 = _fill(bh.Histogram(*axes, storage=storage), 30)

    expected = _ir(h1 + h2 + h3)
    result = add(_ir(h1), h2, _ir(h3))

    assert result["axes"] == expected["axes"]
    _assert_storage_equal(result["storage"], expected["storage"])
    # Result round-trips into boost-histogram (exact == fails on float rounding)
    _assert_storage_equal(
        bh.Histogram(dict(result))._to_uhi_()["storage"], expected["storage"]
    )


def test_add_valid_fixture(valid: Path, sparse: bool) -> None:
    hists = json.loads(
        valid.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )
    for dense in hists.values():
        hist = to_sparse(dense) if sparse else dense
        result = add(hist, hist)
        assert ("index" in result["storage"]) == ("index" in hist["storage"])
        assert result["axes"] == hist["axes"]
        assert result.get("metadata") == hist.get("metadata")
        assert result.get("writer_info") == hist.get("writer_info")
        if hist["storage"]["type"] in {"int", "double", "weighted"} and hist["axes"]:
            expected = uhi.io.from_sparse(hist)["storage"]
            got: Mapping[str, Any] = uhi.io.from_sparse(result)["storage"]
            for key in ARRAY_KEYS & expected.keys():
                np.testing.assert_array_equal(got[key], 2 * np.asarray(expected[key]))


def test_add_keeps_int_dtype() -> None:
    h = bh.Histogram(bh.axis.Integer(0, 3), storage=bh.storage.Int64())
    h.fill([0, 1, 1])
    result = add(h, h)
    assert np.issubdtype(result["storage"]["values"].dtype, np.integer)
    np.testing.assert_array_equal(result["storage"]["values"], [0, 2, 4, 0, 0])


def test_add_mixed_sparse_gives_dense() -> None:
    h = bh.Histogram(bh.axis.Integer(0, 3))
    h.fill([0, 1, 1])
    dense = _ir(h)
    sparse = to_sparse(dense)
    assert "index" in sparse["storage"]
    assert "index" not in add(dense, sparse)["storage"]
    assert "index" not in add(sparse, dense)["storage"]
    assert "index" in add(sparse, sparse)["storage"]
    np.testing.assert_array_equal(
        uhi.io.from_sparse(add(sparse, sparse))["storage"]["values"], [0, 2, 4, 0, 0]
    )


def test_add_empty_storage() -> None:
    h = bh.Histogram(bh.axis.Integer(0, 3))
    h.fill([0, 1, 1])
    full = _ir(h)
    empty: Any = {**full, "storage": {"type": "double"}}

    assert add(empty, empty)["storage"] == {"type": "double"}
    np.testing.assert_array_equal(
        add(empty, full)["storage"]["values"], full["storage"]["values"]
    )
    np.testing.assert_array_equal(
        add(full, empty)["storage"]["values"], full["storage"]["values"]
    )


def test_add_ignores_axis_metadata_and_keeps_first() -> None:
    h1 = bh.Histogram(
        bh.axis.Regular(3, 0, 1, metadata={"name": "a"}), metadata={"hist": 1}
    )
    h2 = bh.Histogram(
        bh.axis.Regular(3, 0, 1, metadata={"name": "b"}), metadata={"hist": 2}
    )
    result = add(h1, h2)
    assert result["metadata"] == h1._to_uhi_()["metadata"]
    assert result["axes"][0]["metadata"] == h1._to_uhi_()["axes"][0]["metadata"]


def test_add_mismatched_axes() -> None:
    h1 = bh.Histogram(bh.axis.Regular(3, 0, 1))
    h2 = bh.Histogram(bh.axis.Regular(4, 0, 1))
    h3 = bh.Histogram(bh.axis.Regular(3, 0, 1), bh.axis.Regular(3, 0, 1))
    h4 = bh.Histogram(bh.axis.Variable([0, 0.5, 1]))
    h5 = bh.Histogram(bh.axis.Variable([0, 0.25, 1]))
    with pytest.raises(ValueError, match="Histogram 1 has axes"):
        add(h1, h2)
    with pytest.raises(ValueError, match="Histogram 1 has axes"):
        add(h1, h3)
    with pytest.raises(ValueError, match="Histogram 1 has axes"):
        add(h1, h4)
    with pytest.raises(ValueError, match="Histogram 1 has axes"):
        add(h4, h5)


def test_add_mismatched_storage() -> None:
    h1 = bh.Histogram(bh.axis.Regular(3, 0, 1), storage=bh.storage.Int64())
    h2 = bh.Histogram(bh.axis.Regular(3, 0, 1), storage=bh.storage.Double())
    with pytest.raises(ValueError, match="storage type 'double', expected 'int'"):
        add(h1, h2)


# CLI


def _make_files(
    tmp_path: Path, suffix: str
) -> tuple[list[Path], dict[str, bh.Histogram[Any]]]:
    """Write two files; ``only_in_first`` is present in the first file only."""
    a = _fill(bh.Histogram(bh.axis.Regular(3, -1, 1), bh.axis.Regular(4, -2, 2)), 100)
    b = _fill(bh.Histogram(bh.axis.Regular(3, -1, 1), bh.axis.Regular(4, -2, 2)), 100)
    m1 = _fill(
        bh.Histogram(
            bh.axis.Regular(3, -1, 1),
            bh.axis.Regular(4, -2, 2),
            storage=bh.storage.Mean(),
        ),
        100,
    )
    m2 = _fill(
        bh.Histogram(
            bh.axis.Regular(3, -1, 1),
            bh.axis.Regular(4, -2, 2),
            storage=bh.storage.Mean(),
        ),
        100,
    )
    only = _fill(bh.Histogram(bh.axis.Regular(3, -1, 1), bh.axis.Regular(4, -2, 2)), 10)

    files = [tmp_path / f"in1{suffix}", tmp_path / f"in2{suffix}"]
    _write_file(files[0], {"h": a, "sub/mean": m1, "only_in_first": only})
    _write_file(files[1], {"h": b, "sub/mean": m2})
    return files, {"h": a + b, "sub/mean": m1 + m2, "only_in_first": only}


def _write_file(path: Path, hists: dict[str, bh.Histogram[Any]]) -> None:
    match path.suffix:
        case ".json":
            path.write_text(
                json.dumps(hists, default=uhi.io.json.default), encoding="utf-8"
            )
        case ".zip":
            with zipfile.ZipFile(path, "w") as zf:
                for name, hist in hists.items():
                    uhi.io.zip.write(zf, name, hist)
        case _:
            h5py = pytest.importorskip("h5py")
            from uhi.io import hdf5

            with h5py.File(path, "w") as f:
                for name, hist in hists.items():
                    hdf5.write(f.create_group(name), hist)


def _read_file(path: Path) -> dict[str, Any]:
    from uhi.__main__ import _read

    return _read(path)


@pytest.mark.parametrize("in_suffix", [".json", ".zip", ".h5"])
@pytest.mark.parametrize("out_suffix", [".json", ".zip", ".h5"])
def test_cli_add(tmp_path: Path, in_suffix: str, out_suffix: str) -> None:
    if ".h5" in {in_suffix, out_suffix}:
        pytest.importorskip("h5py")
    files, expected = _make_files(tmp_path, in_suffix)
    target = tmp_path / f"out{out_suffix}"

    main(["add", str(target), *map(str, files)])

    result = _read_file(target)
    assert result.keys() == expected.keys()
    for name, hist in expected.items():
        _assert_storage_equal(result[name]["storage"], hist._to_uhi_()["storage"])


def test_cli_add_force(tmp_path: Path) -> None:
    files, _ = _make_files(tmp_path, ".json")
    target = tmp_path / "out.json"
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit, match="use --force"):
        main(["add", str(target), *map(str, files)])
    assert target.read_text(encoding="utf-8") == "{}"

    main(["add", "--force", str(target), *map(str, files)])
    assert "only_in_first" in _read_file(target)


def test_cli_add_unknown_extension(tmp_path: Path) -> None:
    files, _ = _make_files(tmp_path, ".json")
    with pytest.raises(SystemExit, match=re.escape("Unknown file extension '.txt'")):
        main(["add", str(tmp_path / "out.txt"), *map(str, files)])
