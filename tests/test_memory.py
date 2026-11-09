import pytest

from app.core.config import settings
from app.services import vector_service


class FakeVector:
    def __init__(self):
        self.added = []
        self.deleted = []
        self.hits = []
        self.fail = False

    def add_messages(self, conversation_id, messages):
        if self.fail:
            raise RuntimeError("chroma is down")
        self.added.append((conversation_id, messages))

    def search(self, conversation_id, query, n_results, max_distance):
        if self.fail:
            raise RuntimeError("chroma is down")
        return self.hits

    def delete_conversation(self, conversation_id):
        self.deleted.append(conversation_id)


@pytest.fixture
def fake_vector(monkeypatch):
    fake = FakeVector()
    monkeypatch.setattr(settings, "memory_enabled", True)
    monkeypatch.setattr(vector_service, "add_messages", fake.add_messages)
    monkeypatch.setattr(vector_service, "search", fake.search)
    monkeypatch.setattr(vector_service, "delete_conversation", fake.delete_conversation)
    return fake


def test_each_turn_is_indexed(client, fake_vector):
    cid = client.post("/api/chat", json={"message": "hello"}).json()["conversation_id"]
    assert len(fake_vector.added) == 1
    added_cid, messages = fake_vector.added[0]
    assert added_cid == cid
    assert [m["role"] for m in messages] == ["user", "assistant"]


def test_old_message_is_recalled_beyond_the_history_window(
    client, fake_vector, fake_ollama, monkeypatch
):
    monkeypatch.setattr(settings, "max_history_messages", 2)
    fake_vector.hits = [
        {"role": "user", "content": "My name is Tanvir", "message_id": 1}
    ]

    cid = client.post("/api/chat", json={"message": "My name is Tanvir"}).json()["conversation_id"]
    client.post("/api/chat", json={"message": "tell me a joke", "conversation_id": cid})
    client.post("/api/chat", json={"message": "What is my name?", "conversation_id": cid})

    prompt = fake_ollama.system_prompt()
    assert "Relevant earlier messages" in prompt
    assert "My name is Tanvir" in prompt


def test_no_search_when_recent_history_covers_everything(client, fake_vector, fake_ollama):
    fake_vector.hits = [{"role": "user", "content": "old", "message_id": 1}]
    cid = client.post("/api/chat", json={"message": "hi"}).json()["conversation_id"]
    client.post("/api/chat", json={"message": "hi again", "conversation_id": cid})
    assert "Relevant earlier messages" not in fake_ollama.system_prompt()


def test_chroma_failure_does_not_break_chat(client, fake_vector):
    fake_vector.fail = True
    r = client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert r.json()["reply"] == "Hello from fake model"


def test_deleting_a_conversation_removes_its_vectors(client, fake_vector):
    cid = client.post("/api/chat", json={"message": "hello"}).json()["conversation_id"]
    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    assert fake_vector.deleted == [cid]