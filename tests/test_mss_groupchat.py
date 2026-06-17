"""Tests for MSS GroupChat — multi-agent roundtable."""
import pytest
from mssclaw.core.mss_groupchat import (
    MSSGroupChat,
    ChatAgent,
    ChatMessage,
    ChatRole,
    SpeakerStrategy,
)


class TestGroupChat:
    def test_create_and_add_agents(self):
        chat = MSSGroupChat("Test")
        chat.add_agent("alice", priority=0.8, trust_budget=0.9)
        chat.add_agent("bob", priority=0.6)
        assert len(chat._agents) == 2

    def test_remove_agent(self):
        chat = MSSGroupChat("Test")
        chat.add_agent("alice")
        assert chat.remove_agent("alice")
        assert not chat.remove_agent("nobody")

    def test_start_topic(self):
        chat = MSSGroupChat()
        msg = chat.start_topic("Design discussion")
        assert msg.sender_id == "system"
        assert "Design discussion" in msg.text
        assert chat.topic == "Design discussion"

    def test_select_speaker_round_robin(self):
        chat = MSSGroupChat(strategy=SpeakerStrategy.ROUND_ROBIN)
        chat.add_agent("alice")
        chat.add_agent("bob")
        chat.add_agent("carol")

        s1 = chat.select_speaker()
        assert s1 is not None

    def test_select_speaker_by_priority(self):
        chat = MSSGroupChat(strategy=SpeakerStrategy.BY_PRIORITY)
        chat.add_agent("low", priority=0.3, trust_budget=0.5)
        chat.add_agent("high", priority=0.9, trust_budget=0.9)
        speaker = chat.select_speaker()
        assert speaker == "high"

    def test_speak_records_message(self):
        chat = MSSGroupChat(max_rounds=5)
        chat.add_agent("alice")
        chat.start_topic("test")
        msg = chat.speak("alice", "My proposal is...")
        assert msg.sender_id == "alice"
        assert chat._round == 1

    def test_speak_updates_agent_stats(self):
        chat = MSSGroupChat()
        chat.add_agent("alice")
        chat.speak("alice", "hello", heat_tax_cost=0.02, delta_estimate=0.1)
        agent = chat._agents["alice"]
        assert agent.message_count == 1
        assert agent.total_heat_tax == 0.02

    def test_speak_unknown_agent(self):
        chat = MSSGroupChat()
        with pytest.raises(KeyError):
            chat.speak("ghost", "boo")

    def test_max_rounds_stops(self):
        chat = MSSGroupChat(max_rounds=3)
        chat.add_agent("alice")
        chat.speak("alice", "msg1")
        chat.speak("alice", "msg2")
        chat.speak("alice", "msg3")
        ok, reason = chat.should_continue()
        assert not ok
        assert "Max rounds" in reason

    def test_human_input(self):
        chat = MSSGroupChat()
        msg = chat.human_input("I agree")
        assert msg.sender_role == ChatRole.HUMAN
        assert chat._round == 1

    def test_summary(self):
        chat = MSSGroupChat()
        chat.add_agent("alice", priority=0.8)
        chat.add_agent("bob", priority=0.5)
        chat.speak("alice", "msg1", delta_estimate=0.2)
        chat.speak("bob", "msg2", delta_estimate=0.3)
        chat.speak("alice", "msg3", delta_estimate=0.4)
        s = chat.summary()
        assert s["rounds"] == 3
        assert s["total_heat_tax"] > 0
        assert "alice" in s["agents"]
        assert s["agents"]["alice"]["messages"] == 2

    def test_export_transcript(self):
        chat = MSSGroupChat()
        chat.add_agent("alice")
        chat.start_topic("test")
        chat.speak("alice", "hello")
        t = chat.export_transcript()
        assert len(t) == 2  # topic_start + 1 message
        assert t[1]["sender"] == "alice"

    def test_a6_detection(self):
        chat = MSSGroupChat(max_rounds=10)
        chat.add_agent("a")
        chat.add_agent("b")
        chat.add_agent("c")
        # Contradictory messages to trigger A6
        chat.speak("a", "We should use async", delta_estimate=0.1)
        chat.speak("b", "We shouldn't use async at all", delta_estimate=0.1)
        chat.speak("a", "Yes, async is the way", delta_estimate=0.1)
        chat.speak("c", "No, I disagree completely", delta_estimate=0.1)
        assert chat._a6_events

    def test_silence_agent(self):
        chat = MSSGroupChat()
        chat.add_agent("noisy")
        chat.silence_agent("noisy", 60, "too much noise")
        assert chat._agents["noisy"].silenced_until > 0

    def test_silenced_agent_not_selected(self):
        chat = MSSGroupChat()
        chat.add_agent("noisy", priority=1.0)
        chat.add_agent("quiet", priority=0.5)
        chat.silence_agent("noisy", 60)
        speaker = chat.select_speaker()
        assert speaker == "quiet"

    def test_observer_not_selected(self):
        chat = MSSGroupChat()
        chat.add_agent("watcher", role=ChatRole.OBSERVER)
        speaker = chat.select_speaker()
        assert speaker is None

    def test_trust_decay_on_high_heat(self):
        chat = MSSGroupChat(heat_tax_budget=0.01)
        chat.add_agent("spammer", trust_budget=0.8)
        # High heat messages trigger decay
        chat.speak("spammer", "msg1", heat_tax_cost=0.05)
        chat.speak("spammer", "msg2", heat_tax_cost=0.05)
        assert chat._agents["spammer"].trust_budget < 0.8

    def test_on_message_hook(self):
        received = []
        def handler(msg, agent):
            received.append(msg.text)

        chat = MSSGroupChat()
        chat.on("on_message", handler)
        chat.add_agent("alice")
        chat.speak("alice", "hello world")
        assert "hello world" in received
