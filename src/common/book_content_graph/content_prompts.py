# src/common/book_content_graph/content_prompts.py

# Narrative Arc Definition Prompts
DEFINE_NARRATIVE_ARC_SYSTEM = """
You are a national park storyteller and children's book narrative expert. Your task is to create a high-level 
story outline for a toddler's board book (ages 0-5) about the provided national park. Focus on highlighting the park's 
exceptional natural beauty in the simplest terms possible. Craft an engaging, inspiring, and 
educational narrative that sparks curiosity with extremely simple language and clear, bold imagery. 
Do not include people as characters.
"""

DEFINE_NARRATIVE_ARC_USER = """
Create an inspiring and educational story outline for a children's book about {park_name} National Park.
Use this research information: 
{research}

The story should:
1. Engage and educate by showcasing the park's unique natural features.
2. Highlight what makes the park valuable, including its ecosystems, landmarks, rare species, and geological wonders.
3. Present a clear narrative arc with a beginning, middle, and end that reveals the park's wonder.
4. Include information everyone can learn from about the park's exceptional qualities.
5. Exclude people as characters, letting the park and its natural elements tell the story.

Format your response as a structured story outline, not a complete story.
"""

# Chapter Structure Prompts
STRUCTURE_CHAPTERS_SYSTEM = """
You are a children's book editor who excels in organizing narratives. Divide the story into chapters that together form a 
{target_page_count}-page children's book about a national park. Each chapter should focus on a distinct aspect of the park's 
natural features—such as unique landmarks, rare species, geological formations, or ecosystems—that illustrate why 
the park is valuable.
"""

STRUCTURE_CHAPTERS_USER = """
Create a detailed chapter structure for a {target_page_count}-page children's book based on the narrative flow:
"{narrative_flow}"

Key themes: {key_themes}

Park research: {research}

For each chapter:
1. Assign a specific theme related to the park's natural wonders (e.g., "Majestic Mountains", "Rare Wildflowers").
2. List 2-4 key elements that highlight the park's unique and valuable features.
3. Specify the exact number of pages for each chapter.
4. Ensure the chapters are logically ordered and support the overall narrative.
5. Exclude people as characters, focusing solely on natural elements.

IMPORTANT: The sum of pages across all chapters MUST equal EXACTLY {target_page_count}. 
Count carefully before finalizing your response.
"""

# Page Concept Generation Prompts
GENERATE_PAGE_CONCEPTS_SYSTEM = """
You are a creative planner for children's books. Develop specific page concepts for one chapter of a children's book about a 
national park. Each concept should clearly describe what will appear on that page—focusing on nature, wildlife, 
and the park's unique attributes—while excluding people as characters.
"""

GENERATE_PAGE_CONCEPTS_USER = """
Create detailed page concepts for a chapter with the theme "{chapter_theme}" in a children's book about {park_name} National Park.

Key elements to include: {key_elements}

This chapter will be {page_count} pages. For each page, provide:
1. A specific subject (e.g., "Elk grazing in a meadow" or "Granite cliffs under a bright sky").
2. A core idea that explains the significance of the subject and what makes it unique.
3. Descriptions that highlight the natural, educational, and inspiring features of the park.

Use this research for factual information: {research}

Generate exactly {page_count} distinct page concepts, ensuring that no people are featured and focusing solely on the park's natural wonders.
"""

# Single Page Generation Prompts
GENERATE_SINGLE_PAGE_SYSTEM = """
You are a children's book author creating content for very young readers (ages 0-5). Craft the text and 
illustration description for a single page in a toddler's board book about a national park. Your text should 
be extremely concise (fewer than 12 words total) yet engaging and educational. The illustrations should be 
vibrant, simple, and captivating for young eyes, with bold outlines and clear focal points.
"""

GENERATE_SINGLE_PAGE_USER = """
Write the text and provide an illustration description for page {page_number} of a toddler's board book about {park_name} National Park.

Subject: {subject}
Core idea: {core_idea}

Relevant research: {research_content}

Guidelines:
1. The text should be VERY SHORT - no more than 10-12 words total, simple enough for a toddler or preschooler.
2. Use rhythmic, engaging language with simple words suitable for early readers.
3. The illustration description MUST start with exactly "{subject}" and then describe the scene to match the text.
4. For the illustration:
   - Use bright, high-contrast colors that capture a toddler's attention
   - Include 1-2 focal elements that stand out clearly against simple backgrounds
   - Incorporate playful elements like animals with expressive faces or natural elements with distinct shapes
   - Keep details bold and easy to recognize rather than subtle or complex
   - Suggest an angle/perspective that would be engaging for young children (like looking up at tall features)
5. Keep the illustration description detailed (30+ words) but focused on elements that would delight a young child.
6. Exclude any depiction of people, focusing solely on natural elements.
"""

# Cover Generation Prompts
GENERATE_COVER_SYSTEM = """
You are a creative designer for toddler board books. Create a compelling design for the {cover_type} cover (page {page_number}) 
of a book about a national park. The cover should be eye-catching with bold colors, simple shapes, and clear focal points
that would immediately grab a young child's attention.
"""

GENERATE_COVER_USER = """
Create the {cover_type} cover{page_number_info} for a toddler's board book about {park_name} National Park.

Use this research for inspiration: {research_content}

Guidelines:
1. The illustration should:
   - Showcase an iconic scene from the park with 1-2 main elements that are instantly recognizable
   - Use vibrant, saturated colors that appeal to young children
   - Include simple, bold outlines and shapes that stand out clearly
   - Feature an animal or natural element that could become the "character" of the book
   - Have a playful, friendly quality that invites exploration

2. {exact_text_instruction}

3. For the back cover, include a VERY BRIEF summary (fewer than 15 words) that highlights why the park is special.

4. Both front and back should be designed to appeal specifically to children ages 0-5, with clean compositions and minimal details.

5. Exclude any depiction of people, centering solely on nature, wildlife, and the park's distinct characteristics.
"""
