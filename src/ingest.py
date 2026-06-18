import os
import re
import chromadb
from chromadb.utils.embedding_functions import GoogleGenerativeAiEmbeddingFunction
from pypdf import PdfReader
from dotenv import load_dotenv
from tqdm import tqdm

# Import configuration
from src.config import DATA_DIR, DB_DIR, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

def clean_text(text: str) -> str:
    """
    Cleans raw text by stripping multiple consecutive spaces, tabs,
    and trailing/leading spaces while retaining single newlines.
    """
    if not text:
        return ""
    # Replace multiple spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Replace multiple newlines with a double newline (for paragraph separation)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    return text.strip()

def extract_pdf_pages(file_path: str) -> list[dict]:
    """
    Extracts text page-by-page from a PDF, tracking page numbers.
    """
    extracted_pages = []
    file_name = os.path.basename(file_path)
    
    try:
        reader = PdfReader(file_path)
        for index, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                cleaned = clean_text(text)
                if cleaned:
                    extracted_pages.append({
                        "text": cleaned,
                        "metadata": {
                            "source": file_name,
                            "page": index + 1,
                            "section": f"Page {index + 1}"
                        }
                    })
    except Exception as e:
        print(f"Error reading PDF {file_name}: {e}")
        
    return extracted_pages

def extract_docx_sections(file_path: str) -> list[dict]:
    """
    Extracts text from a Word document, utilizing Headings to separate sections
    and grouping body paragraphs into page-like chunks.
    """
    extracted_sections = []
    file_name = os.path.basename(file_path)
    
    try:
        import docx
        doc = docx.Document(file_path)
        
        current_section = "Introduction"
        current_paragraphs = []
        char_count = 0
        pseudo_page = 1
        
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            
            # Check if this paragraph is a heading
            if p.style.name.startswith("Heading"):
                # If we have accumulated text, save it
                if current_paragraphs:
                    section_text = "\n".join(current_paragraphs)
                    cleaned = clean_text(section_text)
                    if cleaned:
                        extracted_sections.append({
                            "text": cleaned,
                            "metadata": {
                                "source": file_name,
                                "page": pseudo_page,
                                "section": current_section
                            }
                        })
                        pseudo_page += 1
                
                # Start new section
                current_section = text
                current_paragraphs = [text]
                char_count = len(text)
            else:
                current_paragraphs.append(text)
                char_count += len(text)
                
                # If the page-like block gets too large, split it
                if char_count > 1500:
                    section_text = "\n".join(current_paragraphs)
                    cleaned = clean_text(section_text)
                    if cleaned:
                        extracted_sections.append({
                            "text": cleaned,
                            "metadata": {
                                "source": file_name,
                                "page": pseudo_page,
                                "section": current_section
                            }
                        })
                        pseudo_page += 1
                    current_paragraphs = []
                    char_count = 0
        
        # Save remaining paragraphs
        if current_paragraphs:
            section_text = "\n".join(current_paragraphs)
            cleaned = clean_text(section_text)
            if cleaned:
                extracted_sections.append({
                    "text": cleaned,
                    "metadata": {
                        "source": file_name,
                        "page": pseudo_page,
                        "section": current_section
                    }
                })
                
    except Exception as e:
        print(f"Error reading DOCX {file_name}: {e}")
        
    return extracted_sections

def extract_txt_file(file_path: str) -> list[dict]:
    """
    Reads plain text files. Uses Markdown headers (e.g. ## Section) to identify sections.
    """
    extracted_data = []
    file_name = os.path.basename(file_path)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        cleaned_content = clean_text(content)
        if not cleaned_content:
            return []
            
        # Try to split by Markdown headings
        sections = re.split(r'(^#+\s+.*)', cleaned_content, flags=re.MULTILINE)
        
        if len(sections) <= 1:
            # No headings found, treat as one single block
            extracted_data.append({
                "text": cleaned_content,
                "metadata": {
                    "source": file_name,
                    "page": 1,
                    "section": "Main Content"
                }
            })
        else:
            current_section = "Introduction"
            pseudo_page = 1
            i = 0
            
            # The split list alternates: text-before-heading (could be empty), heading, text-after-heading...
            while i < len(sections):
                part = sections[i].strip()
                if not part:
                    i += 1
                    continue
                
                # Check if it's a heading line
                if part.startswith("#"):
                    # Clean up the heading to use as section title
                    current_section = part.lstrip("#").strip()
                    # The next part will be the body text of this section
                    body_text = ""
                    if i + 1 < len(sections):
                        body_text = sections[i + 1].strip()
                        i += 1
                    
                    full_section_text = f"{part}\n\n{body_text}" if body_text else part
                    cleaned = clean_text(full_section_text)
                    if cleaned:
                        extracted_data.append({
                            "text": cleaned,
                            "metadata": {
                                "source": file_name,
                                "page": pseudo_page,
                                "section": current_section
                            }
                        })
                        pseudo_page += 1
                else:
                    # Text before the first heading
                    cleaned = clean_text(part)
                    if cleaned:
                        extracted_data.append({
                            "text": cleaned,
                            "metadata": {
                                "source": file_name,
                                "page": pseudo_page,
                                "section": current_section
                            }
                        })
                        pseudo_page += 1
                i += 1
                
    except Exception as e:
        print(f"Error reading TXT {file_name}: {e}")
        
    return extracted_data

