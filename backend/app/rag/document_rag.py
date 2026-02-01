from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import hashlib
import json
from sqlalchemy import select, and_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import asyncio

from app.database import AsyncSessionLocal
from app.config import get_settings

settings = get_settings()


@dataclass
class DocumentChunk:
    """A chunk of processed document"""
    id: str
    document_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    chunk_index: int
    created_at: datetime


@dataclass
class SearchResult:
    """Result from semantic search"""
    chunk: DocumentChunk
    score: float
    highlights: List[str]


class DocumentProcessor:
    """Process and chunk unstructured documents"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    async def process_document(
        self,
        tenant_id: str,
        document_name: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process a document into chunks and store embeddings"""
        
        # Generate document ID
        doc_id = hashlib.md5(
            f"{tenant_id}:{document_name}".encode()
        ).hexdigest()
        
        # Split into chunks
        chunks = self.text_splitter.split_text(content)
        
        # Process each chunk
        processed_chunks = []
        for i, chunk_text in enumerate(chunks):
            # Generate embedding
            embedding = await self.embeddings.aembed_query(chunk_text)
            
            chunk = DocumentChunk(
                id=f"{doc_id}_{i}",
                document_id=doc_id,
                content=chunk_text,
                embedding=embedding,
                metadata={
                    **(metadata or {}),
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                },
                chunk_index=i,
                created_at=datetime.utcnow()
            )
            processed_chunks.append(chunk)
        
        # Store in database
        await self._store_chunks(tenant_id, doc_id, document_name, processed_chunks)
        
        return {
            "document_id": doc_id,
            "document_name": document_name,
            "total_chunks": len(chunks),
            "chunks": [c.id for c in processed_chunks]
        }
    
    async def _store_chunks(
        self,
        tenant_id: str,
        document_id: str,
        document_name: str,
        chunks: List[DocumentChunk]
    ):
        """Store document chunks in database"""
        
        async with AsyncSessionLocal() as session:
            # First, store document metadata
            from app.models import Document
            
            doc = Document(
                id=document_id,
                tenant_id=tenant_id,
                name=document_name,
                chunk_count=len(chunks),
                metadata={"processed_at": datetime.utcnow().isoformat()}
            )
            
            # Upsert document
            await session.merge(doc)
            
            # Store chunks
            for chunk in chunks:
                chunk_record = DocumentChunkModel(
                    id=chunk.id,
                    document_id=chunk.document_id,
                    tenant_id=tenant_id,
                    content=chunk.content,
                    embedding=chunk.embedding,
                    metadata=chunk.metadata,
                    chunk_index=chunk.chunk_index
                )
                await session.merge(chunk_record)
            
            await session.commit()


