import os
from datetime import datetime
from dotenv import load_dotenv

from glob import glob
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.schema import Document

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Set it in your .env or Streamlit secrets.")

FAISS_INDEX_DIR = "faiss_index"
DOCS_DIR = "docs"

def _faiss_exists() -> bool:
    return os.path.isdir(FAISS_INDEX_DIR) and any(
        name.endswith(".faiss") or name.endswith(".pkl")
        for name in os.listdir(FAISS_INDEX_DIR)
    )

def _build_faiss_from_docs():
    pdfs = sorted(set(glob(os.path.join(DOCS_DIR, "*.pdf")) +
                      glob(os.path.join(DOCS_DIR, "**/*.pdf"), recursive=True)))
    if not pdfs:
        return
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = []
    for path in pdfs:
        pages = PyMuPDFLoader(path).load()
        for d in pages:
            for i, c in enumerate(splitter.split_text(d.page_content)):
                m = d.metadata.copy()
                m["source_path"] = path
                m["chunk_index"] = i
                chunks.append(Document(page_content=c, metadata=m))
    embeddings = OpenAIEmbeddings()
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_INDEX_DIR)

def _get_retriever(k: int = 5):
    if not _faiss_exists():
        _build_faiss_from_docs()
    embeddings = OpenAIEmbeddings()
    db = FAISS.load_local(
        FAISS_INDEX_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )
    return db.as_retriever(search_kwargs={"k": k})

def _get_qa_chain():
    retriever = _get_retriever(k=8)
    llm = ChatOpenAI(temperature=0)
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True
    )

def get_answer(query: str):
    qa_chain = _get_qa_chain()
    result = qa_chain.invoke({"query": query})
    answer = result["result"]
    src_docs = result.get("source_documents", [])

    sources = set()
    pages = []
    for doc in src_docs:
        md = doc.metadata or {}
        src = os.path.basename(md.get("source") or md.get("source_path") or "Unknown")
        pg = md.get("page")
        sources.add(src)
        try:
            pages.append(int(pg))
        except (TypeError, ValueError):
            pass

    fallback_phrases = [
        "i don't know",
        "i am not sure",
        "i'm sorry, but i don't know",
        "no relevant information",
        "as it is unrelated to the context",
    ]
    fallback_needed = (not src_docs) or any(p in answer.strip().lower() for p in fallback_phrases)

    if fallback_needed:
        llm = ChatOpenAI(temperature=0)
        answer = llm.invoke(query).content
        sources = []
        pages = []

    start_page = min(pages) if pages else None
    end_page = max(pages) if pages else None
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return answer, sorted(sources), start_page, end_page, timestamp

def generate_response(query: str):
    answer, sources, start_page, end_page, timestamp = get_answer(query)
    source_list = ", ".join(sources) if sources else "Unknown"
    sp = str(start_page) if start_page is not None else "N/A"
    ep = str(end_page) if end_page is not None else "N/A"
    return answer, source_list, sp, ep, timestamp
