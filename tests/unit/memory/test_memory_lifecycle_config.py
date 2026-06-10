from __future__ import annotations

from reflexlearn.common.config import Settings


def test_memory_lifecycle_settings_defaults():
    settings = Settings()

    assert settings.enable_memory_consolidation is True
    assert settings.enable_forgetting is False
    assert settings.memory_ttl_days == 90
    assert settings.memory_forget_min_hits == 1
    assert settings.enable_graph_autogrow is False
