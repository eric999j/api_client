"""utils.py 單元測試"""
import pytest
from utils import (
    format_json,
    minify_json,
    parse_headers,
    headers_to_text,
    format_size,
    validate_url,
    validate_json,
    normalize_dify_request_body,
    get_dify_response_mode,
    extract_variables,
    replace_variables,
)


class TestFormatJson:
    def test_valid_json(self):
        result = format_json('{"a":1,"b":2}')
        assert '"a": 1' in result
        assert '"b": 2' in result

    def test_empty_string(self):
        assert format_json("") == ""

    def test_invalid_json_returns_original(self):
        assert format_json("not json") == "not json"

    def test_custom_indent(self):
        result = format_json('{"a":1}', indent=2)
        assert "  " in result


class TestMinifyJson:
    def test_minifies(self):
        result = minify_json('{\n  "a": 1\n}')
        assert result == '{"a":1}'

    def test_empty_string(self):
        assert minify_json("") == ""

    def test_invalid_json_returns_original(self):
        assert minify_json("invalid") == "invalid"


class TestParseHeaders:
    def test_single_header(self):
        assert parse_headers("Content-Type: application/json") == {
            "Content-Type": "application/json"
        }

    def test_multiple_headers(self):
        text = "Accept: */*\nAuthorization: Bearer token123"
        result = parse_headers(text)
        assert result["Accept"] == "*/*"
        assert result["Authorization"] == "Bearer token123"

    def test_comment_line_ignored(self):
        text = "# This is a comment\nX-Custom: value"
        result = parse_headers(text)
        assert "#" not in str(result.keys())
        assert result["X-Custom"] == "value"

    def test_empty_input(self):
        assert parse_headers("") == {}
        assert parse_headers(None) == {}

    def test_duplicate_headers_merged(self):
        text = "Cookie: a=1\nCookie: b=2"
        result = parse_headers(text)
        assert result["Cookie"] == "a=1, b=2"


class TestHeadersToText:
    def test_round_trip(self):
        headers = {"A": "1", "B": "2"}
        text = headers_to_text(headers)
        assert "A: 1" in text
        assert "B: 2" in text

    def test_empty(self):
        assert headers_to_text({}) == ""
        assert headers_to_text(None) == ""


class TestFormatSize:
    def test_bytes(self):
        assert format_size(500) == "500 B"

    def test_kilobytes(self):
        assert "KB" in format_size(1500)

    def test_megabytes(self):
        assert "MB" in format_size(2 * 1024 * 1024)

    def test_negative(self):
        assert format_size(-1) == "0 B"


class TestValidateUrl:
    def test_valid_http(self):
        valid, err = validate_url("http://example.com")
        assert valid is True
        assert err is None

    def test_valid_https_with_port(self):
        valid, _ = validate_url("https://localhost:8080/api")
        assert valid is True

    def test_empty_url(self):
        valid, err = validate_url("")
        assert valid is False
        assert err is not None

    def test_missing_scheme(self):
        valid, _ = validate_url("example.com/api")
        assert valid is False


class TestValidateJson:
    def test_valid(self):
        valid, err = validate_json('{"key": "value"}')
        assert valid is True

    def test_empty_is_valid(self):
        valid, _ = validate_json("")
        assert valid is True

    def test_invalid(self):
        valid, err = validate_json("{broken")
        assert valid is False
        assert "JSON" in err


class TestNormalizeDifyRequestBody:
    def test_moves_custom_fields_to_inputs(self):
        body = '{"query":"hi","user":"u1","response_mode":"blocking","custom_field":"val"}'
        result, moved = normalize_dify_request_body(body)
        assert "custom_field" in moved
        import json
        parsed = json.loads(result)
        assert "custom_field" in parsed["inputs"]
        assert "custom_field" not in [k for k in parsed if k != "inputs"]

    def test_non_dify_payload_unchanged(self):
        body = '{"name":"test"}'
        result, moved = normalize_dify_request_body(body)
        assert moved == []
        assert result == body

    def test_empty_input(self):
        result, moved = normalize_dify_request_body("")
        assert result == ""
        assert moved == []


class TestGetDifyResponseMode:
    def test_blocking(self):
        body = '{"query":"q","user":"u","response_mode":"blocking","inputs":{}}'
        assert get_dify_response_mode(body) == "blocking"

    def test_streaming(self):
        body = '{"query":"q","user":"u","response_mode":"streaming","inputs":{}}'
        assert get_dify_response_mode(body) == "streaming"

    def test_non_dify(self):
        assert get_dify_response_mode('{"foo":"bar"}') is None


class TestExtractVariables:
    def test_extracts_variables(self):
        result = extract_variables("Hello {{name}}, your id is {{id}}")
        assert set(result) == {"name", "id"}

    def test_no_variables(self):
        assert extract_variables("no vars here") == []

    def test_empty(self):
        assert extract_variables("") == []


class TestReplaceVariables:
    def test_replaces(self):
        result = replace_variables("{{host}}/api", {"host": "http://localhost"})
        assert result == "http://localhost/api"

    def test_no_match(self):
        result = replace_variables("{{missing}}", {"other": "val"})
        assert result == "{{missing}}"

    def test_empty_text(self):
        assert replace_variables("", {"a": "b"}) == ""
