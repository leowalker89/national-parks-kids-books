"""
Illustration Generation Script

This script generates illustrations for a children's book about a national park
using the content from the generated book_text.json file.
"""
import asyncio
import argparse
import json
import sys
import time
import random
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, TypedDict, cast

# Add the src directory to the path to allow importing from common
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.common.image_gen import generate_image
from src.common.constants import ILLUSTRATION_STYLE


class ImageParams(TypedDict, total=False):
    description: str
    park_name: str
    style_focus: str
    output_path: str
    is_cover: bool
    seed: Optional[int]


async def generate_illustration_for_page(
    park_name: str,
    page_number: int,
    description: str,
    output_dir: Path,
    style_focus: str = ILLUSTRATION_STYLE,
    retry_count: int = 2,
    retry_delay: int = 5,
    force_regenerate: bool = False,
    seed: Optional[int] = None,
    is_cover: bool = False
) -> Tuple[bool, str, Optional[int]]:
    """Generate an illustration for a specific page of the book."""
    # Determine output path and page label
    page_label = "front cover" if page_number == 0 else "back cover" if page_number == 11 else f"page {page_number}"
    
    if is_cover:
        output_path = output_dir / (f"front_cover.jpg" if page_number == 0 else "back_cover.jpg")
    else:
        output_path = output_dir / f"page_{page_number:02d}.jpg"
    
    # Skip if file exists and not forcing regeneration
    if output_path.exists() and not force_regenerate:
        print(f"Illustration for {page_label} already exists at {output_path} (skipping)")
        return True, "", seed
    
    # Try to generate the image with retries
    for attempt in range(retry_count + 1):
        if attempt > 0:
            print(f"Retry attempt {attempt}/{retry_count} for {page_label}...")
            time.sleep(retry_delay)
        
        # Log the seed if provided
        seed_message = f" with seed {seed}" if seed is not None else ""
        print(f"Generating illustration for {page_label}{seed_message}...")
        
        # Optional seed parameter
        image_params = {
            "description": description,
            "park_name": park_name,
            "style_focus": style_focus,
            "output_path": str(output_path),
            "is_cover": is_cover
        }
        
        # Only add seed if it's provided
        if seed is not None:
            image_params["seed"] = seed
        
        result = await generate_image(**image_params)  # type: ignore
        
        if result["status"] == "success":
            print(f"Illustration for {page_label} saved to {output_path}")
            return True, "", seed
        
        print(f"Error generating illustration for {page_label}: {result['error']}")
        if attempt == retry_count:
            return False, result["error"], seed
    
    return False, "Max retries exceeded", seed


