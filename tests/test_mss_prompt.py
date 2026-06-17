"""Tests for MSS Prompt — LLLM-inspired first-class typed object."""
import pytest
from mssclaw.core.mss_prompt import MSSPrompt, MSSParser


class TestMSSParser:
    def test_parse_xml_tags(self):
        p = MSSParser(xml_tags=["violations", "score"])
        result = p.parse("<violations>3 found</violations><score>0.4</score>")
        assert result["xml_tags"]["violations"] == ["3 found"]
        assert result["xml_tags"]["score"] == ["0.4"]

    def test_parse_md_code_block(self):
        p = MSSParser(md_tags=["python"])
        result = p.parse("```python\nprint('hello')\n```")
        assert "python" in result["md_tags"]

    def test_required_tag_missing(self):
        p = MSSParser(xml_tags=["score"], required_xml_tags=["violations"])
        errors = p.validate("no violations here")
        assert "violations" in errors

    def test_required_tag_present(self):
        p = MSSParser(required_xml_tags=["score"])
        errors = p.validate("<score>0.8</score>")
        assert len(errors) == 0

    def test_multiline_xml(self):
        p = MSSParser(xml_tags=["report"])
        result = p.parse("<report>\nline1\nline2\n</report>")
        assert "line1" in result["xml_tags"]["report"][0]

    def test_min_confidence_default(self):
        p = MSSParser()
        assert p.min_confidence == 0.0


class TestMSSPrompt:
    def test_render(self):
        p = MSSPrompt(path="test", template="Analyze {target}.")
        assert p(target="test.py") == "Analyze test.py."

    def test_template_vars(self):
        p = MSSPrompt(path="test", template="Review {a} and {b} for {c}.")
        assert p.template_vars == {"a", "b", "c"}

    def test_missing_var(self):
        p = MSSPrompt(path="test", template="Review {target}.")
        with pytest.raises(ValueError, match="target"):
            p(other="value")

    def test_validate_args_ok(self):
        p = MSSPrompt(path="test", template="Hello {name}.")
        assert p.validate_args({"name": "World"}) == []

    def test_validate_args_missing(self):
        p = MSSPrompt(path="test", template="Hello {name}, {date}.")
        assert "name" in p.validate_args({"date": "today"})
        assert "date" in p.validate_args({"name": "Alice"})

    def test_can_execute_low(self):
        p = MSSPrompt(path="test", template="Hi", heat_tax_budget=0.3, delta_min=0.5)
        ok, _ = p.can_execute(0.1, 0.7)
        assert ok

    def test_can_execute_heat_tax_exceeded(self):
        p = MSSPrompt(path="test", template="Hi", heat_tax_budget=0.3)
        ok, reason = p.can_execute(0.35, 0.7)
        assert not ok
        assert "budget" in reason.lower() or "0.35" in reason

    def test_can_execute_delta_too_low(self):
        p = MSSPrompt(path="test", template="Hi", delta_min=0.5)
        ok, reason = p.can_execute(0.1, 0.3)
        assert not ok
        assert "delta" in reason.lower() or "0.3" in reason

    def test_normative_constraints(self):
        p = MSSPrompt(path="test", template="Hi",
                       normative_constraints=["no_bare_except_pass"])
        assert "no_bare_except_pass" in p.normative_constraints

    def test_default_values(self):
        p = MSSPrompt(path="test", template="Hi")
        assert p.heat_tax_budget == 0.3
        assert p.delta_min == 0.5
        assert p.parser is None
        assert p.tools == []

    def test_combined_render_and_parse(self):
        p = MSSPrompt(
            path="code_review/system",
            template="Review {target}. Return in <score> tag.",
            parser=MSSParser(xml_tags=["score"], required_xml_tags=["score"]),
            heat_tax_budget=0.3,
        )
        rendered = p(target="core.py")
        assert "core.py" in rendered
        ok, _ = p.can_execute(0.1, 0.7)
        assert ok
        parsed = p.parser.parse("<score>0.95</score>")
        assert "0.95" in str(parsed["xml_tags"]["score"])
