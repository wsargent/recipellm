import requests
import os

from urllib.parse import urljoin

def get_recipe_in_mealie(slug: str):
    """Get a recipe from Mealie using its slug. This returns ingredients and instructions on the recipe.

    Args:
        slug (str): The slug of the recipe to retrieve.

    Returns:
        str: The text of the recipe.
    """

    def parse_ingredients(ingredients) -> str:
        parsed = [parse_ingredient(ingredient) for ingredient in ingredients]
        return "\n\n".join(parsed)

    def parse_ingredient(ingredient) -> str:
        display = ingredient["display"]
        return f"* {display}"

    def parse_instructions(instructions) -> str:
        parsed = [parse_instruction(instruction) for instruction in instructions]
        return "\n\n".join(parsed)

    def parse_instruction(instruction) -> str:
        text = instruction["text"]
        return f"* {text}"

    def parse_recipe_json(recipe) -> str:
        name = recipe["name"]
        prep_time = recipe["prepTime"]
        perform_time = recipe["performTime"]
        recipe_servings = recipe["recipeServings"]
        recipe_yield_quantity = recipe["recipeYieldQuantity"]
        recipe_ingredients = parse_ingredients(recipe["recipeIngredient"])
        recipe_instructions = parse_instructions(recipe["recipeInstructions"])
        recipe_original_url = recipe["orgURL"]

        return f"""
Name: {name}
Original URL: {recipe_original_url}
Prep Time: {prep_time}
Perform Time: {perform_time}
Servings: {recipe_servings}
Yield: {recipe_yield_quantity}    

## Ingredients: 
    
{recipe_ingredients}
    
## Instructions: 
    
{recipe_instructions}
"""

       
    base_url = os.getenv("MEALIE_ENDPOINT")
    api_key = os.getenv("MEALIE_API_KEY")
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key
    }

    endpoint = urljoin(base_url, f'/api/recipes/{slug}')
    
    response = requests.get(endpoint, headers=headers)
    response.raise_for_status()
    
    recipe = response.json()        
    return parse_recipe_json(recipe)
