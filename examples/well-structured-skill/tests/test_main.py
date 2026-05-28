from main import analyze_text, get_api_config


def test_analyze_text_basic():
    result = analyze_text("Hello world")
    assert result["word_count"] == 2
    assert result["text_length"] == 11


def test_analyze_text_empty():
    try:
        analyze_text("")
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_get_api_config():
    config = get_api_config()
    assert "api_key" in config
    assert "base_url" in config
