import os
from datetime import datetime
from dotenv import load_dotenv

from glob import glob
from langchain_community.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
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
    
    # Configure embeddings with explicit parameters
    embeddings = OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY,
        model="text-embedding-ada-002"  # Explicitly specify embedding model
    )
    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(FAISS_INDEX_DIR)

def _get_retriever(k: int = 5):
    if not _faiss_exists():
        _build_faiss_from_docs()
    
    # Configure embeddings with explicit parameters
    embeddings = OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY,
        model="text-embedding-ada-002"  # Explicitly specify embedding model
    )
    db = FAISS.load_local(
        FAISS_INDEX_DIR,
        embeddings,
        allow_dangerous_deserialization=True
    )
    return db.as_retriever(search_kwargs={"k": k})

def _get_qa_chain():
    """Create a simple QA chain that bypasses RetrievalQA issues"""
    try:
        # Create LLM with minimal parameters
        llm = ChatOpenAI(
            temperature=0,
            openai_api_key=OPENAI_API_KEY
        )
        
        # Create a simple prompt template
        template = """You are a health and safety expert. Answer the following question based on the provided context.

Context: {context}

Question: {question}

Provide a clear, helpful answer based on the context:"""
        
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=template
        )
        
        # Return a simple LLM chain
        return LLMChain(llm=llm, prompt=prompt)
            
    except Exception as e:
        print(f"Error creating QA chain: {e}")
        raise

def _format_response_with_bullets(answer: str, query: str) -> str:
    """Intelligently format responses with bullet points when appropriate."""
    
    # Keywords that suggest bullet points would be helpful
    bullet_keywords = [
        'procedure', 'procedures', 'steps', 'step', 'guidance', 'guidelines',
        'requirements', 'requirement', 'hazards', 'hazard', 'risks', 'risk',
        'controls', 'control', 'measures', 'measure', 'actions', 'action',
        'checklist', 'list', 'items', 'points', 'ways', 'methods', 'tips',
        'safety', 'compliance', 'training', 'equipment', 'maintenance',
        'how to', 'what are', 'explain', 'describe', 'outline', 'summarize'
    ]
    
    # Keywords that suggest numbered steps would be better
    numbered_keywords = [
        'steps', 'step', 'procedure', 'procedures', 'sequence', 'order',
        'first', 'second', 'third', 'then', 'next', 'finally'
    ]
    
    # Check if the query suggests bullet points would be helpful
    query_lower = query.lower()
    should_use_bullets = any(keyword in query_lower for keyword in bullet_keywords)
    should_use_numbers = any(keyword in query_lower for keyword in numbered_keywords)
    
    # Check if the answer already has bullet points or is very short
    if '•' in answer or '-' in answer or answer.count('\n') > 3 or len(answer) < 200:
        return answer
    
    if should_use_bullets:
        # Try to identify natural break points in the text
        sentences = answer.split('. ')
        if len(sentences) > 2:
            # Format as bullet points or numbered list
            formatted_answer = "Based on the WorkSafe guidance:\n\n"
            
            if should_use_numbers:
                # Use numbered list for procedures/steps
                for i, sentence in enumerate(sentences):
                    if sentence.strip():
                        clean_sentence = sentence.strip()
                        if not clean_sentence.endswith('.'):
                            clean_sentence += '.'
                        formatted_answer += f"{i+1}. {clean_sentence}\n"
            else:
                # Use bullet points for general lists
                for i, sentence in enumerate(sentences):
                    if sentence.strip():
                        clean_sentence = sentence.strip()
                        if not clean_sentence.endswith('.'):
                            clean_sentence += '.'
                        formatted_answer += f"• {clean_sentence}\n"
            
            return formatted_answer
    
    return answer

def get_answer(query: str):
    try:
        qa_chain = _get_qa_chain()
        
        # Get relevant documents for context
        retriever = _get_retriever(k=5)
        docs = retriever.get_relevant_documents(query)
        context = "\n".join([doc.page_content for doc in docs])
        
        # Use the simple LLM chain
        result = qa_chain.invoke({"context": context, "question": query})
        answer = result["text"]
        src_docs = docs
        
        # Format the response with bullet points when appropriate
        answer = _format_response_with_bullets(answer, query)
        
    except Exception as e:
        # If the main chain fails, use fallback
        print(f"Main QA chain failed: {e}")
        answer = "I'm having trouble accessing the WorkSafe documents right now. Let me provide general guidance based on my training."
        sources = []
        pages = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return answer, sources, pages, timestamp
    
    # Use the docs we already retrieved from the retriever
    # (LLMChain doesn't return source_documents like RetrievalQA does)
    src_docs = docs

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
        # Use the same properly configured LLM for fallback
        llm = ChatOpenAI(
            temperature=0,
            openai_api_key=OPENAI_API_KEY,
            max_tokens=1000
        )
        answer = llm.invoke(query).content
        # Format fallback responses too
        answer = _format_response_with_bullets(answer, query)
        sources = []
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
        # Ultimate fallback if everything fails
        print(f"All QA methods failed: {e}")
        fallback_answer = "I apologize, but I'm experiencing technical difficulties. Please try again later or contact support if the issue persists."
        return fallback_answer, "Unknown", "N/A", "N/A", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
