from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
import uuid
import os
from datetime import datetime
from typing import List, Optional

# Import database and models
from .database import engine, Base, get_db
from .models import Note, NoteVersion, Link, NoteType, Domain, RelationType
from .schemas import (
    NoteCreate, NoteUpdate, NoteResponse, 
    NoteWithLinksResponse, NoteVersionResponse,
    LinkCreate, LinkResponse,
    GraphResponse, GraphNode, GraphEdge
)

# Create database tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    print("🚀 Noesis API starting up...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Add sample data if needed
    # await create_sample_data()
    
    yield
    
    print("👋 Noesis API shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="Noesis API",
    description="Personal Knowledge Operating System - Backend API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS - Allow requests from GitHub Pages and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://anish-kushwaha.github.io",  # GitHub Pages
        "https://noesis-psi.vercel.app",     # Vercel frontend (if needed)
        "http://localhost:3000",             # Local development
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"  # Remove in production for security
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "🌌 Welcome to Noesis API",
        "description": "Personal Knowledge Operating System",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "notes": "/api/notes",
            "graph": "/api/graph",
            "links": "/api/links",
            "health": "/api/health",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "author": "Anish Kushwaha",
        "github": "https://github.com/Anish-Kushwaha/Noesis"
    }

# Health check endpoint
@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {
            "status": "✅ Healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "Connected",
            "service": "Noesis API"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )

# ========== NOTE ENDPOINTS ==========

@app.post("/api/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    """Create a new note/idea"""
    try:
        db_note = Note(
            id=str(uuid.uuid4()),
            title=note.title.strip(),
            content=note.content.strip(),
            note_type=note.note_type,
            domain=note.domain
        )
        db.add(db_note)
        db.commit()
        db.refresh(db_note)
        
        # Create initial version
        version = NoteVersion(
            id=str(uuid.uuid4()),
            note_id=db_note.id,
            old_content="",  # No old content for creation
            change_reason="Initial creation"
        )
        db.add(version)
        db.commit()
        
        return db_note
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create note: {str(e)}"
        )

@app.get("/api/notes", response_model=List[NoteResponse])
async def get_all_notes(
    skip: int = 0,
    limit: int = 100,
    domain: Optional[Domain] = None,
    note_type: Optional[NoteType] = None,
    db: Session = Depends(get_db)
):
    """Get all notes with optional filtering"""
    query = db.query(Note)
    
    if domain:
        query = query.filter(Note.domain == domain)
    if note_type:
        query = query.filter(Note.note_type == note_type)
    
    notes = query.order_by(Note.created_at.desc()).offset(skip).limit(limit).all()
    return notes

@app.get("/api/notes/{note_id}", response_model=NoteWithLinksResponse)
async def get_note(note_id: str, db: Session = Depends(get_db)):
    """Get a specific note with its links and versions"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found"
        )
    
    # Get versions
    versions = db.query(NoteVersion).filter(
        NoteVersion.note_id == note_id
    ).order_by(NoteVersion.changed_at.desc()).all()
    
    # Get outgoing links
    outgoing = db.query(Link).filter(Link.from_id == note_id).all()
    
    # Get incoming links (backlinks)
    incoming = db.query(Link).filter(Link.to_id == note_id).all()
    
    # Create response
    response = NoteWithLinksResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        note_type=note.note_type,
        domain=note.domain,
        created_at=note.created_at,
        updated_at=note.updated_at,
        outgoing_links=[{"id": l.id, "to_id": l.to_id, "relation": l.relation} for l in outgoing],
        incoming_links=[{"id": l.id, "from_id": l.from_id, "relation": l.relation} for l in incoming],
        versions=[NoteVersionResponse(
            id=v.id,
            old_content=v.old_content,
            change_reason=v.change_reason,
            changed_at=v.changed_at
        ) for v in versions]
    )
    
    return response

