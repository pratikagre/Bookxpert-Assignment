import os
import sys
import streamlit as st
from dotenv import load_dotenv

# Add the root directory to path to enable running this script directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.query import query_rag_pipeline
from src.ingest import run_ingestion
from src.config import DATA_DIR, DB_DIR

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# App title and configuration
st.set_page_config(
    page_title="RAG Doc Q&A Bot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    
    /* Global Styling */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* Header Gradient */
    .header-container {
        text-align: center;
        padding: 2rem 0;
    }
    .main-header {
        background: linear-gradient(135deg, #c084fc 0%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Glassmorphic Cards */
    .glass-card {
        background: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    
    .source-card {
        background: rgba(15, 23, 42, 0.35);
        border-left: 4px solid #c084fc;
        border-top: 1px solid rgba(255, 255, 255, 0.03);
        border-right: 1px solid rgba(255, 255, 255, 0.03);
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 0 12px 12px 0;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .source-card:hover {
        border-left-color: #60a5fa;
        transform: translateX(4px);
        background: rgba(15, 23, 42, 0.5);
    }
    
    /* Badges */
    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 0.8rem;
    }
    
    .custom-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    
    .badge-similarity {
        background-color: rgba(96, 165, 250, 0.12);
        color: #3b82f6;
        border: 1px solid rgba(96, 165, 250, 0.25);
    }
    
    .badge-source {
        background-color: rgba(192, 132, 252, 0.12);
        color: #a855f7;
        border: 1px solid rgba(192, 132, 252, 0.25);
    }
    
    .badge-location {
        background-color: rgba(52, 211, 153, 0.12);
        color: #10b981;
        border: 1px solid rgba(52, 211, 153, 0.25);
    }
    
    /* Sidebar Details */
    .sidebar-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: #f1f5f9;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 0.5rem;
    }
    
    .file-item {
        font-size: 0.85rem;
        color: #94a3b8;
        padding: 0.25rem 0;
        display: flex;
        align-items: center;
    }
    .file-item::before {
        content: "📄";
        margin-right: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Main Page Header
st.markdown("""
<div class="header-container">
    <div class="main-header">Talk-a-Tive Document Q&A Bot</div>
    <div class="sub-header">Retrieval-Augmented Generation (RAG) powered by ChromaDB & Google Gemini</div>
</div>
""", unsafe_allow_html=True)

# API Key Check
if not api_key:
    st.error("⚠️ GEMINI_API_KEY is missing! Please configure the GEMINI_API_KEY environment variable or place it in a `.env` file at the root of the project.")
    st.info("Example `.env` file:\n\n`GEMINI_API_KEY=AIzaSyD-your-api-key`")
    st.stop()

# Sidebar: System Operations & Configurations
with st.sidebar:
    st.markdown('<div class="sidebar-title">⚙️ Control Panel</div>', unsafe_allow_html=True)
    
    # K Value Selector
    k_val = st.slider("Context chunks to retrieve (k)", min_value=1, max_value=8, value=4, step=1)
    
    # Ingestion Trigger
    st.markdown('<div class="sidebar-title">📂 Document Database</div>', unsafe_allow_html=True)
    
    if st.button("🚀 Re-index Knowledge Base", use_container_width=True):
        with st.spinner("Processing documents, generating embeddings and updating ChromaDB..."):
            try:
                run_ingestion()
                st.success("Successfully indexed documents!")
            except Exception as e:
                st.error(f"Error during ingestion: {e}")
                
    # List available documents in data/
    st.markdown('<div class="sidebar-title">📁 Indexed Documents</div>', unsafe_allow_html=True)
    if os.path.exists(DATA_DIR):
        files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]
        if files:
            for file in files:
                st.markdown(f'<div class="file-item">{file}</div>', unsafe_allow_html=True)
        else:
            st.info("No documents found in `data/` folder.")
    else:
        st.warning("`data/` folder not found.")
        
    st.markdown("<br><hr><div style='text-align: center; color: #64748b; font-size: 0.75rem;'>Bookxpert Assignment<br>AI Engineering Intern</div>", unsafe_allow_html=True)

# Chat Interface / Inquiries
st.markdown("### 🔍 Ask a Question against your Knowledge Base")

# Question input form
query_input = st.text_input("Enter your question here...", placeholder="e.g., What is quantum superposition and how does it differ from classical bits?", key="query_text")

if query_input:
    with st.spinner("Querying vector database and synthesizing answer..."):
        result = query_rag_pipeline(query_input, k=k_val)
        
    # Render answer
    st.markdown("### 🧠 Grounded Answer")
    st.markdown(f'<div class="glass-card">{result["answer"]}</div>', unsafe_allow_html=True)
    
    # Render Citations and Source Chunks
    raw_context = result.get("raw_context", [])
    if raw_context:
        st.markdown("### 📄 Retrieved Context & Citations")
        for idx, chunk in enumerate(raw_context):
            source = chunk["source"]
            page = chunk["page"]
            section = chunk["section"]
            similarity = chunk["similarity"]
            text = chunk["text"]
            
            # Format custom expander card
            st.markdown(f"""
            <div class="source-card">
                <div class="badge-container">
                    <span class="custom-badge badge-source">📁 {source}</span>
                    <span class="custom-badge badge-location">📍 Page {page} | Section: {section}</span>
                    <span class="custom-badge badge-similarity">⚡ Similarity: {similarity:.2%}</span>
                </div>
                <div style="font-size: 0.92rem; color: #cbd5e1; line-height: 1.6; font-style: italic;">
                    "{text}"
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No relevant context chunks were retrieved from the database.")
