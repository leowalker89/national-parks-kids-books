# src/common/book_content_flow/content_flow.py

import os
import json
import traceback
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import sys
from pathlib import Path
from dotenv import load_dotenv
from opik import track, Opik
from opik.integrations.crewai import track_crewai

# Add src to path when running directly
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent.parent))

# Import necessary CrewAI components
from crewai import Agent
from crewai.flow import Flow, listen, start

# Import the necessary Pydantic models from the LangGraph state definitions
from src.common.book_content_graph.content_states import (
    StoryOutline,
    ChapterDefinition,
    PageConcept,
    Page,
    KidsBook,
    ChapterDefinitions,
    PageConceptCollection
)

# Import the prompts from content_prompts.py
from src.common.book_content_graph.content_prompts import (
    DEFINE_NARRATIVE_ARC_SYSTEM, DEFINE_NARRATIVE_ARC_USER,
    STRUCTURE_CHAPTERS_SYSTEM, STRUCTURE_CHAPTERS_USER,
    GENERATE_PAGE_CONCEPTS_SYSTEM, GENERATE_PAGE_CONCEPTS_USER
)

# Load environment variables
load_dotenv()

# Configure Opik client with more options
opik_client = Opik(
    project_name="national-parks-kids-books",
)

# Then use track_crewai with this client
track_crewai(project_name="national-parks-kids-books")

# --- Define Pydantic models for structured outputs needed within the flow ---
# These help ensure the LLM/Agent returns data in the correct format between steps

class PlanningOutput(BaseModel):
    """Structure for the output of the planning step."""
    story_outline: StoryOutline = Field(..., description="The overall narrative structure.")
    chapter_definitions: List[ChapterDefinition] = Field(..., description="Breakdown of the book into chapters.")
    page_concepts: List[PageConcept] = Field(..., description="Specific concepts for each content page.")

class CoverDesignOutput(BaseModel):
    """Structure for the output of the cover design step."""
    front_cover: Page = Field(..., description="Concept for the front cover (page 0).")
    back_cover: Page = Field(..., description="Concept for the back cover (last page of the book).")

# --- Define the Flow State ---

class BookGenerationState(BaseModel):
    """Holds the state for the book generation flow."""
    # Inputs
    park_name: str = ""
    research: str = ""
    park_name_lowercase: str = "" # For file path construction
    target_page_count: int = 10   # Default to 10 but can be overridden

    # Intermediate/Planning outputs
    story_outline: Optional[StoryOutline] = None
    chapter_definitions: Optional[List[ChapterDefinition]] = None
    page_concepts: Optional[List[PageConcept]] = None
    front_cover: Optional[Page] = None
    back_cover: Optional[Page] = None

    # Final Output
    final_book: Optional[KidsBook] = None
    output_path: str = "" # Store the final output path

# --- Define the Flow ---

