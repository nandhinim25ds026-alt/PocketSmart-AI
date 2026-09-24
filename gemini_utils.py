import os
import re
import json
import urllib.parse

from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

from models import HomeBudgetInput, PartyBudgetInput, JewelryBudgetInput

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("No GOOGLE_API_KEY found in environment variables. Please set it in your .env file.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-3.6-flash")


def extract_json_from_response(text: str) -> dict:
    """Gemini sometimes wraps its JSON in ```json fences - strip those before parsing."""
    cleaned = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: try to grab the first {...} block in the text
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _add_links(result: dict, breakdown_key: str, platforms: dict):
    """Attach shopping links to every item's search_terms field."""
    for category in result.get(breakdown_key, []):
        for item in category.get("items", []):
            terms = item.get("search_terms", "")
            if terms:
                q = urllib.parse.quote_plus(terms)
                item["shopping_links"] = {name: url.format(q=q) for name, url in platforms.items()}


HOME_PLATFORMS = {
    "amazon": "https://www.amazon.in/s?k={q}",
    "flipkart": "https://www.flipkart.com/search?q={q}",
    "ikea": "https://www.ikea.com/in/en/search/?q={q}",
    "myntra": "https://www.myntra.com/search?q={q}",
}

PARTY_PLATFORMS = {
    "amazon": "https://www.amazon.in/s?k={q}",
    "flipkart": "https://www.flipkart.com/search?q={q}",
    "swiggy": "https://www.swiggy.com/search?query={q}",
    "zomato": "https://www.zomato.com/search?q={q}",
    "bookmyshow": "https://in.bookmyshow.com/search?q={q}",
}

JEWELRY_PLATFORMS = {
    "amazon": "https://www.amazon.in/s?k={q}",
    "flipkart": "https://www.flipkart.com/search?q={q}",
    "tanishq": "https://www.tanishq.co.in/search?q={q}",
    "caratlane": "https://www.caratlane.com/search?q={q}",
}


def get_home_recommendations(budget_input: HomeBudgetInput) -> dict:
    prompt = f"""
    I need interior design product recommendations for a home in India with a
    total budget of INR {budget_input.total_budget:.2f}.

    Requirements:
    - {budget_input.num_lights} lights/lighting fixtures
    - {budget_input.num_fans} ceiling fans
    - {budget_input.num_furniture} furniture pieces
    - {budget_input.num_dining_tables} dining tables

    Rooms to consider:
    {"- Living Room" if budget_input.has_living_room else ""}
    {"- Kitchen" if budget_input.has_kitchen else ""}
    {"- Bedroom" if budget_input.has_bedroom else ""}

    Additional requirements: {budget_input.additional_requirements or "None"}

    Respond ONLY with valid JSON (no markdown, no commentary) in exactly this structure:
    {{
      "total_budget": {budget_input.total_budget:.2f},
      "budget_breakdown": [
        {{
          "category": "lighting",
          "allocation": 0.0,
          "items": [
            {{"name": "", "description": "", "estimated_price": 0.0, "quantity": 0, "search_terms": ""}}
          ]
        }}
      ],
      "remaining_budget": 0.0,
      "additional_suggestions": []
    }}

    Ensure the total of all estimated_price * quantity stays within the given budget.
    """
    response = model.generate_content(prompt)
    result = extract_json_from_response(response.text)
    _add_links(result, "budget_breakdown", HOME_PLATFORMS)
    return result


def get_party_recommendations(budget_input: PartyBudgetInput) -> dict:
    prompt = f"""
    I need party planning recommendations for India with a total budget of
    INR {budget_input.total_budget:.2f}.

    Party details:
    - Type: {budget_input.party_type}
    - Number of guests: {budget_input.num_guests}
    - Venue type: {budget_input.venue_type or "Not specified"}
    - Catering needed: {"Yes" if budget_input.needs_catering else "No"}
    - Decoration needed: {"Yes" if budget_input.needs_decoration else "No"}
    - Entertainment needed: {"Yes" if budget_input.needs_entertainment else "No"}

    Additional requirements: {budget_input.additional_requirements or "None"}

    Respond ONLY with valid JSON (no markdown, no commentary) in exactly this structure:
    {{
      "total_budget": {budget_input.total_budget:.2f},
      "budget_breakdown": [
        {{
          "category": "catering",
          "allocation": 0.0,
          "items": [
            {{"name": "", "description": "", "estimated_price": 0.0, "quantity": 0, "search_terms": ""}}
          ]
        }}
      ],
      "remaining_budget": 0.0,
      "additional_suggestions": []
    }}

    Ensure all costs stay within budget.
    """
    response = model.generate_content(prompt)
    result = extract_json_from_response(response.text)
    _add_links(result, "budget_breakdown", PARTY_PLATFORMS)
    return result


def get_jewelry_recommendations(budget_input: JewelryBudgetInput, image_path: str = None) -> dict:
    base_prompt = f"""
    I need jewelry recommendations for India with a total budget of
    INR {budget_input.total_budget:.2f}.

    Occasion: {budget_input.occasion}
    Preferences: {budget_input.preferences or "Not specified"}
    """

    json_format = """
    Respond ONLY with valid JSON (no markdown, no commentary) in exactly this structure:
    {
      "total_budget": 0.0,
      "outfit_analysis": {"colors": [], "style": "", "formality": ""},
      "jewelry_recommendations": [
        {"item_type": "", "description": "", "style": "", "estimated_price": 0.0, "search_terms": ""}
      ],
      "remaining_budget": 0.0,
      "styling_tips": []
    }
    Keep prices in INR and stay within budget. If no image was provided, leave
    outfit_analysis fields as empty strings/lists.
    """

    if image_path:
        img = Image.open(image_path)
        prompt = base_prompt + "\nAn outfit image is attached - consider its colors and style.\n" + json_format
        response = model.generate_content([prompt, img])
    else:
        prompt = base_prompt + json_format
        response = model.generate_content(prompt)

    result = extract_json_from_response(response.text)

    for item in result.get("jewelry_recommendations", []):
        terms = item.get("search_terms", "")
        if terms:
            q = urllib.parse.quote_plus(terms)
            item["shopping_links"] = {name: url.format(q=q) for name, url in JEWELRY_PLATFORMS.items()}

    return result
