import requests
import datetime
import json
import os

def read_mealplans(start_date: str = None, end_date: str = None):
    """Reads the meal plans from Mealie and returns it as a string.

    Args:
        start_date (str, optional): The start date of the meal plans to read,
            in the format YYYY-MM-DD.
        end_date (str, optional): The end date of the meal plans to read,
            in the format YYYY-MM-DD.

    Returns:
        str: The meal plans.
    """

    endpoint = os.getenv("MEALIE_ENDPOINT")
    api_key = os.getenv("MEALIE_API_KEY")
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key
    }

    def get_mealplans(sdate, edate):
        url = f"{endpoint}/api/households/mealplans"
        
        params = {}
        if sdate is not None:
            params["start_date"] = sdate
        if end_date is not None:
            params["end_date"] = edate

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status
        return response

    def get_recipe_by_id(recipe_id):
        url = f"{endpoint}/api/recipes/{recipe_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status
        return response

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

    meal_plan_response = get_mealplans(start_date, end_date)
    meals = meal_plan_response.json()["items"]
    response = list()
    for meal in meals:
        # print(json.dumps(meal, indent=4, sort_keys=True))
        entry_type = meal["entryType"]
        date = meal["date"]
        response.append(f"\n# {entry_type} on {date}")
        recipe_id = meal["recipe"]["id"]
        recipe = get_recipe_by_id(recipe_id)
        parsed_recipe = parse_recipe_json(recipe.json())
        response.append(parsed_recipe)
    
    return "\n".join(response)

if __name__ == "__main__":
    print(read_mealplans("2025-02-25", "2025-02-26"))