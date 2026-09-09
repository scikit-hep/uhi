from __future__ import annotations

import json
from pathlib import Path

import pytest

from uhi.__main__ import main


def test_cli_validate(resources: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["validate", str(resources / "valid" / "reg.json")])
    assert capsys.readouterr().out.startswith("OK")
    with pytest.raises(SystemExit):
        main(["validate", str(resources / "invalid" / "missing_axis.json")])
    assert capsys.readouterr().out.startswith("ERROR")


def test_cli_validate_single_and_mapping(
    resources: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hists = json.loads((resources / "valid" / "reg.json").read_text(encoding="utf-8"))
    single = tmp_path / "single.json"
    single.write_text(json.dumps(hists["one"]), encoding="utf-8")
    main(["validate", str(single)])
    assert capsys.readouterr().out.startswith("OK")

    del hists["two"]["axes"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(hists), encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["validate", str(bad)])
    out = capsys.readouterr().out
    assert out.startswith("ERROR")
    assert "data.two must contain ['axes']" in out
