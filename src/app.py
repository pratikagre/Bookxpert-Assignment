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

    /* Main App Gradient Background */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #090514 0%, #0c0d21 45%, #050716 100%) !important;
        background-attachment: fixed !important;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: rgba(10, 11, 22, 0.75) !important;
        backdrop-filter: blur(15px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }

    /* Text Input Customization */
    div[data-testid="stTextInput"] input {
        background-color: rgba(22, 24, 47, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        color: #f1f5f9 !important;
        border-radius: 12px !important;
        backdrop-filter: blur(10px) !important;
        padding: 0.6rem 1rem !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #c084fc !important;
        box-shadow: 0 0 15px rgba(192, 132, 252, 0.3) !important;
        background-color: rgba(22, 24, 47, 0.8) !important;
    }

    /* Button Styling */
    div.stButton > button {
        background: linear-gradient(135deg, #c084fc 0%, #60a5fa 100%) !important;
        color: #0c0d21 !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 15px rgba(192, 132, 252, 0.2) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(192, 132, 252, 0.45) !important;
        color: #ffffff !important;
    }
    div.stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Header Gradient */
    .header-container {
        text-align: center;
        padding: 2.5rem 0 1.5rem 0;
    }
    .main-header {
        background: linear-gradient(135deg, #d8b4fe 0%, #818cf8 50%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: -0.03em;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.15rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Glassmorphic Cards */
    .glass-card {
        background: rgba(22, 24, 47, 0.45) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1.5rem !important;
        backdrop-filter: blur(16px) !important;
        box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.3) !important;
        color: #e2e8f0 !important;
        line-height: 1.7 !important;
    }
    
    .source-card {
        background: rgba(12, 13, 27, 0.35);
        border-left: 4px solid #c084fc;
        border-top: 1px solid rgba(255, 255, 255, 0.03);
        border-right: 1px solid rgba(255, 255, 255, 0.03);
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 0 12px 12px 0;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(8px);
    }
    
    .source-card:hover {
        border-left-color: #60a5fa;
        transform: translateX(4px);
        background: rgba(12, 13, 27, 0.55);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
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
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    
    .badge-similarity {
        background-color: rgba(96, 165, 250, 0.12);
        color: #60a5fa;
        border: 1px solid rgba(96, 165, 250, 0.25);
    }
    
    .badge-source {
        background-color: rgba(192, 132, 252, 0.12);
        color: #c084fc;
        border: 1px solid rgba(192, 132, 252, 0.25);
    }
    
    .badge-location {
        background-color: rgba(52, 211, 153, 0.12);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.25);
    }
    
    /* Sidebar Details */
    .sidebar-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: #f1f5f9;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 0.5rem;
    }
    
    .file-item {
        font-size: 0.85rem;
        color: #94a3b8;
        padding: 0.3rem 0;
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
    <div class="main-header">Document Q&A Bot</div>
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
