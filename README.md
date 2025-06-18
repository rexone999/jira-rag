# Comprehensive Guide to the JIRA-RAG System

## Overview
The JIRA-RAG system is an advanced solution that integrates data extraction, image analysis, and AI-powered search and Q&A capabilities. It transforms how teams interact with their project data, making information retrieval intuitive and efficient.

## File Structure

```
jira-RAG/
├── credentials.json          # Atlassian credentials
├── API_KEY.txt              # Google Gemini API key
├── atlassian_extractor.py   # Extracts JIRA/Confluence data
├── download_jira_images.py  # Downloads attachments from JIRA
├── image_breaker.py         # Analyzes images using AI
├── pdf_processor.py         # Extracts content from PDFs
├── vector_db_builder.py     # Creates searchable database
├── search_rag.py           # Search interface
├── gemini_test.py          # Q&A interface using Gemini AI
├── data/                   # Extracted data
├── downloads/              # Downloaded attachments
└── vector_db/             # Searchable database
```

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-repo/jira-RAG.git
   cd jira-RAG
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Credentials**
   - Create a `credentials.json` file for Atlassian API credentials.
   - Format:
     ```json
     {
       "email": "your_email",
       "api_token": "your_api_token",
       "domain": "your_domain"
     }
     ```
   - Create an `API_KEY.txt` file for Google Gemini API key.

4. **Data Extraction**
   - Run `atlassian_extractor.py` to extract JIRA and Confluence data.
   - Downloads attachments from JIRA issues.

5. **Process PDF Files**
   - Run `pdf_processor.py` to extract content from PDFs.
   - Extracts text, tables, and images; analyzes images with AI.

6. **Build Vector Database**
   - Run `vector_db_builder.py` to create a searchable vector database.

7. **Search and Q&A**
   - Use `search_rag.py` for keyword-based search.
   - Use `gemini_test.py` for AI-powered Q&A.

## Detailed Usage

### Step 1: Data Extraction
```bash
python atlassian_extractor.py
```

**What this does:**
- Connects to Atlassian API using provided credentials
- Extracts JIRA tickets and Confluence pages
- Saves data as CSV files in the `data/` directory

### Step 2: Download JIRA Images
```bash
python download_jira_images.py
```

**What this does:**
- Downloads images attached to JIRA issues
- Saves images in the `downloads/` directory

### Step 3: Analyze Images
```bash
python image_breaker.py
```

**What this does:**
- Analyzes downloaded images using Google Gemini AI
- Generates detailed context descriptions for each image
- Saves analysis results as text files in the `data/` directory

### Step 4: Process PDF Files
```bash
python pdf_processor.py
```

**What this does:**
- Finds all PDF files in downloads folder
- Extracts text content from PDFs using PyMuPDF (fitz)
- Extracts tables from PDFs automatically
- Extracts images embedded in PDFs
- Uses AI to analyze extracted images
- Saves everything as searchable text files

**Technical Details:**
- **Text Extraction**: Uses PyMuPDF's text extraction capabilities
- **Table Detection**: Automatically finds and extracts table structures
- **Image Processing**: Extracts images as PNG files, then analyzes with Gemini Vision
- **Multi-Modal**: Handles PDFs with mixed content (text, tables, images)

**Output:**
- `data/{filename}_text.txt` - All text content from the PDF
- `data/{filename}_tables.txt` - Structured table data
- `data/{filename}_image_contexts.txt` - AI analysis of images found in PDF
- `downloads/extracted_images/` - Individual image files extracted from PDFs

**Example Use Cases:**
- Technical documentation with diagrams
- Reports with charts and tables
- Manuals with screenshots
- Presentations saved as PDFs

### Step 5: Build Vector Database
```bash
python vector_db_builder.py
```

**What this does:**
- Creates embeddings for all documents using SentenceTransformer
- Builds a FAISS index for efficient similarity search
- Saves the vector database and documents to the `vector_db/` directory

### Step 6: Search Documents
```bash
python search_rag.py
```

**What this does:**
- Loads the vector database
- Allows keyword-based search across all documents
- Displays matching documents with context

### Step 7: Ask Questions with AI (Optional)
```bash
python gemini_test.py
```

**What this does:**
- Provides an intelligent Q&A interface
- Uses the vector database to find relevant information
- Sends context to Google Gemini AI for natural language answers
- Combines retrieval with generation (the "RAG" in action)

**How it works:**
1. You ask a question in natural language
2. System searches vector database for relevant documents
3. Retrieves top matching content with context
4. Sends question + context to Gemini AI
5. Gemini generates a comprehensive answer based on your data