@app.put("/api/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str, 
    update_data: NoteUpdate, 
    db: Session = Depends(get_db)
):
    """Update a note (requires change reason)"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found"
        )
    
    if not update_data.change_reason or update_data.change_reason.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Change reason is required for updates"
        )
    
    try:
        # Save current version before updating
        version = NoteVersion(
            id=str(uuid.uuid4()),
            note_id=note_id,
            old_content=note.content,
            change_reason=update_data.change_reason.strip()
        )
        db.add(version)
        
        # Update note fields
        if update_data.title is not None:
            note.title = update_data.title.strip()
        if update_data.content is not None:
            note.content = update_data.content.strip()
        if update_data.note_type is not None:
            note.note_type = update_data.note_type
        if update_data.domain is not None:
            note.domain = update_data.domain
        
        note.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(note)
        
        return note
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update note: {str(e)}"
        )

@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: str, db: Session = Depends(get_db)):
    """Delete a note and all associated data"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found"
        )
    
    try:
        # Delete the note (cascade will handle versions and links)
        db.delete(note)
        db.commit()
        
        return {
            "message": "Note deleted successfully",
            "note_id": note_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete note: {str(e)}"
        )

@app.get("/api/notes/{note_id}/versions", response_model=List[NoteVersionResponse])
async def get_note_versions(note_id: str, db: Session = Depends(get_db)):
    """Get version history for a note"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found"
        )
    
    versions = db.query(NoteVersion).filter(
        NoteVersion.note_id == note_id
    ).order_by(NoteVersion.changed_at.desc()).all()
    
    return versions

# ========== LINK ENDPOINTS ==========

@app.post("/api/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_link(link: LinkCreate, db: Session = Depends(get_db)):
    """Create a link between two notes"""
    # Check if both notes exist
    from_note = db.query(Note).filter(Note.id == link.from_id).first()
    to_note = db.query(Note).filter(Note.id == link.to_id).first()
    
    if not from_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source note with ID {link.from_id} not found"
        )
    
    if not to_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target note with ID {link.to_id} not found"
        )
    
    # Check for self-link
    if link.from_id == link.to_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link a note to itself"
        )
    
    # Check if link already exists
    existing_link = db.query(Link).filter(
        Link.from_id == link.from_id,
        Link.to_id == link.to_id
    ).first()
    
    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link already exists between these notes"
        )
    
    try:
        db_link = Link(
            id=str(uuid.uuid4()),
            from_id=link.from_id,
            to_id=link.to_id,
            relation=link.relation
        )
        
        db.add(db_link)
        db.commit()
        db.refresh(db_link)
        
        return db_link
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create link: {str(e)}"
        )

@app.get("/api/links/from/{note_id}", response_model=List[LinkResponse])
async def get_outgoing_links(note_id: str, db: Session = Depends(get_db)):
    """Get all links originating from a note"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found"
        )
    
    links = db.query(Link).filter(Link.from_id == note_id).all()
    return links

@app.get("/api/links/to/{note_id}", response_model=List[LinkResponse])
async def get_incoming_links(note_id: str, db: Session = Depends(get_db)):
    """Get all links pointing to a note (backlinks)"""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found"
        )
    
    links = db.query(Link).filter(Link.to_id == note_id).all()
    return links

@app.delete("/api/links/{link_id}")
async def delete_link(link_id: str, db: Session = Depends(get_db)):
    """Delete a link"""
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Link with ID {link_id} not found"
        )
    
    try:
        db.delete(link)
        db.commit()
        
        return {
            "message": "Link deleted successfully",
            "link_id": link_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete link: {str(e)}"
        )

# ========== GRAPH ENDPOINTS ==========

@app.get("/api/graph", response_model=GraphResponse)
async def get_graph_data(
    domain: Optional[Domain] = None,
    db: Session = Depends(get_db)
):
    """Get all notes and links for graph visualization"""
    # Get notes
    query = db.query(Note)
    if domain:
        query = query.filter(Note.domain == domain)
    notes = query.all()
    
    # Get all links between the notes
    note_ids = [note.id for note in notes]
    links = db.query(Link).filter(
        Link.from_id.in_(note_ids),
        Link.to_id.in_(note_ids)
    ).all()
    
    # Convert to graph format
    nodes = [
        GraphNode(
            id=note.id,
            title=note.title,
            note_type=note.note_type,
            domain=note.domain
        )
        for note in notes
    ]
    
    edges = [
        GraphEdge(
            id=link.id,
            source=link.from_id,
            target=link.to_id,
            relation=link.relation
        )
        for link in links
    ]
    
    return GraphResponse(nodes=nodes, edges=edges)

