"""
Park Research Script

This script researches a national park and saves the results to a markdown file.
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add the src directory to the path to allow importing from common
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.common.research import research_park


async def main() -> None:
    """Parse command line arguments and run the research script."""
    parser = argparse.ArgumentParser(description="Research a national park and save the results.")
    parser.add_argument("park_name", help="Name of the national park to research")
    
    args = parser.parse_args()
    park_name = args.park_name
    
    # Create normalized version of park name for directory purposes
    park_dir_name = park_name.lower().replace(" ", "_").replace("-", "_")
    
    # Define paths
    base_path = Path(__file__).parent.parent.parent / "parks"
    park_path = base_path / park_dir_name
    research_path = park_path / "research"
    
    # Create directories if they don't exist
    park_path.mkdir(exist_ok=True)
    research_path.mkdir(exist_ok=True)
    
    # Research the park
    print(f"Researching {park_name} National Park...")
    result = await research_park(park_name)
    
    if result["status"] == "error":
        print(f"Error: {result['error']}")
        sys.exit(1)
    
    # Save research file
    output_file = research_path / "research.md"
    
    with open(output_file, "w") as f:
        f.write(result["research_content"])
    
    print(f"Research saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main()) 