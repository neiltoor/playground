"""Service for Recipe Hunter - pantry management and recipe generation."""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

import httpx
from sqlalchemy import text

from app.database import create_db_engine


# Anthropic service URL (internal Docker network)
ANTHROPIC_SERVICE_URL = "http://anthropic-service:8001"
CONFIG_FILE_PATH = "/data/config.json"


def _load_anthropic_model() -> str:
    """Load default Anthropic model from config file."""
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            model = config.get("llm_providers", {}).get("anthropic", {}).get("default_model")
            if model:
                return model
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        pass
    return "claude-3-haiku-20240307"  # Fallback


ANTHROPIC_MODEL = _load_anthropic_model()

# Available cuisines
CUISINES = [
    "Italian",
    "Chinese",
    "Indian",
    "American",
    "Mexican",
    "Mediterranean",
    "Japanese",
    "Thai",
    "French",
    "Korean"
]


class RecipeService:
    """Service for pantry and recipe management."""

    # --- Pantry Operations ---

    @staticmethod
    def get_pantry_items(username: str) -> List[Dict[str, Any]]:
        """Get all pantry items for a user."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, item_name, created_at
                        FROM pantry_items
                        WHERE username = :username
                        ORDER BY item_name
                    """),
                    {"username": username}
                )
                return [
                    {
                        "id": row.id,
                        "item_name": row.item_name,
                        "created_at": row.created_at
                    }
                    for row in result
                ]
        except Exception as e:
            print(f"Error getting pantry items: {e}")
            return []

    @staticmethod
    def add_pantry_item(username: str, item_name: str) -> Dict[str, Any]:
        """Add an item to user's pantry."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                # Check if item already exists
                existing = conn.execute(
                    text("""
                        SELECT id FROM pantry_items
                        WHERE username = :username AND LOWER(item_name) = LOWER(:item_name)
                    """),
                    {"username": username, "item_name": item_name}
                ).fetchone()

                if existing:
                    return {"success": False, "error": "Item already in pantry"}

                # Insert new item
                result = conn.execute(
                    text("""
                        INSERT INTO pantry_items (username, item_name)
                        VALUES (:username, :item_name)
                        RETURNING id, item_name, created_at
                    """),
                    {"username": username, "item_name": item_name.strip()}
                )
                conn.commit()
                row = result.fetchone()

                return {
                    "success": True,
                    "item": {
                        "id": row.id,
                        "item_name": row.item_name,
                        "created_at": row.created_at
                    }
                }
        except Exception as e:
            print(f"Error adding pantry item: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def remove_pantry_item(username: str, item_id: int) -> Dict[str, Any]:
        """Remove an item from user's pantry."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        DELETE FROM pantry_items
                        WHERE id = :item_id AND username = :username
                        RETURNING id
                    """),
                    {"item_id": item_id, "username": username}
                )
                conn.commit()

                if result.fetchone():
                    return {"success": True}
                else:
                    return {"success": False, "error": "Item not found"}
        except Exception as e:
            print(f"Error removing pantry item: {e}")
            return {"success": False, "error": str(e)}

    # --- Recipe Generation ---

    @staticmethod
    async def generate_recipes(
        username: str,
        cuisines: List[str],
        recipe_count: int
    ) -> Dict[str, Any]:
        """Generate recipes based on pantry and cuisine preferences."""
        try:
            # Get user's pantry items
            pantry_items = RecipeService.get_pantry_items(username)
            pantry_list = [item["item_name"] for item in pantry_items]

            if not pantry_list:
                return {
                    "success": False,
                    "error": "Your pantry is empty. Add some ingredients first!"
                }

            # Build the prompt
            prompt = f"""You are a helpful chef assistant. Based on the user's pantry and cuisine preferences, suggest {recipe_count} recipes.

Pantry items available: {', '.join(pantry_list)}

Cuisine preferences: {', '.join(cuisines)}

For each recipe, provide the information in this exact JSON format:
{{
    "recipes": [
        {{
            "name": "Recipe Name",
            "cuisine": "Cuisine Type",
            "ingredients": ["ingredient 1", "ingredient 2"],
            "ingredients_in_pantry": ["items from pantry used"],
            "ingredients_to_buy": ["items needed but not in pantry"],
            "instructions": ["Step 1", "Step 2", "Step 3"],
            "prep_time": "30 minutes"
        }}
    ]
}}

