import os
import sys
from dotenv import load_dotenv

# Add the root directory to path to enable running this script directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.query import query_rag_pipeline

def run_cli_loop():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("\033[91mError: GEMINI_API_KEY is not set in the environment or .env file.\033[0m")
        print("Please create a .env file at the project root containing: GEMINI_API_KEY=your_actual_api_key")
        return

    print("=" * 60)
    print("\033[94m              RAG Document Q&A Bot - CLI Loop\033[0m")
    print("=" * 60)
    print("Type your question and press Enter. Type 'exit' or 'quit' to close.")
    print("=" * 60)

    while True:
        try:
            user_query = input("\n\033[92mQuestion:\033[0m ").strip()
            if not user_query:
                continue
                
            if user_query.lower() in ['exit', 'quit']:
                print("\nGoodbye!")
                break
                
            print("\033[93mSearching database and generating grounded answer...\033[0m")
            
            result = query_rag_pipeline(user_query, k=4)
            
            print("\n\033[96mAnswer:\033[0m")
            print(result["answer"])
            
            # Print citations and context if available
            raw_context = result.get("raw_context", [])
            if raw_context:
                print("\n" + "-" * 40)
                print("\033[95mRetrieved Source Chunks:\033[0m")
                for idx, chunk in enumerate(raw_context):
                    source = chunk["source"]
                    page = chunk["page"]
                    section = chunk["section"]
                    similarity = chunk["similarity"]
                    text = chunk["text"]
                    
                    # Truncate text for CLI print to avoid flooding screen
                    snippet = text[:150].replace('\n', ' ') + "..." if len(text) > 150 else text.replace('\n', ' ')
                    
                    print(f"[{idx+1}] {source} (Page {page}, Section: {section}) | Similarity: {similarity:.2%}")
                    print(f"    Snippet: \"{snippet}\"")
                print("-" * 40)
            else:
                print("\n\033[91mNo relevant context chunks were retrieved.\033[0m")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\033[91mAn error occurred: {e}\033[0m")

if __name__ == "__main__":
    run_cli_loop()
