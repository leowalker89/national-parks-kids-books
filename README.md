# National Parks Board Books for Kids

**Introduce young children (ages 0-5) to the wonders of U.S. National Parks!**

This project uses AI to help create simple, beautiful board books showcasing America's natural treasures. Each book provides an age-appropriate glimpse into a park's unique animals, plants, and landscapes through engaging text and vibrant illustrations.

## Project Goal

To generate draft content (text and illustration ideas) for 10-page board books about individual National Parks, focusing purely on nature and designed for early childhood engagement.

## Technical Details

*   **Core Language:** Python 3.12+
*   **Environment/Packages:** `uv`
*   **AI APIs:** Perplexity (for research), Fireworks AI (for content/image generation - *Note: Image generation script might need updates*)

## Setup

**Requirements:**

*   Python 3.12+
*   `uv` (Python package manager)
*   Perplexity API Key
*   Fireworks AI API Key

**Steps:**

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd national-parks-kids-books
    ```

2.  **Install `uv`:**
    *   **macOS/Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`
    *   **Windows (PowerShell):** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
    *   *(Alternative)* If you have `pip`: `pip install uv`

3.  **Create a `.env` file** in the project root and add your API keys:
    ```dotenv
    PPLX_API_KEY=your_perplexity_api_key
    FIREWORKS_API_KEY=your_fireworks_api_key
    ```

4.  **Set up the virtual environment and install dependencies:**
    ```bash
    uv venv  # Create virtual environment (.venv)
    uv sync # Install dependencies from pyproject.toml
    ```
    *   To activate the environment (usually optional when using `uv run`): `source .venv/bin/activate` (Mac/Linux) or `.venv\\Scripts\\activate` (Windows)
    *   To add a new package: `uv add <package_name>`

## How to Use

These scripts help generate the raw materials for a park book.

1.  **Create Park Folder:**
    *   Creates the standard directory structure for a new park.
    *   **Command:** `uv run python src/scripts/create_park_folder.py "Park Name"`
    *   *(Example: `uv run python src/scripts/create_park_folder.py "Yellowstone"`)*

2.  **Research Park:**
    *   Uses Perplexity AI to gather facts about the park.
    *   Saves research to `parks/park_name/research/research.md`.
    *   **Command:** `uv run python src/scripts/research_park.py "Park Name"`
    *   *(Example: `uv run python src/scripts/research_park.py "Yellowstone"`)*

3.  **Generate Book Text & Illustration Ideas:**
    *   Uses Fireworks AI and the research file to generate text and illustration descriptions for each page.
    *   Saves output to `parks/park_name/content/book.json`.
    *   **Command:** `uv run python src/scripts/generate_book_text.py "Park Name"`
    *   *(Example: `uv run python src/scripts/generate_book_text.py "Yellowstone"`)*

4.  **(Optional) Generate Illustrations:**
    *   *Note: These scripts use the generated `book.json` to create images.*
    *   **Command:** `uv run python src/scripts/generate_illustrations.py "Park Name"`
    *   OR `uv run python src/scripts/generate_illustrations_together.py "Park Name"`

**(Park names are automatically formatted for folder names, e.g., "Yellowstone" becomes `yellowstone`)**

## License

[Your chosen license]

## Acknowledgments

*   U.S. National Park Service
