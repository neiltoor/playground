"""Recipe Hunter API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.models import (
    PantryItem,
    PantryItemCreate,
    PantryListResponse,
    RecipeGenerateRequest,
    RecipeGenerateResponse,
    Recipe,
    SaveRecipeRequest,
    SavedRecipe,
    SavedRecipesResponse
)
from app.services.recipe_service import RecipeService, CUISINES


router = APIRouter()


# --- Cuisine Options ---

@router.get("/cuisines")
async def get_cuisines(user: dict = Depends(get_current_user)):
    """Get available cuisine options."""
    return {"cuisines": CUISINES}


# --- Pantry Endpoints ---

@router.get("/pantry", response_model=PantryListResponse)
async def get_pantry(user: dict = Depends(get_current_user)):
    """Get user's pantry items."""
    items = RecipeService.get_pantry_items(user["username"])
    return PantryListResponse(
        items=[PantryItem(**item) for item in items]
    )


@router.post("/pantry", response_model=PantryItem)
async def add_pantry_item(
    item: PantryItemCreate,
    user: dict = Depends(get_current_user)
):
    """Add an item to user's pantry."""
    result = RecipeService.add_pantry_item(user["username"], item.item_name)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to add item")
        )

    return PantryItem(**result["item"])


@router.delete("/pantry/{item_id}")
async def remove_pantry_item(
    item_id: int,
    user: dict = Depends(get_current_user)
):
    """Remove an item from user's pantry."""
    result = RecipeService.remove_pantry_item(user["username"], item_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Item not found")
        )

    return {"message": "Item removed"}


# --- Recipe Generation ---

@router.post("/recipes/generate")
async def generate_recipes(
    request: RecipeGenerateRequest,
    user: dict = Depends(get_current_user)
):
    """Generate recipes based on pantry and cuisine preferences."""
    result = await RecipeService.generate_recipes(
        username=user["username"],
        cuisines=request.cuisines,
        recipe_count=request.recipe_count
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to generate recipes")
        )

    return {
        "recipes": result["recipes"],
        "pantry_used": result["pantry_used"]
    }


# --- Saved Recipes ---

@router.get("/recipes/saved", response_model=SavedRecipesResponse)
async def get_saved_recipes(user: dict = Depends(get_current_user)):
    """Get user's saved recipes."""
    recipes = RecipeService.get_saved_recipes(user["username"])
    return SavedRecipesResponse(
        recipes=[SavedRecipe(**recipe) for recipe in recipes]
    )


@router.post("/recipes/save", response_model=SavedRecipe)
async def save_recipe(
    request: SaveRecipeRequest,
    user: dict = Depends(get_current_user)
):
    """Save a recipe."""
    result = RecipeService.save_recipe(
        username=user["username"],
        recipe_name=request.recipe_name,
        cuisine=request.cuisine,
        ingredients=request.ingredients,
        instructions=request.instructions,
        prep_time=request.prep_time
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to save recipe")
        )

    return SavedRecipe(**result["recipe"])


@router.delete("/recipes/saved/{recipe_id}")
async def delete_saved_recipe(
    recipe_id: int,
    user: dict = Depends(get_current_user)
):
    """Delete a saved recipe."""
    result = RecipeService.delete_saved_recipe(user["username"], recipe_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Recipe not found")
        )

    return {"message": "Recipe deleted"}
