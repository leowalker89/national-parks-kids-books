from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel, Field
from typing import List

# Import the necessary Pydantic models from the LangGraph state definitions
# Adjust the import path if necessary based on your project structure
from ..book_content_graph.content_states import (
    StoryOutline,
    ChapterDefinition,
    PageConcept,
    Page,
    KidsBook,
)

# Define Pydantic models for the structured outputs expected by specific tasks
# These match the 'expected_output' descriptions in tasks.yaml
class PlanningOutput(BaseModel):
    """Structure for the output of the planning_task."""
    story_outline: StoryOutline = Field(..., description="The overall narrative structure.")
    chapter_definitions: List[ChapterDefinition] = Field(..., description="Breakdown of the book into chapters.")
    page_concepts: List[PageConcept] = Field(..., description="Specific concepts for each content page.")

class CoverDesignOutput(BaseModel):
    """Structure for the output of the cover_design_task."""
    front_cover: Page = Field(..., description="Concept for the front cover (page 0).")
    back_cover: Page = Field(..., description="Concept for the back cover (page 11).")

@CrewBase
class ContentCreationCrew:
    """
    Crew responsible for generating the text content and illustration concepts
    for a children's board book about a National Park.
    """
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def book_planner(self) -> Agent:
        """Agent responsible for planning the book structure."""
        return Agent(
            config=self.agents_config["book_planner"],
            verbose=True # Or set based on global config/preference
        )

    @agent
    def cover_designer(self) -> Agent:
        """Agent responsible for designing cover concepts."""
        return Agent(
            config=self.agents_config["cover_designer"],
            verbose=True
        )

    @agent
    def content_writer(self) -> Agent:
        """Agent responsible for writing page content and assembling the book."""
        return Agent(
            config=self.agents_config["content_writer"],
            verbose=True
        )

    @task
    def planning_task(self) -> Task:
        """Task for analyzing research and creating the book plan."""
        return Task(
            config=self.tasks_config["planning_task"],
            agent=self.book_planner(),
            output_pydantic=PlanningOutput
        )

    @task
    def cover_design_task(self) -> Task:
        """Task for designing the front and back cover concepts."""
        return Task(
            config=self.tasks_config["cover_design_task"],
            agent=self.cover_designer(),
            output_pydantic=CoverDesignOutput
        )

    @task
    def content_writing_task(self) -> Task:
        """Task for writing page content and assembling the final book JSON."""
        return Task(
            config=self.tasks_config["content_writing_task"],
            agent=self.content_writer(),
            context=[self.planning_task(), self.cover_design_task()],
            # The task specifies output_file, but we can also parse the final
            # JSON output into the KidsBook model if the agent returns it directly.
            output_pydantic=KidsBook
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Content Creation Crew"""
        return Crew(
            agents=self.agents,  # Uses agents defined with @agent
            tasks=self.tasks,    # Uses tasks defined with @task
            process=Process.sequential,
            verbose=2 # Set desired verbosity (e.g., 1 for basic logs, 2 for detailed)
            # Memory configuration can be added here if needed
            # memory=True
        )
