
from langchain_core.documents import Document
import uuid
import os
import threading
from langchain_community.document_loaders import PDFPlumberLoader  
class DataLoader:
    def __init__(self, upload_dir):
        self.UPLOAD_DIR = upload_dir
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        self.keyspace_cassandra=os.getenv("KEYSPACE")
    def load_documents(self,semantic_spliter,session):
        docs = []
        all_files = os.listdir(self.UPLOAD_DIR)
        threads = []
        for file in all_files:
            if(session.execute(f"SELECT * FROM {self.keyspace_cassandra}.documents WHERE FILE_name = %s ALLOW FILTERING", (file,)).one() is not None):
                continue
            else:
                document_id = (uuid.uuid4())
                session.execute(f"INSERT INTO {self.keyspace_cassandra}.documents (FILE_name,document_id) VALUES (%s,%s)", (file,document_id))
                #session.commit()
                self.choosing_logic(docs, threads, file)

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        docs=semantic_spliter.split_documents(docs)
        doc_ids = [str(uuid.uuid4()) for _ in docs]
        return docs, doc_ids

    def choosing_logic(self, docs, threads, file):
        if file.endswith(".pdf"):
            thread = threading.Thread(target=self.process_pdf_file, args=(docs, file))
            threads.append(thread)
        elif file.endswith(".csv"):
            thread = threading.Thread(target=self.load_csv_to_documents, args=(docs, file))
            threads.append(thread)
        elif file.endswith(".txt"):
            thread = threading.Thread(target=self.process_txt_file, args=(docs, file))
            threads.append(thread)


    

    def process_pdf_file(self, docs, file):
        full_path = os.path.join(self.UPLOAD_DIR, file)
        loader = PDFPlumberLoader(full_path)
        document = loader.load()
        if document is not None:
            docs.extend(document)
    def process_txt_file(self, docs, file):
        from langchain_community.document_loaders import TextLoader

        full_path = os.path.join(self.UPLOAD_DIR, file)
        loader = TextLoader(full_path, encoding="utf-8")
        document = loader.load()
        if document is not None:
            docs.extend(document)

    def load_csv_to_documents(self, docs, file):
        file_path = os.path.join(self.UPLOAD_DIR, file)
        if not file.endswith(".csv"):
            return
        import  pandas as pd
        df = pd.read_csv(str(file_path))
        df['meta'] = df.apply(lambda row: {"source": file_path}, axis=1)
        records = df.to_dict('records')
        columns = df.columns
        ds = []

        for record in records:
            full_text = "\n".join([f"{col}: {record[col]}" for col in columns])
            meta = record.get('meta', {})
            doc = Document(page_content=full_text, metadata=meta)
            ds.append(doc)

        docs.extend(ds)
