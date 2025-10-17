from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import chromadb
import uvicorn
import requests
from bs4 import BeautifulSoup
import re
import logging
import openai
import os
import json
from datetime import datetime

app = FastAPI(title="ChatWith Wiki", description="FastAPI with ChromaDB Vector Database")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ChromaDB client (using new client configuration)
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Get or create collection
collection = chroma_client.get_or_create_collection(name="wiki_documents")

# OpenAI client setup
openai_client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
)

# Pydantic models
class Document(BaseModel):
    id: str
    content: str
    metadata: Optional[dict] = None

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5

class QueryResponse(BaseModel):
    documents: List[str]
    metadatas: List[dict]
    distances: List[float]
    ids: List[str]
    summary: Optional[str] = None
    is_relevant: bool = True
    message: Optional[str] = None

# Wikipedia scraping functions
def scrape_wikipedia_page(url: str) -> dict:
    """Scrape content from a Wikipedia page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.find('h1', {'class': 'firstHeading'}).get_text().strip()
        
        # Extract main content paragraphs
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        paragraphs = content_div.find_all('p')
        
        # Clean and combine paragraphs
        content_parts = []
        for p in paragraphs:
            text = p.get_text().strip()
            # Remove citation markers like [1], [2], etc.
            text = re.sub(r'\[\d+\]', '', text)
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            if text and len(text) > 20:  # Only include substantial paragraphs
                content_parts.append(text)
        
        content = '\n\n'.join(content_parts)
        
        # Extract some metadata
        infobox = soup.find('table', {'class': 'infobox'})
        metadata = {
            'source': 'wikipedia',
            'url': url,
            'title': title,
            'has_infobox': infobox is not None
        }
        
        return {
            'title': title,
            'content': content,
            'metadata': metadata
        }
        
    except Exception as e:
        logging.error(f"Error scraping Wikipedia page {url}: {str(e)}")
        raise

def check_and_ingest_wikipedia():
    """Check if Wikipedia content is already ingested, if not, ingest it"""
    wikipedia_url = "https://en.wikipedia.org/wiki/Sai_Sai_Kham_Leng"
    document_id = "sai_sai_kham_leng_wiki"
    
    try:
        # Check if document already exists
        existing = collection.get(ids=[document_id])
        if existing['ids']:
            logging.info(f"Wikipedia content for {document_id} already exists, skipping ingestion")
            return
        
        logging.info(f"Ingesting Wikipedia content from {wikipedia_url}")
        
        # Scrape the Wikipedia page
        wiki_data = scrape_wikipedia_page(wikipedia_url)
        
        # Split content into chunks for better search results
        content = wiki_data['content']
        chunks = []
        
        # Split by paragraphs and create chunks of reasonable size
        paragraphs = content.split('\n\n')
        current_chunk = ""
        chunk_size = 1000  # characters
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Add chunks to ChromaDB
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            chunk_metadata = wiki_data['metadata'].copy()
            chunk_metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunks),
                'chunk_id': chunk_id
            })
            
            collection.add(
                documents=[chunk],
                metadatas=[chunk_metadata],
                ids=[chunk_id]
            )
        
        # Also add the full document
        collection.add(
            documents=[wiki_data['content']],
            metadatas=[wiki_data['metadata']],
            ids=[document_id]
        )
        
        logging.info(f"Successfully ingested {len(chunks)} chunks + full document for Sai Sai Kham Leng")
        
    except Exception as e:
        logging.error(f"Error during Wikipedia ingestion: {str(e)}")
        raise

# LLM functions
async def check_query_relevance(query: str) -> bool:
    """Check if the query is relevant to Sai Sai Kham Leng using LLM"""
    try:
        # First check for exact greetings and conversational phrases
        greeting_patterns = [
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
            "how are you", "what's up", "greetings", "nice to meet you",
            "thanks", "thank you", "bye", "goodbye", "see you", "ok", "okay"
        ]
        
        # Check for contextual follow-up questions that are clearly about Sai Sai
        contextual_patterns = [
            "so how old", "how old", "what age", "his age", "age now", "current age",
            "so what", "and what", "tell me more", "more info", "more details",
            "when was that", "what year", "which year", "how many", "how much"
        ]
        
        query_lower = query.lower().strip()
        
        # Check for exact matches or greetings at the start/end of short phrases
        if query_lower in greeting_patterns or any(
            query_lower.startswith(greeting + " ") or 
            query_lower.endswith(" " + greeting) or
            query_lower == greeting
            for greeting in greeting_patterns
        ):
            return True
            
        # Check for contextual follow-up questions
        if any(pattern in query_lower for pattern in contextual_patterns):
            return True
        
        prompt = f"""
