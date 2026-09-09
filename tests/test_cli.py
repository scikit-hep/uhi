from __future__ import annotations

from pathlib import Path

import pytest

from uhi.__main__ import main


def test_cli_validate(resources: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(["validate", str(resources / "valid" / "reg.json")])
    assert capsys.readouterr().out.startswith("OK")
    main(["validate", str(resources / "valid_single" / "reg.json")])
    assert capsys.readouterr().out.startswith("OK")
    with pytest.raises(SystemExit):
        main(["validate", str(resources / "invalid" / "missing_axis.json")])
    assert capsys.readouterr().out.startswith("ERROR")