def get_page_from_book(book_content: Dict[str, Any], page_number: int) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Get a page from the book content by its page number."""
    if page_number == 0 and "front_cover" in book_content:
        return book_content["front_cover"], True
    elif page_number == 11 and "back_cover" in book_content:
        return book_content["back_cover"], True
    else:
        page = next((p for p in book_content["pages"] if p["page_number"] == page_number), None)
        return page, False


async def process_page(
    park_name: str,
    page: Dict[str, Any],
    is_cover: bool,
    images_path: Path,
    style_focus: str,
    retry_count: int,
    retry_delay: int,
    force_regenerate: bool,
    seed: Optional[int],
    rotating_seeds: bool
) -> Optional[Dict[str, Any]]:
    """Process a single page and return failure info if it fails."""
    # Generate a new random seed if rotating seeds
    current_seed = random.randint(1, 1000000) if rotating_seeds else seed
    
    success, error, _ = await generate_illustration_for_page(
        park_name=park_name,
        page_number=page["page_number"],
        description=page["illustration_description"],
        output_dir=images_path,
        style_focus=style_focus,
        retry_count=retry_count,
        retry_delay=retry_delay,
        force_regenerate=force_regenerate,
        seed=current_seed,
        is_cover=is_cover
    )
    
    if not success:
        return {
            "page_number": page["page_number"],
            "error": error,
            "description": page["illustration_description"]
        }
    return None


async def main() -> None:
    """Parse command line arguments and run the illustration generation script."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Generate illustrations for a children's book.")
    parser.add_argument("park_name", help="Name of the national park")
    parser.add_argument("--style", help="Custom style override for the illustrations (optional)")
    parser.add_argument("--page", type=int, help="Generate only a specific page (optional)")
    parser.add_argument("--retry-failed", action="store_true", help="Only retry pages that failed in previous runs")
    parser.add_argument("--retry-count", type=int, default=2, help="Number of retry attempts (default: 2)")
    parser.add_argument("--retry-delay", type=int, default=5, help="Seconds to wait between retries (default: 5)")
    parser.add_argument("--force", action="store_true", help="Force regeneration of existing images")
    
    # New seed options
    seed_group = parser.add_mutually_exclusive_group()
    seed_group.add_argument("--seed", type=int, help="Specific seed for image generation (optional)")
    seed_group.add_argument("--rotating-seeds", action="store_true", help="Use a different random seed for each illustration")
    
    parser.add_argument("--skip-covers", action="store_true", help="Skip generating front and back covers")
    
    args = parser.parse_args()
    
    # Set up paths and options
    park_name = args.park_name
    park_dir_name = park_name.lower().replace(" ", "_").replace("-", "_")
    style_focus = args.style if args.style else ILLUSTRATION_STYLE
    
    base_path = Path(__file__).parent.parent.parent / "parks"
    park_path = base_path / park_dir_name
    content_path = park_path / "content"
    book_path = content_path / "book_text.json"
    images_path = park_path / "images"
    failed_pages_path = content_path / "failed_illustrations.json"
    
    # Validate book_text.json exists
    if not book_path.exists():
        print(f"Error: Book content file not found at {book_path}")
        print("Please generate book text content first using generate_book_text.py")
        sys.exit(1)
    
    # Read book content
    try:
        with open(book_path, 'r') as f:
            book_content = json.load(f)
    except Exception as e:
        print(f"Error reading book content: {str(e)}")
        sys.exit(1)
    
    # Create images directory
    images_path.mkdir(exist_ok=True)
    
    # Load failed pages for retry mode
    failed_pages = []
    if args.retry_failed and failed_pages_path.exists():
        try:
            with open(failed_pages_path, 'r') as f:
                failed_pages = json.load(f)
            print(f"Loaded {len(failed_pages)} failed pages from previous run")
        except Exception as e:
            print(f"Error loading failed pages: {str(e)}")
            args.retry_failed = False
    
    # Track failures in this run
    current_failures = []
    
    # SINGLE PAGE MODE
    if args.page is not None:
        page, is_cover = get_page_from_book(book_content, args.page)
        if not page:
            print(f"Error: No page found with page number {args.page}")
            sys.exit(1)
        
        failure = await process_page(
            park_name, page, is_cover, images_path, style_focus, 
            args.retry_count, args.retry_delay, args.force, args.seed,
            args.rotating_seeds
        )
        if failure:
            current_failures.append(failure)
    
    # BATCH MODE
    else:
        # Process pages based on mode (retry or all)
        if args.retry_failed:
            # Process only previously failed pages
            for failed_page in failed_pages:
                page, is_cover = get_page_from_book(book_content, failed_page["page_number"])
                if page:
                    failure = await process_page(
                        park_name, page, is_cover, images_path, style_focus,
                        args.retry_count, args.retry_delay, args.force, args.seed,
                        args.rotating_seeds
                    )
                    if failure:
                        current_failures.append(failure)
                else:
                    print(f"Warning: Failed page {failed_page['page_number']} not found in book content")
        else:
            # Process all content - front cover
            if not args.skip_covers and "front_cover" in book_content:
                failure = await process_page(
                    park_name, book_content["front_cover"], True, images_path, style_focus,
                    args.retry_count, args.retry_delay, args.force, args.seed,
                    args.rotating_seeds
                )
                if failure:
                    current_failures.append(failure)
            
            # Process all content pages
            for page in book_content["pages"]:
                page_dict = cast(Dict[str, Any], page)  # Tell type checker page is definitely a Dict
                failure = await process_page(
                    park_name, page_dict, False, images_path, style_focus,
                    args.retry_count, args.retry_delay, args.force, args.seed,
                    args.rotating_seeds
                )
                if failure:
                    current_failures.append(failure)
            
            # Process back cover
            if not args.skip_covers and "back_cover" in book_content:
                failure = await process_page(
                    park_name, book_content["back_cover"], True, images_path, style_focus,
                    args.retry_count, args.retry_delay, args.force, args.seed,
                    args.rotating_seeds
                )
                if failure:
                    current_failures.append(failure)
    
    # Handle failures
    if current_failures:
        try:
            with open(failed_pages_path, 'w') as f:
                json.dump(current_failures, f, indent=2)
            
            print(f"\n⚠️ {len(current_failures)} pages failed to generate:")
            for failure in current_failures:
                page_label = "front cover" if failure["page_number"] == 0 else "back cover" if failure["page_number"] == 11 else f"page {failure['page_number']}"
                print(f"  - {page_label}: {failure['error']}")
            print(f"\nFailed pages saved to {failed_pages_path}")
            print("You can retry generating these pages with the --retry-failed flag")
        except Exception as e:
            print(f"Error saving failed pages: {str(e)}")
    else:
        # Success - remove failed pages file if it exists
        if failed_pages_path.exists():
            failed_pages_path.unlink()
        print(f"\n✅ All requested illustrations for {park_name} National Park have been successfully generated")


if __name__ == "__main__":
    asyncio.run(main()) 