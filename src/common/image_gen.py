"""
National Parks Image Generation Module.

This module handles the generation of children's book illustrations about U.S. National Parks
using Fireworks AI's Flux image generation model.
"""
import os
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from src.common.constants import ILLUSTRATION_STYLE

load_dotenv()

async def generate_image(
    description: str,
    park_name: str,
    style_focus: str = ILLUSTRATION_STYLE,
    output_path: Optional[str] = None,
    aspect_ratio: str = "9:16",
    guidance_scale: float = 3.5,
    num_inference_steps: int = 30,
    seed: int = 424242,
    is_cover: bool = False
) -> Dict[str, Any]:
    """
    Generate an illustration for a children's book about a national park.
    
    Args:
        description: Detailed description of the scene to illustrate
        park_name: Name of the national park (will be added to the prompt)
        style_focus: Style guidelines for the illustration
        output_path: Path where the image should be saved (if None, image won't be saved)
        aspect_ratio: Aspect ratio of the output image
        guidance_scale: Controls how closely the image follows the prompt
        num_inference_steps: Number of denoising steps
        seed: Seed for reproducible image generation (default: 424242)
        is_cover: Whether this is a cover page (front or back)
        
    Returns:
        Dict containing:
            - park_name: str
            - image_data: bytes (the raw image data)
            - output_path: str (path where image was saved, if applicable)
            - prompt: str (the full prompt used)
            - seed: int (the seed that was used)
            - status: "success" or "error"
            - error: str (only present if status is "error")
    """
    url = "https://api.fireworks.ai/inference/v1/workflows/accounts/fireworks/models/flux-1-dev-fp8/text_to_image"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "image/jpeg",
        "Authorization": f"Bearer {os.environ.get('FIREWORKS_API_KEY')}",
    }
    
    # Create the full prompt by combining style, park name, and description
    if is_cover:
        # For covers, we want to emphasize clarity and make sure the park name is prominently displayed
        full_prompt = f"{style_focus} Book cover for {park_name} National Park: {description} Don't include any text or title - the title will be added separately."
    else:
        full_prompt = f"{style_focus} {description}. Don't include any text."
    
    # Use the same aspect ratio for all pages including covers
    data = {
        "prompt": full_prompt,
        "aspect_ratio": aspect_ratio,
        "guidance_scale": guidance_scale,
        "num_inference_steps": num_inference_steps,
        "seed": seed  # Always include the seed
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    # Save the image if output_path is provided
                    if output_path:
                        # Ensure directory exists
                        output_dir = Path(output_path).parent
                        output_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Save the image
                        with open(output_path, "wb") as f:
                            f.write(image_data)
                    
                    return {
                        "park_name": park_name,
                        "image_data": image_data,
                        "output_path": output_path,
                        "prompt": full_prompt,
                        "seed": seed,
                        "status": "success"
                    }
                else:
                    error_text = await response.text()
                    return {
                        "park_name": park_name,
                        "error": f"API error: {response.status} - {error_text}",
                        "status": "error"
                    }
    except Exception as e:
        return {
            "park_name": park_name,
            "error": f"Error generating image: {str(e)}",
            "status": "error"
        }


async def main() -> None:
    """Example usage of the generate_image function."""
    # This is just a simple example
    park_name = "Rocky Mountain"
    description = "Bear Lake's crystal clear blue water reflects the surrounding mountains and sky, with smooth gray boulders and tall pine trees along the shore."
    
    # Use the default seed (424242) for reproducible generation
    result = await generate_image(
        description=description,
        park_name=park_name,
        output_path="example_image.jpg"
    )
    
    if result["status"] == "success":
        print(f"Image for {park_name} National Park generated successfully")
        if result["output_path"]:
            print(f"Saved to: {result['output_path']}")
        print(f"Used seed: {result['seed']}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())