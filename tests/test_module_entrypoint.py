import runpy

import pytest


def test_module_entrypoint_uses_cli_main(monkeypatch):
    monkeypatch.setattr("rankweave.cli.main", lambda: 7)

    with pytest.raises(SystemExit) as raised:
        runpy.run_module("rankweave.__main__", run_name="__main__")

    assert raised.value.code == 7