class BookGenerationFlow(Flow[BookGenerationState]):
    """Flow to generate children's book content using CrewAI agents."""

    @start()
    @track(
        project_name="national-parks-kids-books", 
    )
    def initialize_generation(self):
        """Initializes the flow with park name and research."""
        print(f"\n--- Starting Book Generation Flow for: {self.state.park_name} ---")
        # Derive lowercase name for paths
        self.state.park_name_lowercase = self.state.park_name.lower().replace(" ", "_")
        # Define the output path using the lowercase name
        self.state.output_path = f"parks/{self.state.park_name_lowercase}/content/book_crewai_flow.json"
        print(f"   Input Research Loaded. Output path set to: {self.state.output_path}")
        # No agent needed here, just setting up state
        return self.state # Pass the whole state along

    @listen(initialize_generation)
    @track(project_name="national-parks-kids-books")
    def plan_book_structure(self):
        """Uses the BookPlannerAgent to create the story outline, chapters, and page concepts."""
        print("--- Step: Planning Book Structure ---")

        planner_agent = Agent(
            role="Children's Book Architect",
            goal=f"Analyze provided research for {self.state.park_name} and devise a complete structural plan for a {self.state.target_page_count}-page toddler's board book (ages 0-5).",
            backstory="You are an expert in early childhood development and narrative structure, skilled at transforming factual research into engaging, age-appropriate book outlines.",
            llm="gpt-4.1",
            verbose=True,
            allow_delegation=False
        )

        # First create the narrative arc/outline
        system_prompt = DEFINE_NARRATIVE_ARC_SYSTEM
        user_prompt = DEFINE_NARRATIVE_ARC_USER.format(
            park_name=self.state.park_name,
            research=self.state.research
        )
        
        # Execute the agent directly to get story outline
        print("   Invoking Planner Agent for story outline...")
        try:
            result = planner_agent.kickoff(user_prompt, system_prompt=system_prompt, response_format=StoryOutline)
            self.state.story_outline = result.pydantic
            
            # Now structure into chapters using the outline
            system_prompt = STRUCTURE_CHAPTERS_SYSTEM.format(
                target_page_count=self.state.target_page_count
            )
            user_prompt = STRUCTURE_CHAPTERS_USER.format(
                narrative_flow=self.state.story_outline.narrative_flow,
                key_themes=', '.join(self.state.story_outline.key_themes),
                research=self.state.research,
                target_page_count=self.state.target_page_count
            )
            
            # Get the chapter structure
            result = planner_agent.kickoff(user_prompt, system_prompt=system_prompt, response_format=ChapterDefinitions)
            self.state.chapter_definitions = result.pydantic.chapters
            
            # Now generate page concepts based on chapters
            self.state.page_concepts = []
            page_num = 1
            
            for chapter in self.state.chapter_definitions:
                # Generate concepts for this chapter
                system_prompt = GENERATE_PAGE_CONCEPTS_SYSTEM
                user_prompt = GENERATE_PAGE_CONCEPTS_USER.format(
                    chapter_theme=chapter.theme,
                    key_elements=', '.join(chapter.key_elements),
                    page_count=chapter.page_count,
                    research=self.state.research,
                    park_name=self.state.park_name
                )
                
                result = planner_agent.kickoff(user_prompt, system_prompt=system_prompt, response_format=PageConceptCollection)
                chapter_concepts = result.pydantic.concepts
                
                # Assign page numbers
                for concept in chapter_concepts:
                    concept.page_number = page_num
                    concept.chapter_number = chapter.chapter_number
                    self.state.page_concepts.append(concept)
                    page_num += 1
                    
            print("   Planning complete with outline, chapters, and page concepts.")
        except Exception as e:
            print(f"   Error in planning: {e}")
            # Create fallback structure with flexible page count
            self.state.story_outline = StoryOutline(
                narrative_flow=f"Simple exploration of {self.state.park_name}", 
                key_themes=["Nature", "Discovery"]
            )
            self.state.chapter_definitions = [
                ChapterDefinition(
                    chapter_number=1, 
                    theme="Park Introduction", 
                    key_elements=["Park features"], 
                    page_count=self.state.target_page_count
                )
            ]
            self.state.page_concepts = [
                PageConcept(
                    page_number=i+1, 
                    chapter_number=1, 
                    subject=f"Nature element {i+1}", 
                    core_idea=f"Simple fact about {self.state.park_name}"
                ) for i in range(self.state.target_page_count)
            ]
            print("   Using fallback planning structure due to error.")
        
        return self.state # Pass state to next step

    @listen(plan_book_structure)
    @track(project_name="national-parks-kids-books")
    def design_covers(self):
        """Uses the CoverDesignerAgent to create front and back cover concepts."""
        print("--- Step: Designing Covers ---")
        designer_agent = Agent(
            role="Children's Book Cover Concept Creator",
            goal=f"Design compelling text and detailed illustration descriptions for the front cover (page 0) and back cover (page {self.state.target_page_count+1}) for the {self.state.park_name} book, adhering to toddler-focused aesthetics and specific constraints (like exact title text).",
            backstory="You are a specialist in creating eye-catching cover concepts for the 0-5 age group, understanding how to use simple visuals, bold colors, and minimal text effectively. Your focus is solely on nature, capturing the essence of the park while ensuring the front cover text is exactly '{self.state.park_name} National Park'.",
            llm="gpt-4.1",
            verbose=True,
            allow_delegation=False
        )

        cover_prompt = f"""
Using the provided research for {self.state.park_name} National Park, design the concepts for
the front cover (page 0) and back cover (page {self.state.target_page_count+1}) of the toddler's board book.
For each cover:
1. Create a detailed illustration description (30+ words) showcasing an iconic,
   simple, and vibrant natural scene appealing to ages 0-5. Focus on nature,
   exclude people.
2. Write the cover text. CRITICAL: The front cover text MUST be exactly
   "{self.state.park_name} National Park". The back cover text should be a very brief
   summary (<15 words).
Return the concepts structured according to the CoverDesignOutput Pydantic model.

Research Content:
{self.state.research}
"""
        
        # Execute the agent directly
        print("   Invoking Cover Designer Agent...")
        try:
            # Call the agent directly with the cover prompt
            result = designer_agent.kickoff(cover_prompt, response_format=CoverDesignOutput)
            
            # Extract the Pydantic result
            parsed_result = result.pydantic
            
            print("   Cover Designer Agent finished.")
            self.state.front_cover = parsed_result.front_cover
            self.state.back_cover = parsed_result.back_cover
            print("   State updated with cover designs.")
        except Exception as e:
            print(f"   Error in Cover Designer execution: {e}")
            # Fallback to default values in case of error
            self.state.front_cover = Page(
                page_number=0, 
                illustration_description=f"Default illustration for {self.state.park_name} front cover", 
                text=f"{self.state.park_name} National Park"
            )
            self.state.back_cover = Page(
                page_number=self.state.target_page_count+1, 
                illustration_description=f"Default illustration for {self.state.park_name} back cover", 
                text="Discover the wonders of nature."
            )
            print("   Using fallback cover designs due to error.")
        
        return self.state

    @listen(design_covers)
    @track(project_name="national-parks-kids-books")
    def write_and_assemble_book(self):
        """Uses the ContentWriterAgent to write page text/illustrations and assemble the final book."""
        print("--- Step: Writing Content and Assembling Book ---")

        # Ensure previous steps populated the state correctly
        if not self.state.page_concepts or not self.state.front_cover or not self.state.back_cover:
             print("   Error: Missing required state from previous steps (concepts or covers).")
             # TODO: Implement proper error handling for the flow
             return self.state # Or raise an exception to halt the flow

        writer_agent = Agent(
             role="Toddler's Book Author & Assembler",
             goal=f"Write extremely concise text (<12 words) and detailed illustration descriptions for each of the {self.state.target_page_count} content pages based on the planner's concepts for {self.state.park_name}. Assemble the final book structure including covers and content pages into a single JSON output conforming to the KidsBook model.",
             backstory="You are a master of ultra-simple, rhythmic language perfect for pre-readers (ages 0-5). You excel at providing clear, actionable descriptions for illustrators that strictly follow the provided page concepts (especially the illustration subject). Finally, you meticulously assemble all generated components (covers, content pages) into the final, complete book structure.",
             llm="gpt-4.1",
             verbose=True,
             allow_delegation=False
        )

        # Prepare context for the writer agent - pass concepts and covers explicitly in the prompt
        # Ensure components exist before trying to dump them
        page_concepts_str = json.dumps([pc.model_dump() for pc in self.state.page_concepts], indent=2) if self.state.page_concepts else "[]"
        front_cover_str = self.state.front_cover.model_dump_json(indent=2) if self.state.front_cover else "{}"
        back_cover_str = self.state.back_cover.model_dump_json(indent=2) if self.state.back_cover else "{}"

        writing_prompt = f"""
You need to generate the content for a {self.state.target_page_count}-page toddler's book about {self.state.park_name} and assemble the final book structure.

Here is the plan (page concepts):
{page_concepts_str}

Here is the front cover concept:
{front_cover_str}

Here is the back cover concept:
{back_cover_str}

Instructions:
1. For each of the {self.state.target_page_count} page concepts provided above, write the page text (extremely concise: max 10-12 simple words suitable for ages 0-5).
2. For each page concept, write a detailed illustration description (30+ words) that MUST start exactly with the page's specified 'subject'. Descriptions should guide an illustrator to create vibrant, simple, nature-focused visuals.
3. Assemble the final book content by combining the front cover, the {self.state.target_page_count} generated content pages (in order, with page numbers 1 through {self.state.target_page_count}), and the back cover into a single, complete structure.
Return the final assembled structure as JSON conforming to the KidsBook Pydantic model.
"""
        # Execute the agent directly
        print("   Invoking Content Writer Agent...")
        try:
            # Call the agent directly with the writing prompt
            result = writer_agent.kickoff(writing_prompt, response_format=KidsBook)
            
            # Extract the Pydantic result
            parsed_result = result.pydantic
            
            print("   Content Writer Agent finished.")
            self.state.final_book = parsed_result
            print("   State updated with final book.")

            # Save the final book JSON
            try:
                output_dir = os.path.dirname(self.state.output_path)
                os.makedirs(output_dir, exist_ok=True)
                with open(self.state.output_path, 'w') as f:
                    # Use model_dump_json for Pydantic v2+
                    f.write(self.state.final_book.model_dump_json(indent=2))
                print(f"   Final book JSON saved to: {self.state.output_path}")
            except Exception as e:
                print(f"   Error saving final book JSON: {e}")
        except Exception as e:
            print(f"   Error in Content Writer execution: {e}")
            # Create minimal book in case of error
            self.state.final_book = KidsBook(
                park_name=self.state.park_name,
                front_cover=self.state.front_cover,
                pages=[
                    Page(
                        page_number=i+1,
                        text=f"Simple text about {self.state.park_name} page {i+1}",
                        illustration_description=f"Basic illustration for page {i+1}"
                    ) for i in range(self.state.target_page_count)
                ],
                back_cover=self.state.back_cover
            )
            print("   Using fallback book content due to error.")
            
            # Try to save fallback content
            try:
                output_dir = os.path.dirname(self.state.output_path)
                os.makedirs(output_dir, exist_ok=True)
                with open(self.state.output_path, 'w') as f:
                    f.write(self.state.final_book.model_dump_json(indent=2))
                print(f"   Fallback book JSON saved to: {self.state.output_path}")
            except Exception as save_err:
                print(f"   Error saving fallback book JSON: {save_err}")

        return self.state # Flow ends after this step

