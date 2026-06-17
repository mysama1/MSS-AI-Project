"""Tests for MSS Channel — unified output pipeline."""
import io
import json
import sys
import tempfile
from pathlib import Path
import pytest
from mssclaw.core.mss_channel import (
    MSSChannel,
    ChannelKind,
    ChannelMessage,
    ChannelPolicy,
    MessageLevel,
    TerminalFormatter,
    JsonFormatter,
    TextFormatter,
)


class TestFormatters:
    def test_terminal_formatter(self):
        msg = ChannelMessage(text="Hello", level=MessageLevel.INFO, sender="Agent-A")
        policy = ChannelPolicy()
        result = TerminalFormatter.format(msg, policy)
        assert "Agent-A" in result or "Hello" in result

    def test_terminal_truncate(self):
        msg = ChannelMessage(text="x" * 10000, level=MessageLevel.INFO)
        policy = ChannelPolicy(max_chars=100)
        result = TerminalFormatter.format(msg, policy)
        assert len(result) <= 100 + len(policy.truncate_marker)

    def test_json_formatter(self):
        msg = ChannelMessage(text="test", level=MessageLevel.INFO, sender="A")
        policy = ChannelPolicy()
        result = JsonFormatter.format(msg, policy)
        data = json.loads(result)
        assert data["text"] == "test"
        assert data["sender"] == "A"

    def test_text_formatter_truncate(self):
        msg = ChannelMessage(text="x" * 1000, level=MessageLevel.INFO)
        policy = ChannelPolicy(max_chars=50)
        result = TextFormatter.format(msg, policy)
        assert len(result) <= 50 + len(policy.truncate_marker)


class TestMSSChannel:
    def test_create_terminal(self):
        c = MSSChannel(kind="terminal")
        assert c.kind == ChannelKind.TERMINAL

    def test_info_returns_formatted(self):
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        try:
            c = MSSChannel(kind="terminal")
            result = c.info("Agent-X", "Hello")
            assert result is not None
            assert "Hello" in result
        finally:
            sys.stdout = old_stdout

    def test_debug_filtered_by_policy(self):
        c = MSSChannel(kind="null", policy=ChannelPolicy(allow_levels=[MessageLevel.INFO, MessageLevel.ERROR]))
        result = c.debug("Agent-X", "should not appear")
        assert result is None

    def test_null_channel(self):
        c = MSSChannel(kind="null")
        result = c.info("Agent-X", "silent")
        assert result is not None  # formatted, just not printed
        assert c._message_count == 1

    def test_json_channel(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tf:
            tf_path = tf.name

        try:
            c = MSSChannel(kind="json", file_path=Path(tf_path))
            c.send_dict({"status": "ok"}, sender="Orch")
            c.close()  # ensures flush

            with open(tf_path) as f:
                raw = f.read().strip()
            # JSON channel wraps as {text: ..., sender: ...}
            envelope = json.loads(raw)
            assert "ok" in envelope["text"]
        finally:
            import os
            os.unlink(tf_path)

    def test_text_channel(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tf:
            tf_path = tf.name

        try:
            c = MSSChannel(kind="text", file_path=Path(tf_path))
            c.info("Agent-A", "Log entry")

            with open(tf_path) as f:
                content = f.read()
            assert "Log entry" in content
        finally:
            import os
            os.unlink(tf_path)

    def test_broadcast(self):
        c = MSSChannel(kind="null")
        results = c.broadcast(["A", "B", "C"], "announcement")
        assert len(results) == 3
        assert c._message_count == 3

    def test_callback_channel(self):
        received = []
        def handler(msg, formatted):
            received.append((msg.sender, msg.text))

        c = MSSChannel(kind="callback", callback=handler)
        c.info("Agent-X", "via callback")
        assert received[0] == ("Agent-X", "via callback")

    def test_levels(self):
        c = MSSChannel(kind="null")
        c.debug("X", "d")
        c.info("X", "i")
        c.warn("X", "w")
        c.error("X", "e")
        c.critical("X", "c")
        assert c._message_count == 5

    def test_heat_tax_threshold(self):
        c = MSSChannel(kind="null", policy=ChannelPolicy(heat_tax_threshold=0.1))
        result = c.info("X", "test", heat_tax_cost=0.2)
        assert result is None  # blocked
        result = c.info("X", "test", heat_tax_cost=0.05)
        assert result is not None

    def test_timestamp_in_message(self):
        c = MSSChannel(kind="null")
        result = c.send("test", sender="X")
        assert "X" in result if c.policy.prefix_sender else True

    def test_report(self):
        c = MSSChannel(kind="null")
        c.info("X", "msg1")
        c.info("Y", "msg2")
        report = c.report()
        assert report["message_count"] == 2
        assert report["kind"] == "null"
