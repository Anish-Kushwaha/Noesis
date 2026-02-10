from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class NoteType(str, enum.Enum):
    IDEA = "idea"
    QUESTION = "question"
    DEFINITION = "definition"

class Domain(str, enum.Enum):
    PHYSICS = "physics"
    SECURITY = "security"
    PHILOSOPHY = "philosophy"
    PERSONAL = "personal"
    OTHER = "other"

class RelationType(str, enum.Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    REFERENCES = "references"

class Note(Base):
    __tablename__ = "notes"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(Enum(NoteType), default=NoteType.IDEA)
    domain = Column(Enum(Domain), default=Domain.OTHER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    versions = relationship("NoteVersion", back_populates="note", cascade="all, delete-orphan")
    outgoing_links = relationship("Link", 
                                  foreign_keys="[Link.from_id]",
                                  back_populates="source_note")
    incoming_links = relationship("Link",
                                  foreign_keys="[Link.to_id]",
                                  back_populates="target_note")

class NoteVersion(Base):
    __tablename__ = "note_versions"
    
    id = Column(String, primary_key=True, index=True)
    note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"))
    old_content = Column(Text, nullable=False)
    change_reason = Column(Text)
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    note = relationship("Note", back_populates="versions")

class Link(Base):
    __tablename__ = "links"
    
    id = Column(String, primary_key=True, index=True)
    from_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"))
    to_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"))
    relation = Column(Enum(RelationType), default=RelationType.REFERENCES)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    source_note = relationship("Note", 
                               foreign_keys=[from_id],
                               back_populates="outgoing_links")
    target_note = relationship("Note",
                               foreign_keys=[to_id],
                               back_populates="incoming_links")
