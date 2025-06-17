import json
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import os

DB_DIR = 'vector_db/'

def search_similar(query, similarity_threshold=0.4, top_k=15):
    """Search for similar documents with similarity threshold filtering"""
    # Load latest paths
    with open('vector_db/latest_paths.json', 'r') as f:
        paths = json.load(f)
        index_path = paths['index_path']
        docs_path = paths['documents_path']
    
    # Load embedding model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Load index and documents
    index = faiss.read_index(index_path)
    with open(docs_path, 'rb') as f:
        documents = pickle.load(f)
    
    # Create query embedding
    query_embedding = model.encode([query])
    query_embedding = query_embedding.astype('float32')
    faiss.normalize_L2(query_embedding)
    
    # Search with higher top_k to get more candidates for filtering
    scores, indices = index.search(query_embedding, top_k)
    
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(documents) and score >= similarity_threshold:
            result = documents[idx].copy()
            result['similarity_score'] = float(score)
            results.append(result)
    
    # Sort by similarity score (descending)
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    
    print(f"Found {len(results)} results above similarity threshold of {similarity_threshold}")
    return results

def search_tickets(query, similarity_threshold=0.4):
    """Search for tickets related to a query with similarity threshold"""
    try:
        results = search_similar(query, similarity_threshold=similarity_threshold)
        
        if not results:
            print(f"No tickets found with similarity above {similarity_threshold}")
            return []
        
        print(f"Query: '{query}'")
        print(f"Found {len(results)} related tickets/pages (similarity ≥ {similarity_threshold}):")
        print("="*70)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. [{result['source'].upper()}] {result['title']}")
            print(f"   Similarity Score: {result['similarity_score']:.3f}")
            print(f"   URL: {result['url']}")
            
            if result['source'] == 'jira':
                metadata = result['metadata']
                print(f"   Status: {metadata['status']} | Priority: {metadata['priority']}")
                print(f"   Type: {metadata['issue_type']} | Assignee: {metadata['assignee']}")
            else:
                metadata = result['metadata']
                print(f"   Space: {metadata['space_name']}")
            
            # Show more text since we're not chunking
            preview_text = result['text'][:400] + "..." if len(result['text']) > 400 else result['text']
            print(f"   Content: {preview_text}")
            print("-" * 70)
        
        return results
            
    except Exception as e:
        print(f"Error searching: {e}")
        print("Make sure you have run vector_db_builder.py first to create the vector database.")
        return []

def search_with_fixed_threshold(query):
    """Search with fixed threshold of 0.4"""
    return search_tickets(query, similarity_threshold=0.4)

def search_documents(query, top_k=5):
    """Search for similar documents"""
    try:
        # Load vector database
        index, documents = load_vector_db()
        
        # Create query embedding
        query_embedding = model.encode([query])
        query_embedding = query_embedding.astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = index.search(query_embedding, top_k)
        
        # Format results with enhanced context
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx < len(documents):
                doc = documents[idx]
                
                # Create enhanced result with more context
                result = {
                    'rank': i + 1,
                    'similarity_score': float(score),
                    'source': doc.get('source', 'unknown'),
                    'source_id': doc.get('source_id', ''),
                    'title': doc.get('title', 'Untitled'),
                    'url': doc.get('url', ''),
                    'text_preview': doc.get('text', '')[:500] + '...' if len(doc.get('text', '')) > 500 else doc.get('text', ''),
                    'full_text': doc.get('text', ''),
                    'metadata': doc.get('metadata', {})
                }
                
                # Add source-specific context
                if doc.get('source') == 'text_file':
                    # Enhanced context for text files
                    filename = doc.get('metadata', {}).get('filename', 'unknown')
                    file_type = doc.get('metadata', {}).get('file_type', 'text')
                    
                    # Try to determine what type of content this is
                    text_content = doc.get('text', '').lower()
                    content_type = "document"
                    
                    if 'image' in text_content and 'analysis' in text_content:
                        content_type = "image analysis"
                    elif 'table' in filename.lower() or 'tables' in filename.lower():
                        content_type = "table data"
                    elif 'context' in filename.lower():
                        content_type = "contextual information"
                    elif any(word in text_content for word in ['pdf', 'document', 'report']):
                        content_type = "document extract"
                    
                    result['content_description'] = f"This is a {content_type} from file '{filename}'"
                    result['enhanced_context'] = f"Source: {content_type.title()} | File: {filename} | Type: {file_type}"
                
                elif doc.get('source') == 'jira':
                    # Enhanced context for JIRA tickets
                    metadata = doc.get('metadata', {})
                    status = metadata.get('status', 'Unknown')
                    priority = metadata.get('priority', 'Unknown')
                    issue_type = metadata.get('issue_type', 'Unknown')
                    
                    result['content_description'] = f"JIRA {issue_type} ticket: {doc.get('title', 'Untitled')}"
                    result['enhanced_context'] = f"Source: JIRA Ticket | Status: {status} | Priority: {priority} | Type: {issue_type}"
                
                elif doc.get('source') == 'confluence':
                    # Enhanced context for Confluence pages
                    metadata = doc.get('metadata', {})
                    space_name = metadata.get('space_name', 'Unknown Space')
                    
                    result['content_description'] = f"Confluence page from '{space_name}' space"
                    result['enhanced_context'] = f"Source: Confluence Page | Space: {space_name}"
                
                else:
                    # Generic context for other sources
                    result['content_description'] = f"Content from {doc.get('source', 'unknown')} source"
                    result['enhanced_context'] = f"Source: {doc.get('source', 'Unknown').title()}"
                
                results.append(result)
        
        return results
        
    except Exception as e:
        print(f"Error searching: {e}")
        return []

