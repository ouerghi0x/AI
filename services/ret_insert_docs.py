import os

from langchain.retrievers import ParentDocumentRetriever
from langchain_community.vectorstores import Cassandra
from langchain_core.stores import InMemoryStore
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import TokenTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from env_loader import load_environment
from services.cassandra_service import CassandraManager
from services.load_data import DataLoader

load_environment()
class ParentRetriever:
    def __init__(self):
        self.cassandraInterface = CassandraManager()
        self.parent_store = InMemoryStore()
        self.astra_db_store = self.setup_vector_store()
        self.semantic_chunker = SemanticChunker(
           GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",  # Gecko model
                google_api_key=os.getenv("LANGSMITH_API_KEY")
            )
        )
        self.parent_retriever = self.configure_parent_child_splitters()

    def setup_vector_store(self) -> Cassandra | None:
        try:
            hf_embedding = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",  # Gecko model
                google_api_key=os.getenv("LANGSMITH_API_KEY")
            )
            astra_db_store: Cassandra = Cassandra(
                embedding=hf_embedding,
                session=self.cassandraInterface.session,
                keyspace=self.cassandraInterface.KEYSPACE,
                table_name="vectores_new"
            )
            return astra_db_store
        except Exception as e:
            print(f"Error initializing AstraDBVectorStore: {e}")
            return None

    def configure_parent_child_splitters(self):
        if self.astra_db_store is None:
            raise RuntimeError("Vector store is not initialized")
        parent_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=0)
        child_splitter = TokenTextSplitter(chunk_size=128, chunk_overlap=0)
        parent_retriever = ParentDocumentRetriever(
            vectorstore=self.astra_db_store,
            docstore=self.parent_store,
            child_splitter=child_splitter,
            parent_splitter=parent_splitter,
        )
        return parent_retriever

    async def add_documents_to_parent_retriever(self):
        load_data = DataLoader(os.getenv('UPLOAD_DIR'))
        documents, docs_ids = load_data.load_documents(self.semantic_chunker, self.cassandraInterface.session)
        self.parent_retriever.docstore.mset(list(zip(docs_ids, documents)))
        for i, doc in enumerate(documents):
            doc.metadata["doc_id"] = docs_ids[i]
        self.astra_db_store.clear()
        await self.parent_retriever.vectorstore.aadd_documents(documents=documents)
