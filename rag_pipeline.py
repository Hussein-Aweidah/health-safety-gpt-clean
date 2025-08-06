import os
from dotenv import load_dotenv
from datetime import datetime

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.vectorstores import VectorStoreConfig

# --- Load API key ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Set it in your .env or Streamlit secrets.")

# --- Paths ---
FAISS_INDEX_DIR = "faiss_index"
DOCS_DIR = "docs"

# --- Load and split documents ---
loaders = [
    PyPDFLoader(os.path.join(DOCS_DIR, fn))
    for fn in os.listdir(DOCS_DIR)
    if fn.lower().endswith(".pdf")
]
docs = []
for loader in loaders:
    docs.extend(loader.load())

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(docs)
texts = [doc.page_content for doc in splits]
metadatas = [doc.metadata for doc in splits]

# --- Embedding & FAISS setup ---
embedding = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
config = VectorStoreConfig(embedding=embedding, distance_strategy=DistanceStrategy.COSINE)

if os.path.isdir(FAISS_INDEX_DIR):
    vectordb = FAISS.load_local(FAISS_INDEX_DIR, config=config)
else:
    vectordb = FAISS.from_texts(texts=texts, embedding=embedding, metadatas=metadatas)
    vectordb.save_local(FAISS_INDEX_DIR)

retriever = vectordb.as_retriever(search_kwargs={"k": 5})
qa_chain = RetrievalQA.from_chain_type(
    llm=OpenAI(openai_api_key=OPENAI_API_KEY),
    retriever=retriever,
    return_source_documents=True
)

# --- Answer with fallback ---
def get_answer(query: str):
    """
    Uses documents first, then GPT if irrelevant.
    Returns: answer, sources[], start_page, end_page, timestamp
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

    # Detect fallback
    fallback_phrases = [
        "i don't know",
        "i am not sure",
        "i'm sorry, but i don't know",
        "no relevant information",
        "as it is unrelated to the context"
    ]
    fallback_needed = (
        not docs or
        any(phrase in answer.strip().lower() for phrase in fallback_phrases)
    )

    # Use GPT directly if fallback needed
    if fallback_needed:
        llm = OpenAI(openai_api_key=OPENAI_API_KEY)
        answer = llm.invoke(query)
        sources = []
        pages = []

    start_page = min(pages) if pages else None
    end_page = max(pages) if pages else None
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return answer, sorted(sources), start_page, end_page, timestamp

# --- Generate response for app.py ---
def generate_response(query: str):
    """
    Return: (answer, source string, start page str, end page str, timestamp)
    """
    answer, sources, start_page, end_page, timestamp = get_answer(query)
    source_list = ", ".join(sources) if sources else "Unknown"
    sp = str(start_page) if start_page is not None else "N/A"
    ep = str(end_page) if end_page is not None else "N/A"
    return answer, source_list, sp, ep, timestamp
