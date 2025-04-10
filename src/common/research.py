"""
National Parks Research Module.

This module handles research queries to the Perplexity API for gathering 
kid-friendly information about U.S. National Parks.
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def research_park(park_name: str) -> Dict[str, Any]:
    """
    Research a specific national park using Perplexity API.
    
    Args:
        park_name: Name of the national park to research
            
    Returns:
        Dict containing organized research results with keys:
            - park_name: str
            - research_content: str
            - status: "success" or "error"
            - error: str (only present if status is "error")
    """
    # Ensure API key is available
    api_key = os.getenv("PPLX_API_KEY")
    if not api_key:
        return {
            "park_name": park_name,
            "error": "PERPLEXITY_API_KEY environment variable not set",
            "status": "error"
        }
    
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai"
    )
    
    system_prompt = """
    You are a children’s book research assistant specializing in U.S. National Parks.

    Your research should be:
        1.	Suitable for children ages 2-5—simple, engaging, and visually descriptive.
        2.	Highly accurate to support detailed illustrations created by a Text-to-Image generator.
        3.	Rich in precise visual details (colors, shapes, textures, scale, perspective).
        4.  Detailed descriptions that can be used to create a descriptive story line about the park.

    Include the following information for each park in bullet points:
        **Landmarks, Scenic Views, and Notable Features (emphasize at least 7, but aim for 10)**:
        •	Distinctive features (unique shapes, colors, textures, scale).
        •	Clearly describe foreground and background elements.
        •	Note appearance variations at different times of day or seasons (if relevant).
        •	Include popular viewpoints even if they aren’t formal landmarks.
        **Common Wildlife (at least 5 animals, but aim for 7-10)**:
        •	Precise descriptions of color, markings, size (compared to familiar objects), and notable physical traits.
        •	Distinctive behaviors or poses appealing to children.
        •	Typical habitats within the park (near rivers, meadows, forests, etc.).
        **Notable Plants & Trees (at least 3, but aim for 5-7)**:
        •	Common species and their distinguishing features.
        •	Detailed visual descriptions (unique colors, leaves, bark, flowers).
        •	Changes in appearance across seasons (if relevant).
        **Simple & Memorable Facts (at least 3, but aim for 5-7)**:
        •	Brief, interesting, easy-to-remember facts.
        •	Safe & Fun Activities suitable for families.

    Do not mention any man-made structures, visitor centers, or facilities.

    Present all information clearly and engagingly, appropriate for young children and ideal for vividly detailed illustrations.
    """

    user_prompt = f"""
    Please research {park_name} National Park with a focus on creating content 
    for a children's board book. The research will be used to generate illustrations,
    so provide highly detailed visual descriptions.
    """
    
    try:
        response = await client.chat.completions.create(
            model="sonar-pro",  
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
        )
        
        # Make sure we have content before returning
        if not response.choices or not response.choices[0].message.content:
            return {
                "park_name": park_name,
                "error": "No content returned from API",
                "status": "error"
            }
        
        return {
            "park_name": park_name,
            "research_content": response.choices[0].message.content,
            "status": "success"
        }
        
    except Exception as e:
        return {
            "park_name": park_name,
            "error": str(e),
            "status": "error"
        }

async def main() -> None:
    """Example usage of the research_park function."""
    result = await research_park("Yellowstone")
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