# --- Kickoff Function ---
def kickoff_flow(park_name: str, research_content: str, target_page_count: int = 10):
    """Instantiates and runs the BookGenerationFlow."""
    
    
    
    # Create and configure the flow with the model specified in environment variable
    # The LLM will be determined by the OpenAI API key in the environment
    book_flow = BookGenerationFlow()
    
    # Create initial state with required inputs
    initial_state = {
        "park_name": park_name,
        "research": research_content,
        "target_page_count": target_page_count,
    }
    
    try:
        # Run the flow with initial state
        final_state = book_flow.kickoff(inputs=initial_state)

        print("\n--- Flow Execution Complete ---")
        # Ensure all traces are flushed to Opik
        Opik().flush()
        
        if final_state and final_state.final_book:
            print(f"Final Book generated for: {final_state.final_book.park_name}")
            # Option to print the JSON output for debugging
            # print(final_state.final_book.model_dump_json(indent=2))
        else:
            print("Flow did not complete successfully or final book not found in state.")
        return final_state
    except Exception as e:
        print(f"\n--- Flow Execution Error ---")
        print(f"An error occurred during flow execution: {e}")
        traceback.print_exc() # Print detailed traceback
        return None

# --- Plot Function (Optional) ---
def plot_flow():
    """Generates a visualization of the flow."""
    # Create a flow instance without kickoff
    book_flow = BookGenerationFlow()
    
    # Generate plot visualization
    try:
        book_flow.plot() # Saves flow.png by default
        print("\nFlow diagram saved to flow.png (requires graphviz python library and system install)")
    except ImportError:
        print("\nError: Could not plot flow. Please install graphviz: uv add graphviz")
    except Exception as e:
        print(f"\nCould not plot flow (ensure graphviz library/system package is installed): {e}")


