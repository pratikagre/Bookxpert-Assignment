import os
import google.generativeai as genai
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from dotenv import load_dotenv

from src.config import DB_DIR, EMBEDDING_MODEL, GENERATIVE_MODEL

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004", task_type: str = "retrieval_query"):
        self.model_name = model_name
        self.task_type = task_type
        genai.configure(api_key=api_key)
        
    def __call__(self, input: Documents) -> Embeddings:
        try:
            response = genai.embed_content(
                model=self.model_name,
                content=input,
                task_type=self.task_type
            )
            return response['embedding']
        except Exception as e:
            print(f"Error in GeminiEmbeddingFunction: {e}")
            raise e

def query_rag_pipeline(user_query: str, k: int = 4) -> dict:
    """
    Retrieves relevant document chunks from ChromaDB, constructs a grounded prompt,
    sends it to Google Gemini, and returns the generated answer alongside citations.
    """
    if not api_key:
        return {
            "answer": "Error: GEMINI_API_KEY environment variable is not set. Please add it to your .env file.",
            "citations": [],
            "raw_context": []
        }

    client = chromadb.PersistentClient(path=DB_DIR)
    
    embedding_fn = GeminiEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL,
        task_type="retrieval_query"
    )
    
    try:
        collection = client.get_collection(
            name="document_knowledge_base",
            embedding_function=embedding_fn
        )
    except Exception as e:
        return {
            "answer": f"Error: The vector database could not be loaded. Details: {e}",
            "citations": [],
            "raw_context": []
        }
        
    try:
        results = collection.query(
            query_texts=[user_query],
            n_results=k
        )
    except Exception as e:
        return {
            "answer": f"Error querying vector database: {e}",
            "citations": [],
            "raw_context": []
        }
        
    if not results or not results['documents'] or not results['documents'][0]:
        return {
            "answer": "I am sorry, but the database does not contain any matching chunks.",
            "citations": [],
            "raw_context": []
        }
        
    context_blocks = []
    citations_list = []
    raw_context = []
    
    for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
        source = meta['source']
        page = meta['page']
        section = meta['section']
        
        citation_str = f"Source: {source}, Page: {page}, Section: {section}"
        context_blocks.append(f"[{citation_str}]\nContext:\n{doc}")
        
        similarity = max(0.0, min(1.0, 1.0 - dist))
        raw_context.append({
            "text": doc,
            "source": source,
            "page": page,
            "section": section,
            "similarity": similarity
        })
        citations_list.append(citation_str)
        
    context_payload = "\n\n---\n\n".join(context_blocks)
    
    system_prompt = (
        "You are an expert, precise document Q&A assistant. Your job is to answer the user's question "
        "using ONLY the provided document context below. Follow these instructions strictly:\n"
        "1. Answer the question based ONLY on the provided context. Do NOT use external knowledge, training data facts, or assume anything not written in the context.\n"
        "2. You MUST cite your sources inline next to the facts you mention. Use the format '(Source: filename, Page: page_num)' or '(Source: filename, Section: section_name)' based on the source blocks.\n"
        "3. Every factual claim you make must be accompanied by an inline citation to the block it came from.\n"
        "4. If the answer cannot be found in the provided context, you must state exactly: "
        "'I am sorry, but the provided documents do not contain the answer to your question.' "
        "Do not write anything else or try to answer using external information.\n"
        "5. Keep the answer professional, concise, and structured."
    )
    
    prompt = (
        f"{system_prompt}\n\n"
        f"CONTEXT INFORMATION:\n"
        f"{context_payload}\n\n"
        f"USER QUESTION: {user_query}\n\n"
        f"GROUNDED ANSWER:"
    )
    
    try:
        model = genai.GenerativeModel(GENERATIVE_MODEL)
        response = model.generate_content(prompt)
        answer = response.text
    except Exception as e:
        answer = f"Error generating answer from Gemini: {e}"
        
    return {
        "answer": answer,
        "citations": list(set(citations_list)), # Keep unique list of citations
        "raw_context": raw_context
    }
