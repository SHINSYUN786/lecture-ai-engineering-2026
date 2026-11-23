"""app/ask.py のテスト（APIキー不要。genai.Client の代わりに偽物を使う）。"""

from types import SimpleNamespace

from app import ask as ask_mod


class FakeModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, model, contents, config=None):
        self.calls.append((model, contents, config))
        usage = SimpleNamespace(prompt_token_count=7, candidates_token_count=3)
        return SimpleNamespace(text="答え", usage_metadata=usage)


class FakeChat:
    def __init__(self):
        self.sent = []

    def send_message(self, text):
        self.sent.append(text)
        usage = SimpleNamespace(prompt_token_count=10 * len(self.sent), candidates_token_count=2)
        return SimpleNamespace(text=f"返答{len(self.sent)}", usage_metadata=usage)


class FakeClient:
    def __init__(self):
        self.models = FakeModels()
        self.chat = FakeChat()
        self.chats = SimpleNamespace(create=lambda model, config=None: self.chat)


def test_ask_returns_tokens_and_passes_temperature():
    client = FakeClient()
    result = ask_mod.ask("Q", model="m", temperature=1.5, client=client)
    assert (result.text, result.input_tokens, result.output_tokens) == ("答え", 7, 3)
    model, contents, config = client.models.calls[0]
    assert (model, contents, config.temperature) == ("m", "Q", 1.5)


def test_ask_without_temperature_has_no_config():
    client = FakeClient()
    ask_mod.ask("Q", client=client)
    assert client.models.calls[0][2] is None


def test_format_usage():
    text = ask_mod.format_usage(ask_mod.Result("x", 7, 3, 1.234))
    assert "入力=7" in text and "出力=3" in text and "1.23秒" in text


def test_chat_loop_keeps_one_chat_session(monkeypatch, capsys):
    client = FakeClient()
    inputs = iter(["一つ目", "二つ目", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))
    ask_mod.chat_loop(client=client)
    assert client.chat.sent == ["一つ目", "二つ目"]
    out = capsys.readouterr().out
    assert "返答1" in out and "返答2" in out
    assert "入力=10" in out and "入力=20" in out  # 履歴ぶん入力トークンが増える
