# build_faiss_index.py
import os
from glob import glob
from dotenv import load_dotenv

from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

load_dotenv()

DOCS_DIR = "docs"
FAISS_INDEX_DIR = "faiss_index"

pdf_paths = sorted(set(glob(os.path.join(DOCS_DIR, "*.pdf")) +
                       glob(os.path.join(DOCS_DIR, "**/*.pdf"), recursive=True)))

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)

docs = []
for path in pdf_paths:
    pages = PyMuPDFLoader(path).load()
    for d in pages:
        for i, chunk in enumerate(splitter.split_text(d.page_content)):
            meta = d.metadata.copy()
            meta["source_path"] = path
            meta["chunk_index"] = i
            docs.append(Document(page_content=chunk, metadata=meta))

embeddings = OpenAIEmbeddings()
db = FAISS.from_documents(docs, embeddings)
db.save_local(FAISS_INDEX_DIR)

print(f"✅ FAISS index saved to {FAISS_INDEX_DIR} | {len(docs)} chunks from {len(pdf_paths)} PDFs")
