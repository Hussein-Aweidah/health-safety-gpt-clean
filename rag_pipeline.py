import os
from dotenv import load_dotenv
from datetime import datetime
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- Config & Paths ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FAISS_INDEX_DIR = "faiss_index"
DOCS_DIR = "docs"

# --- Load & Split Documents ---
loaders = [
    PyPDFLoader(os.path.join(DOCS_DIR, fn))
    for fn in os.listdir(DOCS_DIR)
    if fn.lower().endswith(".pdf")
]
docs = []
for loader in loaders:
    docs.extend(loader.load())

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
splits = text_splitter.split_documents(docs)
texts = [doc.page_content for doc in splits]
metadatas = [doc.metadata for doc in splits]

# --- Embedding & Vector Store Setup ---
embedding = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Load FAISS index if exists; otherwise, create and save
if os.path.isdir(FAISS_INDEX_DIR):
    vectordb = FAISS.load_local(FAISS_INDEX_DIR, embedding)
else:
    vectordb = FAISS.from_texts(texts=texts, embedding=embedding, metadatas=metadatas)
    vectordb.save_local(FAISS_INDEX_DIR)

retriever = vectordb.as_retriever(search_kwargs={"k": 5})

# --- QA Chain ---
qa_chain = RetrievalQA.from_chain_type(
    llm=OpenAI(openai_api_key=OPENAI_API_KEY),
    retriever=retriever,
    return_source_documents=True
)

def get_answer(query: str):
    """
    Run the QA chain and extract:
      - answer text
      - sorted list of source filenames
      - start_page (min of all pages)
      - end_page   (max of all pages)
      - timestamp
    """
    result = qa_chain(query)
    answer = result["result"]
    docs = result["source_documents"]

    sources = set()
    pages = []
    for doc in docs:
        md = doc.metadata
        src = os.path.basename(md.get("source", "Unknown"))
        pg = md.get("page", None)
        sources.add(src)
        try:
            pages.append(int(pg))
        except (TypeError, ValueError):
            pass

    if pages:
        start_page = min(pages)
        end_page = max(pages)
    else:
        start_page = end_page = None

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return answer, sorted(sources), start_page, end_page, timestamp

def generate_response(query: str):
    """
    Returns a 5‑tuple matching app.py’s unpacking:
      (answer, source_list_str, start_page_str, end_page_str, timestamp)
    """
    answer, sources, start_page, end_page, timestamp = get_answer(query)
    source_list = ", ".join(sources) if sources else "Unknown"
    sp = str(start_page) if start_page is not None else "N/A"
    ep = str(end_page)   if end_page   is not None else "N/A"
    return answer, source_list, sp, ep, timestamp
