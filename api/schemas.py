from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class NoteType(str, Enum):
    IDEA = "idea"
    QUESTION = "question"
    DEFINITION = "definition"

class Domain(str, Enum):
    PHYSICS = "physics"
    SECURITY = "security"
    PHILOSOPHY = "philosophy"
    PERSONAL = "personal"
    OTHER = "other"

class RelationType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    REFERENCES = "references"

# Base schemas
class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str
    note_type: NoteType = NoteType.IDEA
    domain: Domain = Domain.OTHER

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    note_type: Optional[NoteType] = None
    domain: Optional[Domain] = None
    change_reason: str = Field(..., min_length=1)

class LinkBase(BaseModel):
    from_id: str
    to_id: str
    relation: RelationType = RelationType.REFERENCES

class LinkCreate(LinkBase):
    pass

# Response schemas
class NoteVersionResponse(BaseModel):
    id: str
    old_content: str
    change_reason: Optional[str]
    changed_at: datetime
    
    class Config:
        from_attributes = True

class NoteResponse(NoteBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class NoteWithLinksResponse(NoteResponse):
    outgoing_links: List[dict] = []
    incoming_links: List[dict] = []
    versions: List[NoteVersionResponse] = []

class LinkResponse(LinkBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class GraphNode(BaseModel):
    id: str
    title: str
    note_type: NoteType
    domain: Domain

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: RelationType

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
