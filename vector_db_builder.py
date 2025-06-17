import json
import pandas as pd
import numpy as np
import faiss
import pickle
import os
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import re
from datetime import datetime
from pathlib import Path

class VectorDBBuilder:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """
        Initialize with sentence transformer model
        all-MiniLM-L6-v2 is lightweight and good for semantic search
        """
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
    def clean_text(self, text):
        """Clean and preprocess text"""
        if not text or pd.isna(text):
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', str(text))
        # Remove special characters and normalize whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def process_text_files(self, data_dir):
        """Process all text files in data directory"""
        print("Processing text files...")
        documents = []
        
        text_files = list(Path(data_dir).glob('*.txt'))
        
        for file_path in text_files:
            print(f"Processing: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                cleaned_text = self.clean_text(content)
                
                if cleaned_text.strip():
                    doc = {
                        'text': cleaned_text,
                        'source': 'text_file',
                        'source_id': file_path.stem,
                        'title': file_path.stem,
                        'url': '',
                        'metadata': {
                            'filename': file_path.name,
                            'file_type': 'text'
                        }
                    }
                    documents.append(doc)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        print(f"Created {len(documents)} text file documents")
        return documents
    
    def process_jira_data(self, file_path):
        """Process JIRA tickets from CSV"""
        print(f"Processing JIRA data from: {file_path}")
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            data = df.to_dict('records')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []
        
        documents = []
        
        for ticket in data:
            # Combine relevant fields for embedding
            title = ticket.get('summary', '')
            description = ticket.get('description', '')
            status = ticket.get('status', '')
            priority = ticket.get('priority', '')
            issue_type = ticket.get('issue_type', '')
            
            # Create full text - more structured for better embedding
            full_text = f"{title}\n\n{description}\n\nStatus: {status}\nPriority: {priority}\nType: {issue_type}"
            cleaned_text = self.clean_text(full_text)
            
            if cleaned_text.strip():  # Only add non-empty documents
                doc = {
                    'text': cleaned_text,
                    'source': 'jira',
                    'source_id': ticket.get('key', ticket.get('id', '')),
                    'title': title,
                    'url': ticket.get('url', ''),
                    'metadata': {
                        'status': status,
                        'priority': priority,
                        'issue_type': issue_type,
                        'assignee': ticket.get('assignee', ''),
                        'reporter': ticket.get('reporter', ''),
                        'created': ticket.get('created', ''),
                        'updated': ticket.get('updated', ''),
                        'labels': ticket.get('labels', []),
                        'components': ticket.get('components', [])
                    }
                }
                documents.append(doc)
        
        print(f"Created {len(documents)} JIRA documents")
        return documents
    
    def process_confluence_data(self, file_path):
        """Process Confluence pages from CSV"""
        print(f"Processing Confluence data from: {file_path}")
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            data = df.to_dict('records')
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []
        
        documents = []
        
        for page in data:
            title = page.get('title', '')
            content = page.get('content', '')
            space_name = page.get('space_name', '')
            
            # Create full text
            full_text = f"{title}\n\nSpace: {space_name}\n\n{content}"
            cleaned_text = self.clean_text(full_text)
            
            if cleaned_text.strip():  # Only add non-empty documents
                doc = {
                    'text': cleaned_text,
                    'source': 'confluence',
                    'source_id': page.get('id', ''),
                    'title': title,
                    'url': page.get('url', ''),
                    'metadata': {
                        'space_key': page.get('space_key', ''),
                        'space_name': space_name,
                        'version': page.get('version', ''),
                        'created': page.get('created', '')
                    }
                }
                documents.append(doc)
        
        print(f"Created {len(documents)} Confluence documents")
        return documents
    
    def process_all_data_files(self, data_dir):
        """Process all files in the data directory"""
        print(f"Processing all files in {data_dir}...")
        all_documents = []
        
        data_path = Path(data_dir)
        if not data_path.exists():
            print(f"Data directory {data_dir} not found!")
            return []
        
        # Process text files (including image contexts, PDF extracts, etc.)
        text_docs = self.process_text_files(data_dir)
        all_documents.extend(text_docs)
        
        # Process CSV files
        csv_files = list(data_path.glob('*.csv'))
        
        for csv_file in csv_files:
            filename = csv_file.name.lower()
            
            if 'jira' in filename:
                jira_docs = self.process_jira_data(csv_file)
                all_documents.extend(jira_docs)
            elif 'confluence' in filename:
                confluence_docs = self.process_confluence_data(csv_file)
                all_documents.extend(confluence_docs)
            else:
                # Generic CSV processing
                print(f"Processing generic CSV: {csv_file}")
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8')
                    for _, row in df.iterrows():
                        # Try to find text content in the row
                        text_content = ""
                        for col in df.columns:
                            if row[col] and pd.notna(row[col]):
                                text_content += f"{col}: {row[col]}\n"
                        
                        cleaned_text = self.clean_text(text_content)
                        if cleaned_text.strip():
                            doc = {
                                'text': cleaned_text,
                                'source': 'csv_file',
                                'source_id': f"{csv_file.stem}_{len(all_documents)}",
                                'title': csv_file.stem,
                                'url': '',
                                'metadata': {
                                    'filename': csv_file.name,
                                    'file_type': 'csv'
                                }
                            }
                            all_documents.append(doc)
                except Exception as e:
                    print(f"Error processing {csv_file}: {e}")
        
        print(f"Total documents processed: {len(all_documents)}")
        return all_documents
    
    def create_vector_db(self, documents):
        """Create FAISS vector database"""
        print("Creating embeddings...")
        
        # Extract texts for embedding
        texts = [doc['text'] for doc in documents]
        
        # Create embeddings in batches to manage memory
        batch_size = 32
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, show_progress_bar=True)
            embeddings.extend(batch_embeddings)
        
        embeddings = np.array(embeddings).astype('float32')
        
        # Create FAISS index
        print("Building FAISS index...")
        index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        return index, embeddings
    
    def save_vector_db(self, index, documents, output_dir='vector_db'):
        """Save FAISS index and documents with fixed names"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Fixed filenames
        index_path = os.path.join(output_dir, 'faiss_index.bin')
        docs_path = os.path.join(output_dir, 'documents.pkl')
        
        # Remove existing files if they exist
        if os.path.exists(index_path):
            os.remove(index_path)
            print(f"Replaced existing {index_path}")
        
        if os.path.exists(docs_path):
            os.remove(docs_path)
            print(f"Replaced existing {docs_path}")
        
        # Save FAISS index
        faiss.write_index(index, index_path)
        
        # Save documents with metadata
        with open(docs_path, 'wb') as f:
            pickle.dump(documents, f)
        
        # Save latest paths for easy access
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        latest_paths_file = os.path.join(output_dir, 'latest_paths.json')
        with open(latest_paths_file, 'w') as f:
            json.dump({
                'index_path': index_path,
                'documents_path': docs_path,
                'timestamp': timestamp,
                'total_documents': len(documents)
            }, f, indent=2)
        
        print(f"Vector DB saved:")
        print(f"  Index: {index_path}")
        print(f"  Documents: {docs_path}")
        print(f"  Latest paths: {latest_paths_file}")
        print(f"  Total documents: {len(documents)}")
        
        return index_path, docs_path

def main():
    # Configuration
    DATA_DIR = 'data'
    
    if not os.path.exists(DATA_DIR):
        print(f"Data directory {DATA_DIR} not found. Please run data extraction scripts first.")
        return
    
    # Build vector database
    builder = VectorDBBuilder()
    
    # Process all data files
    all_documents = builder.process_all_data_files(DATA_DIR)
    
    if not all_documents:
        print("No documents found to process!")
        return
    
    print(f"Total documents to vectorize: {len(all_documents)}")
    
    # Create vector database
    index, embeddings = builder.create_vector_db(all_documents)
    
    # Save vector database
    index_path, docs_path = builder.save_vector_db(index, all_documents)
    
    print("\nVector database creation completed!")
    print(f"You can now use search_rag.py to query the database.")

if __name__ == "__main__":
    main()