def format_search_results(results):
    """Format search results for display with enhanced information"""
    if not results:
        return "No results found."
    
    formatted = []
    for result in results:
        # Header with enhanced context
        header = f"{result['rank']}. [{result['source'].upper()}] {result['title']}"
        similarity = f"   Similarity Score: {result['similarity_score']:.3f}"
        context = f"   Context: {result.get('enhanced_context', 'No additional context')}"
        description = f"   Description: {result.get('content_description', 'No description')}"
        url = f"   URL: {result['url']}" if result['url'] else "   URL: Not available"
        
        # Text preview
        preview = f"   Preview: {result['text_preview']}"
        
        formatted.append(f"{header}\n{similarity}\n{context}\n{description}\n{url}\n{preview}\n")
    
    return "\n".join(formatted)

def get_context_for_llm(results, top_n=3):
    """Get formatted context for LLM with enhanced information"""
    if not results:
        return "No relevant information found."
    
    context_parts = []
    for i, result in enumerate(results[:top_n]):
        # Create rich context for the LLM
        context_part = f"""
DOCUMENT {i+1}:
Source: {result.get('enhanced_context', 'Unknown')}
Title: {result['title']}
Relevance Score: {result['similarity_score']:.3f}
Description: {result.get('content_description', 'No description available')}

Content:
{result['full_text']}

---
"""
        context_parts.append(context_part)
    
    return "\n".join(context_parts)

def load_vector_db():
    """Load the vector database (index and documents)"""
    try:
        # Load latest paths
        with open('vector_db/latest_paths.json', 'r') as f:
            paths = json.load(f)
            index_path = paths['index_path']
            docs_path = paths['documents_path']
        
        # Load index
        index = faiss.read_index(index_path)
        
        # Load documents
        with open(docs_path, 'rb') as f:
            documents = pickle.load(f)
        
        return index, documents
    
    except Exception as e:
        print(f"Error loading vector database: {e}")
        return None, None

def main():
    # Check if vector database exists
    if not os.path.exists(DB_DIR):
        print("Vector database not found. Please run vector_db_builder.py first.")
        return
    
    print("JIRA/Confluence RAG Search System")
    print("Type 'quit' to exit\n")
    
    while True:
        query = input("Enter your search query: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        print(f"\nSearching for: '{query}'")
        print("-" * 50)
        
        # Search documents
        results = search_documents(query)
        
        if results:
            # Display formatted results
            formatted_results = format_search_results(results)
            print(formatted_results)
            
            # Show context for LLM
            print("\n" + "="*50)
            print("CONTEXT FOR LLM:")
            print("="*50)
            llm_context = get_context_for_llm(results)
            print(llm_context)
        else:
            print("No results found. Make sure you have run vector_db_builder.py first to create the vector database.")
        
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    model = SentenceTransformer('all-MiniLM-L6-v2')
    main()