def split_text_recursive(text: str, max_chars: int = 1000, overlap: int = 200) -> list[str]:
    """
    Splits text recursively using paragraphs, sentences, words, and characters to keep
    logical structures intact. Integrates sliding window overlap.
    """
    separators = ["\n\n", "\n", ". ", " ", ""]
    
    def _split(text_to_split, separators_list):
        if len(text_to_split) <= max_chars:
            return [text_to_split]
        if not separators_list:
            # Base case: split characters by sliding window
            chunks = []
            start = 0
            while start < len(text_to_split):
                end = min(start + max_chars, len(text_to_split))
                chunks.append(text_to_split[start:end])
                start += (max_chars - overlap)
            return chunks
            
        sep = separators_list[0]
        next_seps = separators_list[1:]
        
        # Split text by separator
        if sep == "":
            parts = list(text_to_split)
        else:
            parts = text_to_split.split(sep)
            
        chunks = []
        current_chunk = []
        current_len = 0
        
        for part in parts:
            part_with_sep = part if len(current_chunk) == 0 or sep == "" else sep + part
            
            if len(part_with_sep) > max_chars:
                # Flush current chunk
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                
                # Recursively split the oversized part
                sub_chunks = _split(part, next_seps)
                chunks.extend(sub_chunks)
            elif current_len + len(part_with_sep) <= max_chars:
                current_chunk.append(part_with_sep)
                current_len += len(part_with_sep)
            else:
                # Flush and start new chunk with overlap
                prev_text = "".join(current_chunk)
                chunks.append(prev_text)
                
                # Prepend the overlapping characters from previous chunk
                overlap_text = prev_text[-overlap:] if len(prev_text) > overlap else prev_text
                current_chunk = [overlap_text + part_with_sep]
                current_len = len(current_chunk[0])
                
        if current_chunk:
            chunks.append("".join(current_chunk))
            
        return chunks
        
    return _split(text, separators)

def chunk_extracted_documents(docs: list[dict], chunk_size: int = 1000, chunk_overlap: int = 200) -> list[dict]:
    """
    Takes list of documents (with text and metadata) and splits them into smaller,
    overlapping chunks, propagating the source, page, and section metadata.
    """
    all_chunks = []
    
    for doc in docs:
        text = doc["text"]
        metadata = doc["metadata"]
        
        # Split text into overlapping segments
        text_chunks = split_text_recursive(text, max_chars=chunk_size, overlap=chunk_overlap)
        
        for idx, chunk_text in enumerate(text_chunks):
            # Clean up double overlaps if any edge case introduced double spaces
            chunk_text = clean_text(chunk_text)
            if not chunk_text:
                continue
                
            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": metadata["source"],
                    "page": metadata["page"],
                    "section": metadata["section"],
                    "chunk_index": idx
                }
            })
            
    return all_chunks

def load_documents_from_folder(folder_path: str) -> list[dict]:
    """
    Scans the folder, reads all PDF, DOCX, and TXT files, and returns page-level/section-level docs.
    """
    all_documents = []
    
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} does not exist.")
        return []
        
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    print(f"Found {len(files)} files in {folder_path}")
    
    for file in files:
        file_path = os.path.join(folder_path, file)
        ext = os.path.splitext(file).lower()[1]
        
        if ext == 'pdf':
            print(f"Parsing PDF: {file}")
            all_documents.extend(extract_pdf_pages(file_path))
        elif ext == 'docx':
            print(f"Parsing DOCX: {file}")
            all_documents.extend(extract_docx_sections(file_path))
        elif ext in ['txt', 'md']:
            print(f"Parsing Text: {file}")
            all_documents.extend(extract_txt_file(file_path))
        else:
            print(f"Skipping unsupported file type: {file}")
            
    return all_documents

def run_ingestion():
    """
    Executes the full ingestion pipeline: extracts, chunks, embeds, and saves to ChromaDB.
    """
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please add it to your .env file.")
        
    print("Step 1: Extracting raw text from documents...")
    raw_docs = load_documents_from_folder(DATA_DIR)
    
    if not raw_docs:
        print("No documents found to index. Make sure you have placed files in the data/ directory.")
        return
        
    print(f"Extracted {len(raw_docs)} pages/sections in total.")
    
    print("Step 2: Splitting text into semantic overlapping chunks...")
    chunks = chunk_extracted_documents(raw_docs, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    print(f"Created {len(chunks)} chunks.")
    
    print("Step 3: Initializing persistent ChromaDB...")
    client = chromadb.PersistentClient(path=DB_DIR)
    
    embedding_fn = GoogleGenerativeAiEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL
    )
    
    # Delete collection if it already exists to avoid duplicate entries when indexing again
    try:
        client.delete_collection("document_knowledge_base")
        print("Cleared existing vector database collection.")
    except Exception:
        # Collection didn't exist, ignore
        pass
        
    collection = client.create_collection(
        name="document_knowledge_base",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"} # Use Cosine Distance for similarity search
    )
    
    print("Step 4: Embedding and indexing chunks in ChromaDB...")
    # ChromaDB supports batching. We will upload chunks.
    # Note: ChromaDB's embedding function handles batching of text-embedding-004.
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    
    # Batch adding with a progress bar using tqdm
    batch_size = 100
    for i in tqdm(range(0, len(chunks), batch_size), desc="Indexing Batches"):
        end_idx = min(i + batch_size, len(chunks))
        collection.add(
            ids=ids[i:end_idx],
            documents=documents[i:end_idx],
            metadatas=metadatas[i:end_idx]
        )
        
    print(f"Successfully indexed {len(chunks)} chunks in the vector database.")

if __name__ == "__main__":
    run_ingestion()
