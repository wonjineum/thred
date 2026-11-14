from types import SimpleNamespace

from app import llm_fallback


def test_disabled_llm_returns_none_without_importing(monkeypatch):
    monkeypatch.setenv("THRED_USE_LLM", "0")
    llm_fallback.clear_cache()
    assert llm_fallback.classify_brand("Some Brand") is None
    assert llm_fallback.extract_materials("Cotton Blend", "Tee") is None


def test_calls_labis_helpers_once_and_caches(monkeypatch):
    calls = []
    fake = SimpleNamespace(
        classify_unknown_brand=lambda name: calls.append(name) or "Average",
        extract_material_composition=lambda text, product_title=None: {"cotton": 100},
    )
    monkeypatch.setattr(llm_fallback, "_helpers", lambda: fake)
    llm_fallback.clear_cache()

    assert llm_fallback.classify_brand("Small Label") == "Average"
    assert llm_fallback.classify_brand("Small Label") == "Average"
    assert calls == ["Small Label"]
    assert llm_fallback.extract_materials("Cotton Blend", "Tee") == {"cotton": 100}
    llm_fallback.clear_cache()


def test_unknown_label_from_llm_becomes_none(monkeypatch):
    fake = SimpleNamespace(classify_unknown_brand=lambda name: "Unknown")
    monkeypatch.setattr(llm_fallback, "_helpers", lambda: fake)
    llm_fallback.clear_cache()
    assert llm_fallback.classify_brand("Who") is None
    llm_fallback.clear_cache()
