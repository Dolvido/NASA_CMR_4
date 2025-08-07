from __future__ import annotations
from typing import Iterable, List, Dict, Any
import os
import os
os.environ.setdefault('CHROMA_TELEMETRY_ENABLED','false')
import chromadb
from chromadb.config import Settings as ChromaSettings
from cmr_agent.config import settings

class ChromaStore:
    def __init__(self, collection_name: str = 'nasa_docs'):
        persist_dir = settings.vector_db_dir
        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.Client(
            ChromaSettings(persist_directory=persist_dir, anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(collection_name)

    def add_texts(self, ids: List[str], texts: List[str], metadatas: List[Dict[str, Any]] | None = None):
        self.collection.add(ids=ids, documents=texts, metadatas=metadatas)

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        res = self.collection.query(query_texts=[query], n_results=k)
        out: List[Dict[str, Any]] = []
        for ids, docs, metas in zip(res.get('ids', [[]])[0], res.get('documents', [[]])[0], res.get('metadatas', [[]])[0]):
            out.append({'id': ids, 'text': docs, 'metadata': metas})
        return out

# Simple ingestion helper

def ingest_docs(docs: Iterable[Dict[str, Any]], id_key: str = 'id', text_key: str = 'text', meta_keys: List[str] | None = None, collection: str = 'nasa_docs'):
    store = ChromaStore(collection)
    ids, texts, metas = [], [], []
    for d in docs:
        ids.append(str(d[id_key]))
        texts.append(str(d[text_key]))
        if meta_keys:
            metas.append({k: d.get(k) for k in meta_keys})
        else:
            metas.append({})
    if ids:
        store.add_texts(ids, texts, metas)
    return len(ids)

