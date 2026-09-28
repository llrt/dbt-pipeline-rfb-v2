from __future__ import annotations

import rfb_pipeline  # noqa: F401


def test_paquete_importable() -> None:
    assert rfb_pipeline.__name__ == "rfb_pipeline"
