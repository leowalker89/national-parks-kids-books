"""
Book Generation Script

This script generates a children's book for a national park using research data
and saves the results to JSON.
"""
import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add the src directory to the path to allow importing from common
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.common.book_content_graph.content_graph import run_graph


async def main() -> None:
    """Parse command line arguments and run the book generation script."""
    parser = argparse.ArgumentParser(description="Generate a children's book for a national park.")
    parser.add_argument("park_name", help="Name of the national park to create a book for")
    parser.add_argument("--model", help="Model to use for content generation", 
                      default="accounts/fireworks/models/llama-v3p3-70b-instruct")
                    # default="accounts/fireworks/models/deepseek-r1")
    parser.add_argument("--provider", help="Provider of the language model", 
                      default="fireworks")
    
    args = parser.parse_args()
    park_name = args.park_name
    model_name = args.model
    model_provider = args.provider
    
    # Create normalized version of park name for directory purposes
    park_dir_name = park_name.lower().replace(" ", "_").replace("-", "_")
    
    # Define paths
    base_path = Path(__file__).parent.parent.parent / "parks"
    park_path = base_path / park_dir_name
    research_path = park_path / "research" / "research.md"
    content_path = park_path / "content"
    
    # Check if paths exist
    if not park_path.exists():
        print(f"Error: Park directory not found at {park_path}")
        sys.exit(1)
        
    if not research_path.exists():
        print(f"Error: Research file not found at {research_path}")
        sys.exit(1)
    
    # Read research content
    try:
        with open(research_path, 'r') as f:
            research_content = f.read()
    except Exception as e:
        print(f"Error reading research file: {str(e)}")
        sys.exit(1)
    
    # Create content directory if it doesn't exist
    content_path.mkdir(exist_ok=True)
    
    # Generate book content
    print(f"Generating book content for {park_name} National Park...")
    final_state = await run_graph(park_name=park_name, research_content=research_content)
    
    if not final_state or 'final_book' not in final_state:
        print("Error: Failed to generate book content")
        sys.exit(1)
    
    # Save book content to JSON file
    book_content = final_state['final_book']
    output_file = content_path / "book_text.json"
    
    try:
        with open(output_file, "w") as f:
            # Use model_dump() for Pydantic v2 compatibility
            json.dump(book_content.model_dump(), f, indent=2)
    except Exception as e:
        print(f"Error saving book content: {str(e)}")
        sys.exit(1)
    
    print(f"Book content saved to {output_file}")
    print(f"Generated {len(book_content.pages)} pages for {park_name} National Park")
    
    # Print a sample of the first page to confirm generation worked
    first_page = book_content.pages[0]
    print("\nSample of the first page:")
    print(f"Page {first_page.page_number}")
    print(f"Text: {first_page.text}")
    print(f"Illustration (first 150 chars): {first_page.illustration_description[:150]}...")


if __name__ == "__main__":
    asyncio.run(main()) 