# flake8: noqa
# pylint: skip-file
# ruff: noqa
# src/common/book_content_graph/content_nodes.py

import asyncio
from typing import Dict, Any, List, TypeVar, Type, Callable, Optional, cast, Union
from dotenv import load_dotenv
from tenacity import wait_exponential, retry_if_exception_type

load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda, Runnable
from langchain_core.exceptions import OutputParserException
from anthropic import APIError, RateLimitError # Example for Anthropic
import httpx # For potential timeout errors

# Import state definitions
from .content_states import (
    GenerationState, StoryOutline, ChapterDefinitions, PageConcept, 
    Page, KidsBook, PageConceptCollection, ChapterDefinition
)
# Import prompts (assuming they are defined in content_prompts.py)
from . import content_prompts as prompts 
# Import config/constants (assuming defined elsewhere, e.g., config.py or state)
from ..config import DEFAULT_MODEL, TARGET_PAGE_COUNT 

# Type variable for structured output types
T = TypeVar('T')

# --- Utility Functions ---
def get_llm(model_name: str = DEFAULT_MODEL, temperature: float = 0.7) -> ChatAnthropic:
    """Initializes the ChatAnthropic model with proper parameters.
    
    Args:
        model_name: Name of the model to use (imported default)
        temperature: Temperature parameter for generation
        
    Returns:
        Configured ChatAnthropic instance
    """
    return ChatAnthropic(
        temperature=temperature, 
        model_name=model_name,
        timeout=600,  # 10 minutes timeout
        stop=None     # No custom stop tokens
    )

def create_messages(system_prompt: str, user_prompt: str) -> List:
    """Creates a standard message sequence for LLM invocation.
    
    Args:
        system_prompt: The system prompt text
        user_prompt: The user prompt text
        
    Returns:
        List of message objects
    """
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]

async def structured_llm_call(output_type: Type[T], messages: List, 
                             model_name: str = DEFAULT_MODEL, temperature: float = 0.7) -> T:
    """Makes a structured LLM call with retry logic and proper error handling."""
    llm = get_llm(model_name=model_name, temperature=temperature)
    structured_llm: Runnable = llm.with_structured_output(output_type) # Type hint for clarity

    # --- Add Retry Logic ---
    # Define exceptions to retry on (adjust based on the LLM provider)
    retry_exceptions = (
        APIError,        # General Anthropic API errors
        RateLimitError,  # Anthropic rate limit errors
        httpx.TimeoutException, # Network timeouts (if using httpx internally)
        # OutputParserException, # Optionally retry on parsing errors (use with caution)
        # Add other transient error types specific to your LLM/networking stack
    )

    # Configure the retry mechanism
    wait_strategy = wait_exponential(multiplier=1, min=1, max=10)
    structured_llm_with_retry = structured_llm.with_retry(
        stop_after_attempt=3,  # Retry up to 2 times (3 attempts total)
    )
    # --- End Retry Logic ---

    try:
        # Use the chain with retry logic
        result = await structured_llm_with_retry.ainvoke(messages)
        return cast(T, result)
    except retry_exceptions as e:
        # If retries fail, wrap the final error
        raise ConnectionError(f"LLM call failed after multiple retries: {e}") from e
    except OutputParserException as e:
        # Handle parsing errors specifically if not retrying them
        raise OutputParserException(f"Failed to parse LLM output: {e}") from e
    except ValueError as e:
        # Catch validation errors (these likely shouldn't be retried)
         raise ValueError(f"Validation failed for LLM output: {e}") from e
    except Exception as e:
        # Catch any other unexpected errors
        raise RuntimeError(f"An unexpected error occurred during LLM call: {e}") from e

def create_error_response(error: Exception, context: str) -> Dict[str, Any]:
    """Creates a standardized error response.
    
    Args:
        error: The exception that occurred
        context: Context for the error
        
    Returns:
        Standard error response dictionary
    """
    error_detail = f"{context} failed: {str(error)}"
    print(f"   Error: {error_detail}")
    return {"status": "error", "error_details": error_detail}

# --- Node Implementations ---