Important:
- Focus on practical, easy-to-make meals
- Maximize use of pantry items
- Clearly separate what's in pantry vs what needs to be bought
- Keep instructions clear and numbered
- Return ONLY valid JSON, no additional text"""

            # Call Anthropic service
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{ANTHROPIC_SERVICE_URL}/chat",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "model": ANTHROPIC_MODEL,
                        "temperature": 0.7,
                        "max_tokens": 4096
                    }
                )

                if response.status_code == 503:
                    return {
                        "success": False,
                        "error": "Anthropic API key not configured"
                    }

                response.raise_for_status()
                data = response.json()
                content = data.get("content", "")

                # Parse the JSON response
                try:
                    # Try to extract JSON from the response
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        recipes_data = json.loads(json_str)
                        return {
                            "success": True,
                            "recipes": recipes_data.get("recipes", []),
                            "pantry_used": pantry_list
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Could not parse recipe response"
                        }
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    print(f"Content was: {content}")
                    return {
                        "success": False,
                        "error": "Could not parse recipe response"
                    }

        except httpx.HTTPError as e:
            print(f"HTTP error calling Anthropic: {e}")
            return {"success": False, "error": f"LLM service error: {str(e)}"}
        except Exception as e:
            print(f"Error generating recipes: {e}")
            return {"success": False, "error": str(e)}

    # --- Saved Recipes Operations ---

    @staticmethod
    def get_saved_recipes(username: str) -> List[Dict[str, Any]]:
        """Get all saved recipes for a user."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, recipe_name, cuisine, ingredients, instructions, prep_time, created_at
                        FROM saved_recipes
                        WHERE username = :username
                        ORDER BY created_at DESC
                    """),
                    {"username": username}
                )
                return [
                    {
                        "id": row.id,
                        "recipe_name": row.recipe_name,
                        "cuisine": row.cuisine,
                        "ingredients": row.ingredients,
                        "instructions": row.instructions,
                        "prep_time": row.prep_time,
                        "created_at": row.created_at
                    }
                    for row in result
                ]
        except Exception as e:
            print(f"Error getting saved recipes: {e}")
            return []

    @staticmethod
    def save_recipe(
        username: str,
        recipe_name: str,
        cuisine: str,
        ingredients: str,
        instructions: str,
        prep_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """Save a recipe for a user."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO saved_recipes (username, recipe_name, cuisine, ingredients, instructions, prep_time)
                        VALUES (:username, :recipe_name, :cuisine, :ingredients, :instructions, :prep_time)
                        RETURNING id, recipe_name, cuisine, ingredients, instructions, prep_time, created_at
                    """),
                    {
                        "username": username,
                        "recipe_name": recipe_name,
                        "cuisine": cuisine,
                        "ingredients": ingredients,
                        "instructions": instructions,
                        "prep_time": prep_time
                    }
                )
                conn.commit()
                row = result.fetchone()

                return {
                    "success": True,
                    "recipe": {
                        "id": row.id,
                        "recipe_name": row.recipe_name,
                        "cuisine": row.cuisine,
                        "ingredients": row.ingredients,
                        "instructions": row.instructions,
                        "prep_time": row.prep_time,
                        "created_at": row.created_at
                    }
                }
        except Exception as e:
            print(f"Error saving recipe: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def delete_saved_recipe(username: str, recipe_id: int) -> Dict[str, Any]:
        """Delete a saved recipe."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        DELETE FROM saved_recipes
                        WHERE id = :recipe_id AND username = :username
                        RETURNING id
                    """),
                    {"recipe_id": recipe_id, "username": username}
                )
                conn.commit()

                if result.fetchone():
                    return {"success": True}
                else:
                    return {"success": False, "error": "Recipe not found"}
        except Exception as e:
            print(f"Error deleting saved recipe: {e}")
            return {"success": False, "error": str(e)}

    # --- Shopping List Operations ---

    @staticmethod
    def get_shopping_list(username: str) -> List[Dict[str, Any]]:
        """Get all shopping list items for a user."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, item_name, created_at
                        FROM shopping_list
                        WHERE username = :username
                        ORDER BY item_name
                    """),
                    {"username": username}
                )
                return [
                    {
                        "id": row.id,
                        "item_name": row.item_name,
                        "created_at": row.created_at
                    }
                    for row in result
                ]
        except Exception as e:
            print(f"Error getting shopping list: {e}")
            return []

    @staticmethod
    def add_shopping_item(username: str, item_name: str) -> Dict[str, Any]:
        """Add an item to user's shopping list."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                # Check if item already exists
                existing = conn.execute(
                    text("""
                        SELECT id FROM shopping_list
                        WHERE username = :username AND LOWER(item_name) = LOWER(:item_name)
                    """),
                    {"username": username, "item_name": item_name}
                ).fetchone()

                if existing:
                    return {"success": False, "error": "Item already in shopping list"}

                # Insert new item
                result = conn.execute(
                    text("""
                        INSERT INTO shopping_list (username, item_name)
                        VALUES (:username, :item_name)
                        RETURNING id, item_name, created_at
                    """),
                    {"username": username, "item_name": item_name.strip()}
                )
                conn.commit()
                row = result.fetchone()

                return {
                    "success": True,
                    "item": {
                        "id": row.id,
                        "item_name": row.item_name,
                        "created_at": row.created_at
                    }
                }
        except Exception as e:
            print(f"Error adding shopping item: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def remove_shopping_item(username: str, item_id: int) -> Dict[str, Any]:
        """Remove an item from user's shopping list."""
        try:
            engine = create_db_engine()
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        DELETE FROM shopping_list
                        WHERE id = :item_id AND username = :username
                        RETURNING id
                    """),
                    {"item_id": item_id, "username": username}
                )
                conn.commit()

                if result.fetchone():
                    return {"success": True}
                else:
                    return {"success": False, "error": "Item not found"}
        except Exception as e:
            print(f"Error removing shopping item: {e}")
            return {"success": False, "error": str(e)}

    # --- Vibe Search ---

    @staticmethod
    async def search_by_vibe(vibe: str, recipe_count: int) -> Dict[str, Any]:
        """Generate recipes based on a free-text craving/vibe description."""
        try:
            prompt = f"""You are a helpful chef assistant. The user is craving: "{vibe}"

Generate {recipe_count} recipe suggestions that match this craving/vibe perfectly.

For each recipe, provide the information in this exact JSON format:
{{
    "recipes": [
        {{
            "name": "Recipe Name",
            "cuisine": "Cuisine Type",
            "ingredients": ["ingredient 1", "ingredient 2"],
            "instructions": ["Step 1", "Step 2", "Step 3"],
            "prep_time": "30 minutes"
        }}
    ]
}}

Important:
- Focus on recipes that match the vibe/craving described
- Include practical, easy-to-make meals
- Keep instructions clear and numbered
- Return ONLY valid JSON, no additional text"""

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{ANTHROPIC_SERVICE_URL}/chat",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "model": ANTHROPIC_MODEL,
                        "temperature": 0.7,
                        "max_tokens": 4096
                    }
                )

                if response.status_code == 503:
                    return {
                        "success": False,
                        "error": "Anthropic API key not configured"
                    }

                response.raise_for_status()
                data = response.json()
                content = data.get("content", "")

                # Parse the JSON response
                try:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        recipes_data = json.loads(json_str)
                        return {
                            "success": True,
                            "recipes": recipes_data.get("recipes", []),
                            "vibe": vibe
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Could not parse recipe response"
                        }
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    print(f"Content was: {content}")
                    return {
                        "success": False,
                        "error": "Could not parse recipe response"
                    }

        except httpx.HTTPError as e:
            print(f"HTTP error calling Anthropic: {e}")
            return {"success": False, "error": f"LLM service error: {str(e)}"}
        except Exception as e:
            print(f"Error in vibe search: {e}")
            return {"success": False, "error": str(e)}

    # --- Shopping List Recipe Generation ---

    @staticmethod
    async def generate_from_shopping_list(
        username: str,
        recipe_count: int,
        include_pantry: bool = False
    ) -> Dict[str, Any]:
        """Generate recipes based on shopping list items."""
        try:
            # Get user's shopping list
            shopping_items = RecipeService.get_shopping_list(username)
            shopping_list = [item["item_name"] for item in shopping_items]

            if not shopping_list:
                return {
                    "success": False,
                    "error": "Your shopping list is empty. Add some items first!"
                }

            # Optionally get pantry items
            pantry_list = []
            if include_pantry:
                pantry_items = RecipeService.get_pantry_items(username)
                pantry_list = [item["item_name"] for item in pantry_items]

            # Build the prompt
            prompt = f"""You are a helpful chef assistant. The user plans to buy these items: {', '.join(shopping_list)}
{"They also have in their pantry: " + ', '.join(pantry_list) if pantry_list else ""}

Generate {recipe_count} recipes that make great use of the shopping list items.

For each recipe, provide the information in this exact JSON format:
{{
    "recipes": [
        {{
            "name": "Recipe Name",
            "cuisine": "Cuisine Type",
            "ingredients": ["ingredient 1", "ingredient 2"],
            "from_shopping_list": ["items from shopping list used"],
            "from_pantry": ["items from pantry used"],
            "additional_needed": ["extra items not on either list"],
            "instructions": ["Step 1", "Step 2", "Step 3"],
            "prep_time": "30 minutes"
        }}
    ]
}}

Important:
- Focus on practical, easy-to-make meals
- Maximize use of shopping list items
- Clearly separate what's on shopping list vs pantry vs extra needed
- Keep instructions clear and numbered
- Return ONLY valid JSON, no additional text"""

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{ANTHROPIC_SERVICE_URL}/chat",
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "model": ANTHROPIC_MODEL,
                        "temperature": 0.7,
                        "max_tokens": 4096
                    }
                )

                if response.status_code == 503:
                    return {
                        "success": False,
                        "error": "Anthropic API key not configured"
                    }

                response.raise_for_status()
                data = response.json()
                content = data.get("content", "")

                # Parse the JSON response
                try:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        recipes_data = json.loads(json_str)
                        return {
                            "success": True,
                            "recipes": recipes_data.get("recipes", []),
                            "shopping_list_used": shopping_list,
                            "pantry_used": pantry_list if include_pantry else []
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Could not parse recipe response"
                        }
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    print(f"Content was: {content}")
                    return {
                        "success": False,
                        "error": "Could not parse recipe response"
                    }

        except httpx.HTTPError as e:
            print(f"HTTP error calling Anthropic: {e}")
            return {"success": False, "error": f"LLM service error: {str(e)}"}
        except Exception as e:
            print(f"Error generating from shopping list: {e}")
            return {"success": False, "error": str(e)}