You are a relevance checker for a Wikipedia search system about "Sai Sai Kham Leng", a Myanmar singer, actor, and entertainer.

Analyze this query and determine if it's asking about Sai Sai Kham Leng or topics related to him (his music, movies, career, personal life, etc.).

IMPORTANT: Always respond "YES" to:
- Greetings (hi, hello, hey, etc.)
- Polite phrases (thank you, please, etc.)
- Questions about Sai Sai Kham Leng (explicit or with pronouns like "his", "he", "him")
- Questions about music, albums, movies, films, acting, career when in context of an entertainment figure
- Follow-up questions about age, dates, numbers, details (like "how old?", "so what?", "when?")
- General conversational responses

Query: "{query}"

CONTEXT: This is a chatbot specifically about Sai Sai Kham Leng, so:
1. Questions using pronouns like "his albums", "his movies", "he acted" are referring to him
2. Follow-up questions like "how old?", "so what age?", "when was that?" are asking for more details about him
3. Short contextual questions are likely continuing a conversation about Sai Sai

Respond with only "YES" if the query is relevant to Sai Sai Kham Leng OR is a greeting/polite phrase, or "NO" if it's asking about something completely unrelated.

Examples:
- "Hi" → YES (greeting)
- "Hello" → YES (greeting)  
- "Thank you" → YES (polite phrase)
- "Who is Sai Sai Kham Leng?" → YES
- "What movies did he act in?" → YES  
- "Tell me about his music career" → YES
- "List his albums" → YES (referring to Sai Sai's albums)
- "What songs did he sing?" → YES (referring to Sai Sai)
- "His filmography" → YES (referring to Sai Sai)
- "How old?" → YES (follow-up question about age)
- "So how old?" → YES (follow-up question)
- "When was that?" → YES (follow-up about dates)
- "What is the weather today?" → NO
- "How to cook pasta?" → NO
- "What is Python programming?" → NO

Response:"""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip().upper()
        return result == "YES"
        
    except Exception as e:
        logging.error(f"Error checking query relevance: {str(e)}")
        # Default to True to avoid blocking legitimate queries if LLM fails
        return True

async def summarize_search_results(query: str, documents: List[str]) -> str:
    """Summarize search results using LLM with structured formatting when appropriate"""
    try:
        # Check if this is an exact greeting or conversational phrase
        greeting_patterns = [
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
            "how are you", "what's up", "greetings", "nice to meet you"
        ]
        
        farewell_patterns = ["thanks", "thank you", "bye", "goodbye", "see you"]
        acknowledgment_patterns = ["ok", "okay", "alright", "got it"]
        
        # Age-related contextual questions
        age_patterns = ["so how old", "how old", "what age", "his age", "age now", "current age"]
        
        query_lower = query.lower().strip()
        
        # Handle exact greetings only
        if query_lower in greeting_patterns or any(
            query_lower.startswith(greeting + " ") or 
            query_lower.endswith(" " + greeting) or
            query_lower == greeting
            for greeting in greeting_patterns
        ):
            return "Hello! I'm your AI assistant for Sai Sai Kham Leng. I can help you learn about his music, movies, career, and personal life. What would you like to know about him?"
        
        # Handle exact farewells only
        if query_lower in farewell_patterns or any(
            query_lower.startswith(farewell + " ") or 
            query_lower.endswith(" " + farewell) or
            query_lower == farewell
            for farewell in farewell_patterns
        ):
            return "You're welcome! Feel free to ask me anything else about Sai Sai Kham Leng anytime. Have a great day!"
        
        # Handle exact acknowledgments only
        if query_lower in acknowledgment_patterns or any(
            query_lower.startswith(ack + " ") or 
            query_lower.endswith(" " + ack) or
            query_lower == ack
            for ack in acknowledgment_patterns
        ):
            return "Great! Is there anything else you'd like to know about Sai Sai Kham Leng? I can tell you about his albums, movies, career highlights, or personal life."
        
        # Handle age-related questions with calculation
        if any(pattern in query_lower for pattern in age_patterns):
            # Calculate age from birth date (April 10, 1979)
            birth_date = datetime(1979, 4, 10)
            current_date = datetime.now()
            age = current_date.year - birth_date.year
            if current_date.month < birth_date.month or (current_date.month == birth_date.month and current_date.day < birth_date.day):
                age -= 1
            
            return f"Sai Sai Kham Leng is currently {age} years old. He was born on April 10, 1979."
        
        # If no documents provided (shouldn't happen for non-greetings, but safety check)
        if not documents or not documents[0]:
            return "I'd be happy to help you learn about Sai Sai Kham Leng! Could you ask me something specific about his music, movies, or career?"
        
        # Combine documents for context
        combined_content = "\n\n".join(documents[:3])  # Use top 3 results
        
        prompt = f"""
Based on the following information about Sai Sai Kham Leng, provide a well-formatted answer to the user's question.

User Question: "{query}"

Information from Wikipedia:
{combined_content}

Instructions:
1. Analyze if the user is asking for structured data (lists, tables, chronological info, etc.)
2. If they want structured data (like "list albums", "show movies", "timeline", etc.), format as:
   - Use bullet points (•) for lists
   - Use table format with | separators for tabular data
   - Use numbered lists for chronological items
   - Example table format: | Album Name | Year | Notes |
3. If it's a general question, provide a conversational 2-4 sentence answer
4. Focus on directly answering the user's question
5. Use only the information provided
6. If information is incomplete, mention what you found

Detect these structured request patterns:
- "list", "show", "enumerate", "table" → Use structured format
- "albums", "movies", "films", "songs" + "names/titles/years" → Use table/list
- "chronology", "timeline", "order" → Use numbered list
- General questions → Use conversational format

Answer:"""

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        logging.error(f"Error summarizing results: {str(e)}")
        return "I found some relevant information, but couldn't generate a summary at the moment."

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run startup tasks"""
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting ChatWith Wiki application...")
    
    try:
        # Ingest Wikipedia content on startup
        check_and_ingest_wikipedia()
        logging.info("Startup completed successfully")
    except Exception as e:
        logging.error(f"Error during startup: {str(e)}")
        # Don't raise the error to prevent app from failing to start
        # The app can still function for other operations

@app.get("/")
async def root():
    return {"message": "Welcome to ChatWith Wiki API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

@app.post("/documents/", response_model=dict)
async def add_document(document: Document):
    try:
        collection.add(
            documents=[document.content],
            metadatas=[document.metadata or {}],
            ids=[document.id]
        )
        return {"message": f"Document {document.id} added successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    try:
        result = collection.get(ids=[document_id])
        if not result['ids']:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "id": result['ids'][0],
            "content": result['documents'][0],
            "metadata": result['metadatas'][0]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/search/", response_model=QueryResponse)
async def search_documents(query: QueryRequest):
    try:
        # First, check if the query is relevant to Sai Sai Kham Leng
        is_relevant = await check_query_relevance(query.query)
        
        if not is_relevant:
            return QueryResponse(
                documents=[],
                metadatas=[],
                distances=[],
                ids=[],
                summary=None,
                is_relevant=False,
                message="Your question doesn't seem to be related to Sai Sai Kham Leng. Please ask about his music, movies, career, or personal life."
            )
        
        # Check if this is an exact greeting or conversational phrase (skip Wikipedia search)
        greeting_patterns = [
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
            "how are you", "what's up", "greetings", "nice to meet you",
            "thanks", "thank you", "bye", "goodbye", "see you", "ok", "okay", "alright", "got it"
        ]
        
        # Age-related questions that can be answered directly
        age_patterns = ["so how old", "how old", "what age", "his age", "age now", "current age"]
        
        query_lower = query.query.lower().strip()
        is_greeting = query_lower in greeting_patterns or any(
            query_lower.startswith(greeting + " ") or 
            query_lower.endswith(" " + greeting) or
            query_lower == greeting
            for greeting in greeting_patterns
        )
        
        is_age_question = any(pattern in query_lower for pattern in age_patterns)
        
        if is_greeting or is_age_question:
            # Handle greetings and age questions without searching Wikipedia
            summary = await summarize_search_results(query.query, [])
            return QueryResponse(
                documents=[],
                metadatas=[],
                distances=[],
                ids=[],
                summary=summary,
                is_relevant=True
            )
        
        # If relevant and not a greeting, perform the search
        results = collection.query(
            query_texts=[query.query],
            n_results=query.n_results
        )
        
        # Check if we found any results
        if not results['documents'][0]:
            return QueryResponse(
                documents=[],
                metadatas=[],
                distances=[],
                ids=[],
                summary="I couldn't find specific information about that topic in the available content about Sai Sai Kham Leng.",
                is_relevant=True,
                message="No matching content found."
            )
        
        # Generate summary using LLM
        summary = await summarize_search_results(query.query, results['documents'][0])
        
        return QueryResponse(
            documents=results['documents'][0],
            metadatas=results['metadatas'][0],
            distances=results['distances'][0],
            ids=results['ids'][0],
            summary=summary,
            is_relevant=True
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    try:
        collection.delete(ids=[document_id])
        return {"message": f"Document {document_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/collection/info")
async def get_collection_info():
    try:
        count = collection.count()
        return {
            "collection_name": collection.name,
            "document_count": count
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
