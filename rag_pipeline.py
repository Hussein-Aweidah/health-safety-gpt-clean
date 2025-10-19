import os
from datetime import datetime
from glob import glob
from dotenv import load_dotenv

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document

try:
    from langchain_core.prompts import PromptTemplate
except ImportError:
    from langchain.prompts import PromptTemplate

from langchain.chains import LLMChain
from langchain_community.document_loaders import PyMuPDFLoader
try:
    from langchain_community.vectorstores import FAISS
except ImportError:
    from langchain.vectorstores import FAISS

try:
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
except ImportError:
    from langchain.embeddings import OpenAIEmbeddings  # type: ignore
    from langchain.chat_models import ChatOpenAI      # type: ignore

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Set it in .env or Streamlit secrets.")

FAISS_INDEX_DIR = "faiss_index"
DOCS_DIR = "docs"
EMBEDDING_MODEL_CANDIDATES = ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]
DEFAULT_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def _pick_embedding_model() -> str:
    return os.getenv("OPENAI_EMBEDDING_MODEL") or EMBEDDING_MODEL_CANDIDATES[0]


def _faiss_exists() -> bool:
    return os.path.isdir(FAISS_INDEX_DIR) and any(n.endswith((".faiss", ".pkl")) for n in os.listdir(FAISS_INDEX_DIR))


def _build_faiss_from_docs() -> None:
    pdfs = sorted(set(glob(os.path.join(DOCS_DIR, "*.pdf")) + glob(os.path.join(DOCS_DIR, "**/*.pdf"), recursive=True)))
    if not pdfs:
        return
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = []
    for path in pdfs:
        for d in PyMuPDFLoader(path).load():
            for i, c in enumerate(splitter.split_text(d.page_content or "")):
                m = (d.metadata or {}).copy()
                m["source_path"] = path
                m["chunk_index"] = i
                chunks.append(Document(page_content=c, metadata=m))
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model=_pick_embedding_model())
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_INDEX_DIR)


def _get_retriever(k: int = 5):
    if not _faiss_exists():
        _build_faiss_from_docs()
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model=_pick_embedding_model())
    db = FAISS.load_local(FAISS_INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
    return db.as_retriever(search_kwargs={"k": k})


def _get_qa_chain():
    llm = ChatOpenAI(model=DEFAULT_CHAT_MODEL, temperature=0, openai_api_key=OPENAI_API_KEY)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "You are a health and safety expert. Answer the question from the context.\n\n"
            "Context:\n{context}\n\n"
            "Question: {question}\n\n"
            "Answer clearly and concisely:"
        ),
    )
    return LLMChain(llm=llm, prompt=prompt)


def _format_response_with_bullets(answer: str, query: str) -> str:
    bullet_keywords = {
        'procedure','procedures','steps','step','guidance','guidelines','requirements','requirement',
        'hazards','hazard','risks','risk','controls','control','measures','measure','actions','action',
        'checklist','list','items','points','ways','methods','tips','safety','compliance','training',
        'equipment','maintenance','how to','what are','explain','describe','outline','summarize'
    }
    numbered_keywords = {'steps','step','procedure','procedures','sequence','order','first','second','third','then','next','finally'}
    ql = query.lower()
    use_bullets = any(k in ql for k in bullet_keywords)
    use_numbers = any(k in ql for k in numbered_keywords)
    if '•' in answer or '-' in answer or answer.count('\n') > 3 or len(answer) < 200:
        return answer
    if use_bullets:
        sentences = [s.strip() for s in answer.split('. ') if s.strip()]
        if len(sentences) > 2:
            out = "Based on the WorkSafe guidance:\n\n"
            if use_numbers:
                for i, s in enumerate(sentences, 1):
                    if not s.endswith('.'):
                        s += '.'
                    out += f"{i}. {s}\n"
            else:
                for s in sentences:
                    if not s.endswith('.'):
                        s += '.'
                    out += f"• {s}\n"
            return out
    return answer


def get_answer(query: str):
    try:
        qa_chain = _get_qa_chain()
        retriever = _get_retriever(k=5)
        docs = retriever.get_relevant_documents(query)
        context = "\n".join(d.page_content or "" for d in docs)
        result = qa_chain.invoke({"context": context, "question": query})
        answer = result.get("text") if isinstance(result, dict) else getattr(result, "text", str(result))
        answer = answer or ""
        answer = _format_response_with_bullets(answer, query)
        src_docs = docs
    except Exception as e:
        print(f"Main QA chain failed: {e}")
        answer = ("I'm having trouble accessing the WorkSafe documents right now. "
                  "Here is general guidance based on my training.")
        sources = []
        pages = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return answer, sources, pages, timestamp

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

    fallback_phrases = {
        "i don't know","i am not sure","i'm sorry, but i don't know",
        "no relevant information","as it is unrelated to the context",
    }
    fallback_needed = (not src_docs) or any(p in (answer.strip().lower()) for p in fallback_phrases)
    if fallback_needed:
        llm = ChatOpenAI(model=DEFAULT_CHAT_MODEL, temperature=0, openai_api_key=OPENAI_API_KEY, max_tokens=1000)
        answer = llm.invoke(query).content
        answer = _format_response_with_bullets(answer, query)
        sources = set()
        pages = []

    start_page = min(pages) if pages else None
    end_page = max(pages) if pages else None
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return answer, sorted(sources), start_page, end_page, timestamp


def generate_response(query: str):
    try:
        answer, sources, start_page, end_page, timestamp = get_answer(query)
        source_list = ", ".join(sources) if sources else "Unknown"
        sp = str(start_page) if start_page is not None else "N/A"
        ep = str(end_page) if end_page is not None else "N/A"
        return answer, source_list, sp, ep, timestamp
    except Exception as e:
        print(f"All QA methods failed: {e}")
        fallback_answer = ("I apologize, but I'm experiencing technical difficulties. "
                           "Please try again later or contact support if the issue persists.")
        return fallback_answer, "Unknown", "N/A", "N/A", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
