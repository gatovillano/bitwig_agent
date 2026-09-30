import pytest
from bitwig_agent.devices import BitwigDeviceRecommender, BITWIG_DEVICES_DATABASE

def test_database_not_empty():
    assert len(BITWIG_DEVICES_DATABASE) > 15
    for dev in BITWIG_DEVICES_DATABASE:
        assert "name" in dev
        assert "type" in dev
        assert "category" in dev
        assert "tags" in dev
        assert "description" in dev

def test_recommend_warm_analog_pad():
    recs = BitwigDeviceRecommender.recommend("warm vintage analog pad for synthwave", num_results=3)
    assert len(recs) > 0
    top_names = [r["device"] for r in recs]
    # Polymer or Polysynth should be in the top recommendations
    assert any(name in ["Polymer", "Polysynth"] for name in top_names)
    assert recs[0]["relevance_score"] > 0
    assert "explanation" in recs[0]

def test_recommend_reverb_space():
    recs = BitwigDeviceRecommender.recommend("spacious hall reverb for vocals", num_results=3, category="Reverb")
    assert len(recs) > 0
    assert recs[0]["category"] == "Reverb"
    top_names = [r["device"] for r in recs]
    assert "Reverb" in top_names or "Convolution" in top_names

def test_recommend_sub_bass():
    recs = BitwigDeviceRecommender.recommend("punchy 808 sub bass", num_results=3)
    assert len(recs) > 0
    top_names = [r["device"] for r in recs]
    assert any(name in ["Polymer", "Polysynth", "Saturator", "Drum Machine"] for name in top_names)

def test_search_device_browser():
    results = BitwigDeviceRecommender.search("eq")
    assert len(results) >= 2
    names = [r["name"] for r in results]
    assert "EQ+" in names or "EQ-5" in names

def test_search_device_by_category():
    results = BitwigDeviceRecommender.search("", category="Dynamics")
    assert len(results) >= 2
    for r in results:
        assert r["category"] == "Dynamics"

def test_get_device_info():
    info = BitwigDeviceRecommender.get_info("Polymer")
    assert info is not None
    assert info["name"] == "Polymer"
    assert info["type"] == "Instrument"
    assert "Filter Cutoff" in info["parameters"]

    not_found = BitwigDeviceRecommender.get_info("NonExistentDevice123")
    assert not_found is None

def test_get_device_categories():
    cats = BitwigDeviceRecommender.get_categories()
    assert "categories" in cats
    assert "types" in cats
    assert "total_devices" in cats
    assert "Synth" in cats["categories"]
    assert "Reverb" in cats["categories"]
    assert "Instrument" in cats["types"]
    assert "Audio Effect" in cats["types"]
