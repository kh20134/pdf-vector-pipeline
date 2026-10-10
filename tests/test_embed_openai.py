import sys
import types

from pdfvec.embed import OpenAIEmbedder


def test_openai_embedder_batches_and_sorts(monkeypatch):
    class Item:
        def __init__(self, index, embedding):
            self.index = index
            self.embedding = embedding

    class Response:
        def __init__(self, data):
            self.data = data

    class Embeddings:
        def __init__(self):
            self.calls = []

        def create(self, model, input):
            self.calls.append(list(input))
            data = [Item(index, [float(index), 1.0]) for index in range(len(input))]
            return Response(list(reversed(data)))

    embeddings = Embeddings()

    class OpenAI:
        def __init__(self):
            self.embeddings = embeddings

    module = types.ModuleType("openai")
    module.OpenAI = OpenAI
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    embedder = OpenAIEmbedder("text-embedding-3-small")
    texts = [f"문장 {index}" for index in range(3)]
    assert embedder.embed_documents(texts) == [[0.0, 1.0], [1.0, 1.0], [2.0, 1.0]]
    assert embedder.embed_query("질의") == [0.0, 1.0]
    assert embeddings.calls[0] == texts