if __name__ == "__main__":
    # --- Test the flow with Yosemite data ---
    target_park_name = "Yosemite"
    print(f"--- Preparing to run CrewAI Flow for: {target_park_name} ---")

    # Construct the path to the research file
    research_file_path = os.path.join(
        "parks",
        target_park_name.lower().replace(" ", "_"), # Ensure consistent path formatting
        "research",
        "research.md"
    )
    print(f"Attempting to load research from: {research_file_path}")

    try:
        # Load the research content from the specified file
        with open(research_file_path, 'r', encoding='utf-8') as f:
            park_research_content = f.read()
        print(f"Successfully loaded research for {target_park_name}.")

        # Run the flow with the loaded data
        print("\n--- Kicking off CrewAI Flow ---")
        final_state_result = kickoff_flow(
            park_name=target_park_name,
            research_content=park_research_content
        )

        # Optional: Check the final state result
        if final_state_result:
            print("\n--- Flow Kickoff Attempted ---")
            if final_state_result.final_book:
                print("Result: Successfully generated final book structure in state.")
            else:
                print("Result: Flow finished, but final_book was not found in the final state.")
        else:
            print("\nResult: kickoff_flow returned None, indicating an error during setup or execution.")

    except FileNotFoundError:
        print(f"ERROR: Research file not found at '{research_file_path}'.")
        print("Please ensure the file exists and the path is correct.")
    except Exception as e:
        print(f"An unexpected error occurred during the test run: {e}")
        traceback.print_exc()

    # --- Optional: Plotting ---
    # print("\nAttempting to plot the flow...")
    # plot_flow() # Uncomment if you want to generate the plot (requires graphviz)
    # --- End Optional Plotting ---