**Example Conversation:**
```
You: How do we handle user authentication in our system?
AI: Based on your JIRA tickets and documentation, your system uses JWT tokens 
    for authentication. I found 3 relevant tickets discussing the implementation:
    
    1. PROJ-123 implemented the initial JWT setup
    2. PROJ-145 added refresh token functionality  
    3. PROJ-167 fixed a security vulnerability
    
    The process involves...
```

**Advanced Features:**
- **Contextual Answers**: AI knows which specific tickets/docs it's referencing
- **Source Attribution**: Shows exactly where information came from
- **Multi-Source Synthesis**: Combines information from multiple documents
- **Conversational**: Can ask follow-up questions

## Understanding the Technology

### PDF Processing (PyMuPDF/Fitz)
- **PyMuPDF**: Python binding for the MuPDF library
- **Multi-Modal Extraction**: Handles text, images, and vector graphics
- **Table Detection**: Uses geometric analysis to identify table structures
- **High Accuracy**: Industry-standard PDF processing
- **Memory Efficient**: Processes large PDFs without loading everything into memory

### AI-Powered Q&A (Gemini)
- **Large Language Model**: Google's latest AI model for text generation
- **Context Window**: Can process thousands of tokens of context
- **Multi-Modal**: Can understand text, images, and combined content
- **Instruction Following**: Follows specific prompts for consistent output format

## Advanced Usage

### PDF Processing Customization
```python
# In pdf_processor.py, you can modify:
- Image extraction quality
- Table detection sensitivity  
- Text cleaning rules
- Output formatting
```

### AI Q&A Customization
```python
# In gemini_test.py, you can modify:
- System prompts for different response styles
- Number of context documents retrieved
- Answer length and format
- Temperature settings for creativity vs accuracy
```

## Example Queries You Can Try

### With search_rag.py (Search Only):
- "What are the current security issues?"
- "How do we deploy to production?"
- "What bugs were reported last month?"
- "Show me documentation about the API"

### With gemini_test.py (AI Q&A):
- "Explain our deployment process step by step"
- "What are the most critical bugs and how should we prioritize them?"
- "Summarize the feedback from our latest user testing"
- "What technical debt do we need to address?"
- "How does our authentication system work?"

## Workflow Comparison

### Traditional Approach:
1. Remember which project had the information
2. Search through multiple JIRA projects
3. Check various Confluence spaces
4. Read through dozens of tickets/pages
5. Try to piece together the full picture
6. **Time: Hours to days**

### RAG System Approach:
1. Ask a natural language question
2. Get relevant information instantly
3. AI provides comprehensive answer with sources
4. **Time: Seconds**

## Advanced Integration Examples

### Slack Bot Integration
```python
# Use the search functions in a Slack bot
from search_rag import search_documents

@slack_app.message("search")
def handle_search(message):
    results = search_documents(message['text'])
    # Format and send results
```

### API Endpoint
```python
# Create a REST API for your team
from flask import Flask, request, jsonify
from gemini_test import ask_question

app = Flask(__name__)

@app.route('/ask', methods=['POST'])
def api_ask():
    question = request.json['question']
    answer = ask_question(question)
    return jsonify({'answer': answer})
```

### Dashboard Integration
- Embed search in internal tools
- Create knowledge base widgets
- Add to project management dashboards

## Benefits for Different Roles

### **Developers:**
- Quickly find code examples and technical decisions
- Understand system architecture from past discussions
- Find solutions to similar problems solved before

### **Product Managers:**
- Get instant summaries of feature requests
- Understand user feedback themes
- Track feature development history

### **QA/Support:**
- Find similar bug reports and their solutions
- Understand known issues and workarounds
- Access comprehensive testing documentation

### **Leadership:**
- Get project status summaries
- Understand team capacity and blockers
- Access historical decision context

## Performance Optimizations

### For Large Datasets:
1. **Chunking**: Break large documents into smaller pieces
2. **Batch Processing**: Process documents in batches to manage memory
3. **Incremental Updates**: Only reprocess changed documents
4. **Caching**: Cache frequently accessed embeddings

### For Better Search Results:
1. **Document Preprocessing**: Clean and structure text before embedding
2. **Metadata Filtering**: Add filters for date, project, type, etc.
3. **Hybrid Search**: Combine semantic search with keyword search
4. **User Feedback**: Track which results users find helpful

This comprehensive system transforms your fragmented project information into an intelligent, searchable knowledge base that can answer complex questions and provide insights you might never have discovered manually.