async def define_narrative_arc(state: GenerationState) -> Dict[str, Any]:
    """Node: Generates the high-level story outline using an LLM."""
    print("---NODE: Define Narrative Arc---")
    try:
        park_name = state.park_name
        research = state.research_content
        
        # Use prompts from content_prompts.py
        system_prompt = prompts.DEFINE_NARRATIVE_ARC_SYSTEM
        user_prompt = prompts.DEFINE_NARRATIVE_ARC_USER.format(
            park_name=park_name,
            research=research
        )
        
        messages = create_messages(system_prompt, user_prompt)

        print(f"   Invoking LLM for narrative arc for {park_name}...")
        story_outline_result: StoryOutline = await structured_llm_call(StoryOutline, messages)
        print(f"   Narrative arc generated.")
        
        return {"story_outline": story_outline_result, "status": "structuring_chapters"}

    except Exception as e:
        return create_error_response(e, "Narrative Arc generation")


async def structure_chapters(state: GenerationState) -> Dict[str, Any]:
    """Node: Breaks the story outline into chapter definitions using an LLM."""
    print("---NODE: Structure Chapters---")
    try:
        story_outline = state.story_outline
        research = state.research_content

        if not story_outline or not research:
             return {"status": "error", "error_details": "Missing story outline or research for chapter structuring."}

        # Use prompts from content_prompts.py
        system_prompt = prompts.STRUCTURE_CHAPTERS_SYSTEM.format(
            target_page_count=TARGET_PAGE_COUNT
        )
        user_prompt = prompts.STRUCTURE_CHAPTERS_USER.format(
            narrative_flow=story_outline.narrative_flow,
            key_themes=', '.join(story_outline.key_themes),
            research=research,
            target_page_count=TARGET_PAGE_COUNT
        )

        messages = create_messages(system_prompt, user_prompt)

        print(f"   Invoking LLM for chapter structure...")
        # Improved type hint clarity
        chapter_defs_wrapper: ChapterDefinitions = await structured_llm_call(ChapterDefinitions, messages)
        chapter_defs_result: List[ChapterDefinition] = chapter_defs_wrapper.chapters
        print(f"   Chapter structure generated.")

        # Validation
        if not isinstance(chapter_defs_result, list) or not all(isinstance(c, ChapterDefinition) for c in chapter_defs_result):
             raise ValueError("LLM did not return a valid list of ChapterDefinitions.")
             
        calculated_pages = sum(ch.page_count for ch in chapter_defs_result)
        if calculated_pages != TARGET_PAGE_COUNT:
            # Consider adding retry logic here if this validation fails often
            raise ValueError(f"LLM generated chapters totaling {calculated_pages} pages, expected {TARGET_PAGE_COUNT}.")
            
        # Renumber chapters sequentially just in case LLM didn't
        for i, chapter in enumerate(chapter_defs_result):
            chapter.chapter_number = i + 1

        return {"chapter_definitions": chapter_defs_result, "status": "generating_concepts"}

    except Exception as e:
        return create_error_response(e, "Chapter Structuring")