class RAGRetriever:
    """Retrieve relevant context from documents for RAG"""
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key
        )
    
    async def search(
        self,
        tenant_id: str,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5,
        min_score: float = 0.7
    ) -> List[SearchResult]:
        """Search for relevant document chunks"""
        
        # Generate query embedding
        query_embedding = await self.embeddings.aembed_query(query)
        
        async with AsyncSessionLocal() as session:
            # Build query
            if document_ids:
                # Search specific documents
                sql = text("""
                    SELECT 
                        dc.id,
                        dc.document_id,
                        dc.content,
                        dc.metadata,
                        dc.chunk_index,
                        1 - (dc.embedding <=> :embedding) as similarity
                    FROM document_chunks dc
                    WHERE dc.tenant_id = :tenant_id
                    AND dc.document_id = ANY(:document_ids)
                    ORDER BY dc.embedding <=> :embedding
                    LIMIT :limit
                """)
                result = await session.execute(
                    sql,
                    {
                        "tenant_id": tenant_id,
                        "document_ids": document_ids,
                        "embedding": str(query_embedding),
                        "limit": top_k * 2  // Get more for filtering
                    }
                )
            else:
                # Search all tenant documents
                sql = text("""
                    SELECT 
                        dc.id,
                        dc.document_id,
                        dc.content,
                        dc.metadata,
                        dc.chunk_index,
                        1 - (dc.embedding <=> :embedding) as similarity
                    FROM document_chunks dc
                    WHERE dc.tenant_id = :tenant_id
                    ORDER BY dc.embedding <=> :embedding
                    LIMIT :limit
                """)
                result = await session.execute(
                    sql,
                    {
                        "tenant_id": tenant_id,
                        "embedding": str(query_embedding),
                        "limit": top_k * 2
                    }
                )
            
            rows = result.fetchall()
            
            # Build results
            results = []
            for row in rows:
                if row.similarity >= min_score:
                    chunk = DocumentChunk(
                        id=row.id,
                        document_id=row.document_id,
                        content=row.content,
                        embedding=[],  # Don't return embeddings
                        metadata=row.metadata,
                        chunk_index=row.chunk_index,
                        created_at=datetime.utcnow()
                    )
                    
                    # Extract highlights
                    highlights = self._extract_highlights(row.content, query)
                    
                    results.append(SearchResult(
                        chunk=chunk,
                        score=row.similarity,
                        highlights=highlights
                    ))
            
            # Return top_k
            return results[:top_k]
    
    def _extract_highlights(
        self,
        content: str,
        query: str
    ) -> List[str]:
        """Extract relevant highlights from content"""
        # Simple keyword-based highlighting
        query_words = query.lower().split()
        sentences = content.split(". ")
        
        highlights = []
        for sentence in sentences[:3]:  # Top 3 sentences
            if any(word in sentence.lower() for word in query_words):
                highlights.append(sentence.strip() + ".")
        
        return highlights[:2]  # Return top 2 highlights
    
    async def hybrid_search(
        self,
        tenant_id: str,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[SearchResult]:
        """Combine semantic + keyword search"""
        
        # Semantic search
        semantic_results = await self.search(
            tenant_id, query, document_ids, top_k=top_k * 2
        )
        
        # Keyword search (using full-text search if available)
        keyword_results = await self._keyword_search(
            tenant_id, query, document_ids, top_k=top_k
        )
        
        # Combine and deduplicate
        seen_ids = set()
        combined = []
        
        for result in semantic_results + keyword_results:
            if result.chunk.id not in seen_ids:
                seen_ids.add(result.chunk.id)
                combined.append(result)
        
        # Sort by score
        combined.sort(key=lambda x: x.score, reverse=True)
        
        return combined[:top_k]
    
    async def _keyword_search(
        self,
        tenant_id: str,
        query: str,
        document_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[SearchResult]:
        """Simple keyword-based search as fallback"""
        
        async with AsyncSessionLocal() as session:
            # Build query with ILIKE for keyword matching
            query_terms = query.split()
            
            conditions = [
                f"dc.content ILIKE '%{term}%'" for term in query_terms[:3]
            ]
            
            if document_ids:
                doc_filter = f"AND dc.document_id = ANY(ARRAY{document_ids})"
            else:
                doc_filter = ""
            
            sql = text(f"""
                SELECT 
                    dc.id,
                    dc.document_id,
                    dc.content,
                    dc.metadata,
                    dc.chunk_index,
                    CASE 
                        {' + '.join([f"CASE WHEN dc.content ILIKE '%{t}%' THEN 1 ELSE 0 END" for t in query_terms[:3]])}
                    END as keyword_score
                FROM document_chunks dc
                WHERE dc.tenant_id = :tenant_id
                {doc_filter}
                AND ({' OR '.join(conditions)})
                ORDER BY keyword_score DESC
                LIMIT :limit
            """)
            
            result = await session.execute(
                sql,
                {"tenant_id": tenant_id, "limit": top_k}
            )
            
            rows = result.fetchall()
            
            return [
                SearchResult(
                    chunk=DocumentChunk(
                        id=row.id,
                        document_id=row.document_id,
                        content=row.content,
                        embedding=[],
                        metadata=row.metadata,
                        chunk_index=row.chunk_index,
                        created_at=datetime.utcnow()
                    ),
                    score=row.keyword_score / 3.0,  # Normalize
                    highlights=[row.content[:200] + "..."]
                )
                for row in rows
            ]


class RAGOrchestrator:
    """Orchestrate RAG workflow for AI responses"""
    
    def __init__(self):
        self.retriever = RAGRetriever()
        self.processor = DocumentProcessor()
    
    async def augment_query(
        self,
        tenant_id: str,
        query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Augment a query with relevant document context"""
        
        # Determine if we need document context
        if not self._needs_document_context(query):
            return {**context, "document_context": None}
        
        # Retrieve relevant chunks
        results = await self.retriever.hybrid_search(
            tenant_id=tenant_id,
            query=query,
            top_k=5
        )
        
        if not results:
            return {**context, "document_context": None}
        
        # Build context string
        document_context = self._build_context_string(results)
        
        # Add source metadata
        sources = [
            {
                "document_id": r.chunk.document_id,
                "chunk_index": r.chunk.chunk_index,
                "relevance": r.score,
                "highlights": r.highlights
            }
            for r in results
        ]
        
        return {
            **context,
            "document_context": {
                "context_string": document_context,
                "sources": sources,
                "chunks_used": len(results)
            }
        }
    
    def _needs_document_context(self, query: str) -> bool:
        """Determine if query likely needs document context"""
        # Keywords that suggest document lookup
        doc_keywords = [
            "report", "document", "pdf", "file", "upload",
            "according to", "mentions", "states", "says",
            "documentation", "specification", "proposal"
        ]
        
        query_lower = query.lower()
        return any(kw in query_lower for kw in doc_keywords)
    
    def _build_context_string(self, results: List[SearchResult]) -> str:
        """Build context string from search results"""
        context_parts = []
        
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Document {i}]\n"
                f"Content: {result.chunk.content}\n"
                f"Relevance: {result.score:.0%}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    async def upload_document(
        self,
        tenant_id: str,
        file_name: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Upload and process a document"""
        
        # Validate file type
        allowed_extensions = ['.txt', '.md', '.pdf', '.docx']
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            return {
                "success": False,
                "error": f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            }
        
        # Process document
        try:
            result = await self.processor.process_document(
                tenant_id=tenant_id,
                document_name=file_name,
                content=content,
                metadata=metadata
            )
            
            return {
                "success": True,
                "document_id": result["document_id"],
                "chunks_processed": result["total_chunks"],
                "message": f"Successfully processed {file_name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# SQLAlchemy model for document chunks (add to models.py)
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON, ARRAY
from pgvector.sqlalchemy import Vector
from app.database import Base

class Document(Base):
    """Document metadata"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    chunk_count = Column(Integer, default=0)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentChunkModel(Base):
    """Document chunks with embeddings"""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    tenant_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    metadata = Column(JSON)
    chunk_index = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
