import json
import requests
import os

# https://schema.org/Recipe
def create_recipe_from_arguments(name: str,                              
                              directions: str,
                              ingredients: str, 
                              author: str = "",
                              cook_time: str = "10m",
                              prep_time: str = "10m",
                              total_time: str = "20m",
                              servings: str = "",
                              source_url: str = "",
                              description: str = ""):
    """Creates a recipe in Mealie from raw text. Use this when you have Markdown or text recipes that you have to import into Mealie.

    Args:
        name (str): The name of the recipe.
        directions (str): The directions for the recipe, one direction per paragraph.
        ingredients (set[str]): The ingredients for the recipe, one ingredient per line,
            with no "-" or "*" markdown list items.
        author (str): The author of the recipe.
        cook_time (str): The cooking time for the recipe.
        prep_time (str): The prep time for the recipe.
        total_time (str): The total time for the recipe.
        servings (str): The number of servings in the recipe.
        source_url (str): The source URL for the recipe.
        description (str): The description for the recipe.

    Returns:
        str: The slug of the new recipe.
    """

    def iso_duration(fuzzy_duration: str):
        fuzzy_duration = fuzzy_duration.replace("minutes", "M")
        fuzzy_duration = fuzzy_duration.replace("mins", "M")
        fuzzy_duration = fuzzy_duration.replace("min", "M")
        fuzzy_duration = fuzzy_duration.replace("hours", "H")
        fuzzy_duration = fuzzy_duration.replace("hr", "H")
        fuzzy_duration = fuzzy_duration.replace(" ", "")
        fuzzy_duration = fuzzy_duration.strip()
        return "PT" + fuzzy_duration

    recipe_instructions = list()
    for step in directions.split("\n"):
        recipe_instructions.append({
            "@type": "HowToStep",
            "text": step
        })    
    
    cook_time = iso_duration(cook_time)
    prep_time = iso_duration(prep_time)
    total_time = iso_duration(total_time)
    recipe_yield = servings
    source_name = author
    source = {
        "@type": "Organization",
        "name": source_name
    }
    recipe_ingredients = ingredients.split("\n")
    recipe_dict ={
        "@context": "https://schema.org/",
        "@type": "Recipe",
        "name": name, # https://schema.org/name
        "author": source, # https://schema.org/author
        "recipeIngredient": recipe_ingredients, # https://schema.org/recipeIngredient
        "cookTime": cook_time, # https://schema.org/cookTime
        "prepTime": prep_time, # https://schema.org/prepTime
        "totalTime": total_time, # https://schema.org/totalTime
        "recipeYield": recipe_yield, # https://schema.org/recipeYield        
        "url": source_url, # https://schema.org/url
        "description": description,
        "recipeInstructions": recipe_instructions # https://schema.org/recipeInstructions
    }
    recipe_json = (json.dumps(recipe_dict, indent=2))
    print(recipe_json)

    endpoint = os.getenv("MEALIE_ENDPOINT")
    api_key = os.getenv("MEALIE_API_KEY")
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key
    }

    response = requests.post(f"{endpoint}/api/recipes/create/html-or-json", json={
      "data": recipe_json,
      "includeTags": False
    }, headers=headers)

    response.raise_for_status()
    
    return response.text