@app.get("/api/graph/search")
async def search_notes(
    q: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Search notes by title or content"""
    if not q or len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters"
        )
    
    search_term = f"%{q.strip().lower()}%"
    
    notes = db.query(Note).filter(
        (Note.title.ilike(search_term)) | 
        (Note.content.ilike(search_term))
    ).limit(limit).all()
    
    return [
        {
            "id": note.id,
            "title": note.title,
            "content_preview": note.content[:100] + "..." if len(note.content) > 100 else note.content,
            "note_type": note.note_type,
            "domain": note.domain,
            "created_at": note.created_at.isoformat()
        }
        for note in notes
    ]

# ========== STATISTICS ENDPOINTS ==========

@app.get("/api/stats")
async def get_statistics(db: Session = Depends(get_db)):
    """Get system statistics"""
    total_notes = db.query(Note).count()
    total_links = db.query(Link).count()
    total_versions = db.query(NoteVersion).count()
    
    # Count by note type
    ideas = db.query(Note).filter(Note.note_type == NoteType.IDEA).count()
    questions = db.query(Note).filter(Note.note_type == NoteType.QUESTION).count()
    definitions = db.query(Note).filter(Note.note_type == NoteType.DEFINITION).count()
    
    # Count by domain
    domains = {}
    for domain in Domain:
        count = db.query(Note).filter(Note.domain == domain).count()
        if count > 0:
            domains[domain.value] = count
    
    return {
        "total_notes": total_notes,
        "total_links": total_links,
        "total_versions": total_versions,
        "by_type": {
            "ideas": ideas,
            "questions": questions,
            "definitions": definitions
        },
        "by_domain": domains,
        "timestamp": datetime.utcnow().isoformat()
    }

# ========== ERROR HANDLERS ==========

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": request.url.path
        }
    )

# ========== SAMPLE DATA CREATION ==========

async def create_sample_data():
    """Create sample data for testing"""
    db = next(get_db())
    
    try:
        # Check if we already have data
        if db.query(Note).count() > 0:
            print("✅ Database already has data")
            return
        
        print("📝 Creating sample data...")
        
        # Create sample notes
        sample_notes = [
            {
                "title": "What is Noesis?",
                "content": "Noesis is a personal knowledge operating system designed to externalize structured thinking.",
                "note_type": NoteType.DEFINITION,
                "domain": Domain.PHILOSOPHY
            },
            {
                "title": "Atomic Knowledge Principle",
                "content": "One idea per note. This ensures clarity and enables better connections.",
                "note_type": NoteType.IDEA,
                "domain": Domain.PHILOSOPHY
            },
            {
                "title": "How do ideas evolve?",
                "content": "Ideas change over time. Tracking these changes helps understand thought evolution.",
                "note_type": NoteType.QUESTION,
                "domain": Domain.PHILOSOPHY
            },
            {
                "title": "Graphs vs Folders",
                "content": "Folders force hierarchical thinking. Graphs allow natural, interconnected thinking.",
                "note_type": NoteType.IDEA,
                "domain": Domain.SECURITY
            }
        ]
        
        note_objects = []
        for note_data in sample_notes:
            note = Note(
                id=str(uuid.uuid4()),
                **note_data
            )
            db.add(note)
            note_objects.append(note)
        
        db.commit()
        
        # Create sample links
        if len(note_objects) >= 4:
            links = [
                {"from": note_objects[0], "to": note_objects[1], "relation": RelationType.EXTENDS},
                {"from": note_objects[1], "to": note_objects[2], "relation": RelationType.SUPPORTS},
                {"from": note_objects[3], "to": note_objects[1], "relation": RelationType.EXTENDS},
                {"from": note_objects[2], "to": note_objects[3], "relation": RelationType.REFERENCES}
            ]
            
            for link_data in links:
                link = Link(
                    id=str(uuid.uuid4()),
                    from_id=link_data["from"].id,
                    to_id=link_data["to"].id,
                    relation=link_data["relation"]
                )
                db.add(link)
            
            db.commit()
        
        print(f"✅ Created {len(sample_notes)} sample notes and {len(links)} links")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()

# Run the application
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Starting Noesis API on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
