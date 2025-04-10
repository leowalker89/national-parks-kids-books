from enum import Enum
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union, cast, Literal

class Page(BaseModel):
    """
    Represents a single page in a children's book.
    
    Attributes:
        page_number: The sequential number of the page
        illustration_description: Detailed description for illustrating the page
        text: The text content for the page (limited to ~10 words for board books)
    """
    page_number: Optional[int] = None
    illustration_description: str 
    text: str

class KidsBook(BaseModel):
    """
    Represents a complete children's book about a national park.
    
    Attributes:
        park_name: The name of the national park
        front_cover: Cover page with title and illustration description
        pages: A list of Page objects making up the book content
        back_cover: Back cover with summary and illustration description
    """
    park_name: str
    front_cover: Page
    pages: List[Page]
    back_cover: Page


GenerationStage = Literal[
    "initializing",
    "outlining",
    "structuring_chapters",
    "generating_concepts",
    "generating_pages",
    "aggregating_pages",
    "generating_covers",
    "assembling",
    "completed",
    "error"
]

class StoryOutline(BaseModel):
    """
    Represents the high-level narrative arc or storyline for the book.
    
    Attributes:
        narrative_flow: Text describing the overall story progression.
        key_themes: List of major themes or elements to be covered.
    """
    narrative_flow: str
    key_themes: List[str]

class ChapterDefinition(BaseModel):
    """
    Defines the theme and key elements for a specific section or 'mini-chapter'.
    
    Attributes:
        chapter_number: Sequential number of the chapter.
        theme: The central theme or focus of this chapter (e.g., "Mountain Peaks", "Forest Wildlife").
        key_elements: Specific landmarks, animals, or plants from research assigned to this chapter.
        page_count: Estimated number of pages for this chapter.
    """
    chapter_number: int
    theme: str
    key_elements: List[str]
    page_count: int

class PageConcept(BaseModel):
    """
    Represents the core idea or subject for a single page before detailed content generation.
    
    Attributes:
        page_number: The intended final page number.
        chapter_number: The chapter this page belongs to.
        subject: The main subject (e.g., "Elk", "Longs Peak", "Columbine flower").
        core_idea: A brief description of what the page should convey about the subject.
    """
    page_number: Optional[int] = None
    chapter_number: Optional[int] = None
    subject: str
    core_idea: str

class GenerationState(BaseModel):
    """
    Holds the evolving state of the book generation process across multiple steps.
    
    Attributes:
        park_name: Name of the national park.
        research_content: Original research data provided.
        status: Current stage in the generation workflow, validated against GenerationStage values.
        story_outline: Optional high-level narrative arc.
        chapter_definitions: Optional list defining each chapter's theme and elements.
        page_concepts: Optional list of concepts for pages within the current chapter/overall book.
        generated_pages: List of fully generated Page objects.
        front_cover: Optional generated front cover Page.
        back_cover: Optional generated back cover Page.
        final_book: Optional complete KidsBook object upon successful completion.
        error_details: Optional string describing any error encountered.
    """
    park_name: str
    research_content: str
    status: GenerationStage = "initializing"
    story_outline: Optional[StoryOutline] = None
    chapter_definitions: Optional[List[ChapterDefinition]] = None
    page_concepts: Optional[List[PageConcept]] = None
    generated_pages: List[Page] = []
    front_cover: Optional[Page] = None
    back_cover: Optional[Page] = None
    final_book: Optional[KidsBook] = None
    error_details: Optional[str] = None

class ChapterDefinitions(BaseModel):
    chapters: List[ChapterDefinition]

class PageConceptCollection(BaseModel):
    """
    Container for a collection of page concepts.
    
    Attributes:
        concepts: List of PageConcept objects representing individual page ideas.
    """
    concepts: List[PageConcept]

