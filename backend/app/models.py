

# Document RAG models
class Document(Base):
    """Uploaded documents for RAG"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String, nullable=False)
    content_type = Column(String(50))  # pdf, txt, md, etc.
    chunk_count = Column(Integer, default=0)
    file_size = Column(Integer)  # bytes
    metadata = Column(JSON)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class DocumentChunk(Base):
    """Chunks of documents with embeddings for RAG"""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    chunk_index = Column(Integer)
    metadata = Column(JSON)  # page number, section, etc.
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
