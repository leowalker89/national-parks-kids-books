import asyncio
import operator
from typing import Dict, Any, List
from pprint import pprint

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver # For potential state saving
from langchain_core.runnables import RunnableConfig
from langsmith import traceable

# Import the state definition and node functions
from .content_states import GenerationState
from . import content_nodes as nodes

# --- Graph Definition ---

# Build the StateGraph
workflow = StateGraph(GenerationState)

# Add nodes to the graph
workflow.add_node("define_narrative_arc", nodes.define_narrative_arc)
workflow.add_node("structure_chapters", nodes.structure_chapters)
workflow.add_node("generate_page_concepts", nodes.generate_page_concepts)
workflow.add_node("generate_all_pages", nodes.generate_all_pages)
workflow.add_node("aggregate_generated_pages", nodes.aggregate_generated_pages)
workflow.add_node("generate_covers", nodes.generate_covers)
workflow.add_node("assemble_book", nodes.assemble_book)

# Set the entry point
workflow.set_entry_point("define_narrative_arc")

# Add sequential edges
workflow.add_edge("define_narrative_arc", "structure_chapters")
workflow.add_edge("structure_chapters", "generate_page_concepts")
workflow.add_edge("generate_page_concepts", "generate_all_pages")
workflow.add_edge("generate_all_pages", "aggregate_generated_pages")
workflow.add_edge("aggregate_generated_pages", "generate_covers")
workflow.add_edge("generate_covers", "assemble_book")

# The final node transitions to the end
workflow.add_edge("assemble_book", END)

# Compile the graph
# checkpointer = MemorySaver() # Optional: Add for state persistence/debugging
# graph = workflow.compile(checkpointer=checkpointer)
graph = workflow.compile()

# Add router node that checks for errors
def error_router(state):
    if state.get("status") == "error" or "error_details" in state:
        print(f"Error detected, ending graph execution: {state.get('error_details', 'Unknown error')}")
        return "error"
    return "next"

# Add conditional edges
workflow.add_conditional_edges(
    "define_narrative_arc",
    error_router,
    {
        "error": END,
        "next": "structure_chapters"
    }
)

# --- Example Usage ---
@traceable
async def run_graph(park_name: str, research_content: str):
    """Runs the content generation graph."""
    # Normalize park name (capitalize first letter of each word)
    park_name = ' '.join(word.capitalize() for word in park_name.split())
    
    print(f"\n--- Starting Graph for {park_name} National Park ---")
    initial_state = GenerationState(
        park_name=park_name,
        research_content=research_content,
        # No need to set initial status, first node runs anyway
    )
    
    # Configuration for the run
    config: RunnableConfig = {}

    final_state = None
    try:
        async for event in graph.astream(initial_state, config=config):
            # Process events if needed
            state_keys = list(event.keys())
            if state_keys:
                 last_state_key = state_keys[-1]
                 final_state = event[last_state_key] # Capture the state after each step

        print("\n--- Graph Execution Finished Successfully ---")

    except Exception as e:
        print("\n--- Graph Execution Failed ---")
        print(f"Error: {type(e).__name__} - {str(e)}")
        # final_state might hold the state *before* the error occurred
        if final_state:
            print("State before error:")
            pprint(final_state)  # It's already a dict
        final_state = None # Indicate failure

    # Check the outcome based on whether final_state is populated and has the book
    if final_state and "final_book" in final_state:
        book = final_state['final_book']
        print("\n--- Generated Book ---")
        print(f"Park: {book.park_name}")
        print(f"Front Cover Text: {book.front_cover.text}")
        print(f"Number of Pages: {len(book.pages)}")
        print(f"Page 1 Text: {book.pages[0].text if book.pages else 'N/A'}")
        print(f"Back Cover Text: {book.back_cover.text}")
        print("----------------------")
    elif final_state and final_state.get('status') != "completed":
        # This case might occur if the graph ended unexpectedly without error
        print("\nGraph finished in incomplete state:", final_state.get('status'))
        pprint(final_state)
    elif not final_state:
        print("\nExecution failed, no final book generated.")

    # At the end, return the final state
    return final_state


if __name__ == "__main__":
    # Example run
    park = "Rocky Mountain"
    research = """
    Rocky Mountain National Park in Colorado features majestic mountains, including Longs Peak.
    Alpine tundra ecosystems thrive above the treeline with unique wildflowers like alpine forget-me-nots.
    Wildlife includes elk often seen grazing in meadows, bighorn sheep navigating rocky slopes, and marmots sunning on rocks.
    Bear Lake offers scenic reflections of surrounding peaks. Trail Ridge Road is a famous high-altitude drive.
    The Colorado River originates in the park. Forests contain pine and fir trees.
    """
    
    asyncio.run(run_graph(park_name=park, research_content=research))

    # Example of an intentional error (e.g., if a node fails)
    # park_error = "Error Park"
    # research_error = "This research is faulty." # Simulate bad input if needed
    # asyncio.run(run_graph(park_name=park_error, research_content=research_error))
