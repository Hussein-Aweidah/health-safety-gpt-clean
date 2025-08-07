# build_faiss_index.py
import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load .env if needed
from dotenv import load_dotenv
load_dotenv()

# Constants
DOCS_DIR = "docs"
FAISS_INDEX_DIR = "faiss_index"

# Load PDFs
loaders = [PyPDFLoader(os.path.join(DOCS_DIR, file))
           for file in os.listdir(DOCS_DIR) if file.endswith(".pdf")]
docs = []
for loader in loaders:
    docs.extend(loader.load())

# Split documents
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(docs)

# Embed and store in FAISS
embedding = OpenAIEmbeddings()
vectordb = FAISS.from_documents(splits, embedding)
vectordb.save_local(FAISS_INDEX_DIR)
print(f"✅ FAISS index saved to {FAISS_INDEX_DIR}")
