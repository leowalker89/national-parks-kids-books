"""
Generate book content using CrewAI flow.

This script takes a park name as input, loads the relevant research,
and triggers the CrewAI flow to generate book content with 18 pages.
"""

import sys
import os
import argparse
from pathlib import Path

# Add src to path when running directly
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import the CrewAI flow
from src.common.book_content_flow.content_crew_flow import kickoff_flow

def main():
    """Parse arguments and run the content generation flow."""
    parser = argparse.ArgumentParser(description="Generate book content using CrewAI flow")
    parser.add_argument("park_name", help="Name of the national park to create content for")
    
    args = parser.parse_args()
    park_name = args.park_name
    
    # Create normalized park name for file paths
    park_dir = park_name.lower().replace(" ", "_").replace("-", "_")
    
    # Path to research file
    research_path = Path(f"parks/{park_dir}/research/research.md")
    
    # Validate research file exists
    if not research_path.exists():
        print(f"Error: Research file not found at {research_path}")
        print("Please ensure the park directory and research file exist")
        sys.exit(1)
    
    # Load research content
    try:
        with open(research_path, "r", encoding="utf-8") as f:
            research_content = f.read()
        print(f"Successfully loaded research for {park_name}")
    except Exception as e:
        print(f"Error reading research file: {e}")
        sys.exit(1)
    
    # Run the flow with fixed page count of 18
    print(f"\nStarting CrewAI flow for {park_name} with 18 pages...")
    final_state = kickoff_flow(
        park_name=park_name,
        research_content=research_content,
        target_page_count=18
    )
    
    # Check result
    if final_state and final_state.final_book:
        print(f"\nSuccess! Generated book content for {park_name} with {len(final_state.final_book.pages)} pages")
        print(f"Output saved to: {final_state.output_path}")
    else:
        print("\nError: Failed to generate book content")
        sys.exit(1)

if __name__ == "__main__":
    main()