async def generate_page_concepts(state: GenerationState) -> Dict[str, Any]:
    """Node: Generates specific concepts for each page based on chapters using an LLM."""
    print("---NODE: Generate Page Concepts---")
    try:
        chapter_definitions = state.chapter_definitions
        research = state.research_content
        park_name = state.park_name  # Make sure to get the park_name from state

        if not chapter_definitions or not research:
            return {"status": "error", "error_details": "Missing chapter definitions or research for concept generation."}

        all_concepts: List[PageConcept] = []
        page_num_counter = 1

        for chapter in chapter_definitions:
            print(f"   Generating concepts for Chapter {chapter.chapter_number}: {chapter.theme}...")
            
            # Use prompts from content_prompts.py
            system_prompt = prompts.GENERATE_PAGE_CONCEPTS_SYSTEM
            # Ensure research context is handled appropriately if very large
            user_prompt = prompts.GENERATE_PAGE_CONCEPTS_USER.format(
                chapter_theme=chapter.theme,
                key_elements=', '.join(chapter.key_elements),
                page_count=chapter.page_count,
                research=research,  # Pass full research, LLM prompt guides focus
                park_name=park_name  # Add this parameter
            )

            messages = create_messages(system_prompt, user_prompt)

            # Generate concepts for one chapter
            page_concepts_wrapper: PageConceptCollection = await structured_llm_call(PageConceptCollection, messages)
            chapter_concepts_result: List[PageConcept] = page_concepts_wrapper.concepts

            if not isinstance(chapter_concepts_result, list) or len(chapter_concepts_result) != chapter.page_count:
                raise ValueError(f"LLM did not return the expected {chapter.page_count} concepts for chapter {chapter.chapter_number}.")

            # Assign page and chapter numbers
            for concept in chapter_concepts_result:
                concept.page_number = page_num_counter
                concept.chapter_number = chapter.chapter_number
                all_concepts.append(concept)
                page_num_counter += 1
            
            print(f"   Concepts generated for Chapter {chapter.chapter_number}.")

        # Final validation
        if len(all_concepts) != TARGET_PAGE_COUNT:
             raise ValueError(f"Total concepts generated ({len(all_concepts)}) does not match target ({TARGET_PAGE_COUNT}).")

        return {"page_concepts": all_concepts, "status": "generating_pages"}

    except Exception as e:
        return create_error_response(e, "Page Concept Generation")


async def generate_single_page_content(item: Dict[str, Any], config: Any) -> Dict[str, Page]:
    """
    Node Logic (for mapping): Generates text and illustration description for one page using an LLM.
    Expected input item: {'page_concept': PageConcept, 'research_content': str, 'park_name': str}
    """
    page_concept: PageConcept = item['page_concept']
    research_content: str = item['research_content']
    park_name: str = item['park_name']  # Add this line to get park_name from the item
    
    # Ensure page_number exists and is an int before using
    page_number = page_concept.page_number if page_concept.page_number is not None else -1 
    if page_number == -1:
         # Handle error: page number missing from concept
         print("   Error: Page concept missing page number.")
         error_page = Page(page_number=page_number, illustration_description="Error: Missing page number", text="Error generating content")
         return {"generated_page": error_page}

    print(f"---NODE (Map Item): Generate Page {page_number} ---") 
    
    try:
        # Use prompts from content_prompts.py
        system_prompt = prompts.GENERATE_SINGLE_PAGE_SYSTEM
        user_prompt = prompts.GENERATE_SINGLE_PAGE_USER.format(
            page_number=page_number,
            subject=page_concept.subject,
            core_idea=page_concept.core_idea,
            research_content=research_content,
            park_name=park_name  # Add this parameter
        )

        messages = create_messages(system_prompt, user_prompt)
        
        print(f"   Invoking LLM for page {page_number}...")
        page_result: Page = await structured_llm_call(Page, messages)
        print(f"   Content generated for page {page_number}.")

        # Validation and page number assignment
        if not isinstance(page_result, Page):
            raise ValueError("LLM did not return a valid Page object.")
            
        page_result.page_number = page_number # Ensure page number is set

        # Check illustration description starts with subject - RAISE ERROR if not compliant
        if not page_result.illustration_description.startswith(page_concept.subject):
            # Consider adding retry logic here
            raise ValueError(f"Page {page_number} illustration description validation failed: Does not start with subject '{page_concept.subject}'.")

        return {"generated_page": page_result}

    except Exception as e:
        print(f"   Error generating page {page_number}: {str(e)}")
        # Ensure error page has the correct page number
        error_page = Page(page_number=page_number, illustration_description=f"Error: {e}", text="Error generating content")
        return {"generated_page": error_page}


async def generate_all_pages(state: GenerationState) -> Dict[str, Any]:
    """Node: Coordinates the generation of all page content with limited concurrency."""
    print("---NODE: Generate All Pages---")
    try:
        page_concepts = state.page_concepts
        research_content = state.research_content
        park_name = state.park_name  # Get park_name from state

        if not page_concepts or not research_content:
            return {"status": "error", "error_details": "Missing page concepts or research for page generation."}

        # Prepare inputs for processing
        map_inputs = [
            {
                "page_concept": concept, 
                "research_content": research_content,
                "park_name": park_name  # Include park_name in the input
            }
            for concept in page_concepts
        ]
        
        # TODO: Make batch_size configurable (e.g., via state, config, env var)
        batch_size = 2 
        print(f"   Starting generation of {len(map_inputs)} pages with max {batch_size} concurrent requests...")
        
        # Process in batches to avoid rate limits
        generated_pages = []
        total_batches = (len(map_inputs) + batch_size - 1) // batch_size
        
        for i in range(0, len(map_inputs), batch_size):
            batch = map_inputs[i:i+batch_size]
            batch_num = i // batch_size + 1
            print(f"   Processing batch {batch_num}/{total_batches}...")
            
            # Pass config=None for now, update if needed
            batch_tasks = [generate_single_page_content(item, None) for item in batch] 
            batch_results = await asyncio.gather(*batch_tasks)
            
            # Extract the generated page from each result dictionary
            batch_pages = [result["generated_page"] for result in batch_results if "generated_page" in result]
            generated_pages.extend(batch_pages)
        
        print(f"   Completed generation of {len(generated_pages)} pages.")
        
        return {"generated_pages": generated_pages, "status": "aggregating_pages"}
        
    except Exception as e:
        return create_error_response(e, "Page Generation")


async def aggregate_generated_pages(state: GenerationState) -> Dict[str, Any]:
    """Node: Collects results from the page generation map, validates, and sorts."""
    print("---NODE: Aggregate Generated Pages---")
    
    generated_pages_raw: List[Page] = state.generated_pages
    
    if not generated_pages_raw:
        return {"status": "error", "error_details": "No pages were aggregated from generation step."}

    # Filter out any error pages (identified by the specific error text)
    successful_pages = [p for p in generated_pages_raw if p and not p.text.startswith("Error generating content")]
    failed_pages = [p for p in generated_pages_raw if not p or p.text.startswith("Error generating content")]
    failed_count = len(failed_pages)

    if failed_count > 0:
         failed_page_numbers = [p.page_number for p in failed_pages if p]
         error_detail = f"{failed_count} page(s) failed generation (Pages: {failed_page_numbers})."
         print(f"   Error: {error_detail}")
         # Optionally include more detail from failed_pages[0].illustration_description if needed
         return {"status": "error", "error_details": error_detail}

    # Use imported TARGET_PAGE_COUNT
    if len(successful_pages) != TARGET_PAGE_COUNT:
        error_detail = f"Expected {TARGET_PAGE_COUNT} successful pages, but aggregated {len(successful_pages)}."
        print(f"   Error: {error_detail}")
        return {"status": "error", "error_details": error_detail}

    # Sort pages by page_number, ensuring page_number is not None
    successful_pages.sort(key=lambda p: int(p.page_number if p.page_number is not None else -1))
    
    print(f"   Successfully aggregated and validated {len(successful_pages)} pages.")
    return {"generated_pages": successful_pages, "status": "generating_covers"}


async def generate_cover(
    park_name: str, 
    research_content: str, 
    is_front: bool = True, 
    page_number: int = 0,
    model_name: str = DEFAULT_MODEL # Allow overriding model if needed
) -> Page:
    """Helper function to generate a cover (front or back).
    
    Args:
        park_name: Name of the national park
        research_content: Research content about the park
        is_front: Whether this is the front cover (True) or back cover (False)
        page_number: Page number to assign to the cover
        model_name: Model to use for generation
        
    Returns:
        Generated Page object for the cover
    """
    cover_type = "FRONT" if is_front else "BACK"
    exact_text = f"{park_name} National Park" if is_front else None
    
    # Use prompts from content_prompts.py
    system_prompt = prompts.GENERATE_COVER_SYSTEM.format(
        cover_type=cover_type,
        page_number=page_number,
        is_front=is_front # Pass boolean for potential conditional logic in prompt
    )
    user_prompt = prompts.GENERATE_COVER_USER.format(
        park_name=park_name,
        research_content=research_content,
        cover_type=cover_type.lower(),
        page_number_info=f" for page {page_number}" if not is_front else "",
        exact_text_instruction=f"The text must be exactly '{exact_text}'" if exact_text else ""
    )
    
    messages = create_messages(system_prompt, user_prompt)
    print(f"   Invoking LLM for {cover_type.lower()} cover...")
    
    # Pass model_name explicitly if needed, otherwise uses imported default
    cover_result: Page = await structured_llm_call(Page, messages, model_name=model_name) 
    cover_result.page_number = page_number # Ensure page number is set
    
    # Validate front cover text
    if is_front and cover_result.text != exact_text and exact_text is not None:
        print(f"Warning: Front cover text mismatch ('{cover_result.text}' vs '{exact_text}'). Correcting.")
        cover_result.text = exact_text
        
    print(f"   {cover_type.capitalize()} cover generated.")
    return cover_result


async def generate_covers(state: GenerationState) -> Dict[str, Any]:
    """Node: Generates the front and back covers using an LLM."""
    print("---NODE: Generate Covers---")
    try:
        park_name = state.park_name
        research_content = state.research_content
        # Use imported TARGET_PAGE_COUNT
        target_back_cover_page_num = TARGET_PAGE_COUNT + 1 

        # Generate both covers concurrently
        # Consider passing configured model name from state/config if needed
        front_cover_task = generate_cover(
            park_name, 
            research_content, 
            is_front=True, 
            page_number=0
            # model_name=state.config.get('model_name', DEFAULT_MODEL) # Example
        )
        
        back_cover_task = generate_cover(
            park_name, 
            research_content, 
            is_front=False, 
            page_number=target_back_cover_page_num
            # model_name=state.config.get('model_name', DEFAULT_MODEL) # Example
        )
        
        front_cover_result, back_cover_result = await asyncio.gather(
            front_cover_task, back_cover_task
        )

        # Basic validation
        if not isinstance(front_cover_result, Page) or not isinstance(back_cover_result, Page):
             raise ValueError("Cover generation did not return valid Page objects.")

        return {
            "front_cover": front_cover_result, 
            "back_cover": back_cover_result, 
            "status": "assembling"
        }

    except Exception as e:
        return create_error_response(e, "Cover Generation")


async def assemble_book(state: GenerationState) -> Dict[str, Any]:
    """Node: Assembles the final KidsBook object."""
    print("---NODE: Assemble Book---")
    try:
        park_name = state.park_name
        front_cover = state.front_cover
        generated_pages = state.generated_pages # Assumed sorted and validated by aggregate step
        back_cover = state.back_cover

        # Validation of inputs (using imported TARGET_PAGE_COUNT)
        if not park_name:
            raise ValueError("Missing park_name")
        if not isinstance(front_cover, Page) or front_cover.page_number != 0:
            raise ValueError("Invalid or missing front_cover (requires Page object with page_number 0)")
        if not isinstance(generated_pages, list) or len(generated_pages) != TARGET_PAGE_COUNT:
             raise ValueError(f"Invalid or missing content pages (expected {TARGET_PAGE_COUNT} validated pages, found {len(generated_pages or [])})")
        # Use imported TARGET_PAGE_COUNT for back cover check
        if not isinstance(back_cover, Page) or back_cover.page_number != TARGET_PAGE_COUNT + 1:
             raise ValueError(f"Invalid or missing back_cover (requires Page object with page_number {TARGET_PAGE_COUNT + 1})")
        
        # This check might be redundant if aggregate_generated_pages guarantees list of Pages
        if not all(isinstance(p, Page) for p in generated_pages):
            raise ValueError("Content pages list contains non-Page objects.")

        # Create the final book object
        final_book = KidsBook(
            park_name=park_name,
            front_cover=front_cover,
            pages=generated_pages, # Already sorted
            back_cover=back_cover
        )
        
        print(f"   Successfully assembled book for {park_name}")
        return {"final_book": final_book, "status": "completed"} 

    except Exception as e:
        return create_error_response(e, "Book Assembly")
