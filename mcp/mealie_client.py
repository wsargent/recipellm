from typing import Any
import json

import requests

from urllib.parse import urljoin

class MealieClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def headers(self):
        return {
            "accept": "application/json",
            "Authorization": "Bearer " + self.api_key
        }

    def find_recipes_in_mealie(
            self,
            search_term: str,
            categories_csv: str = None,
            tags_csv: str = None) -> str:
        """
        Search for recipes in Mealie using various filters.

        Args:
            search_term (str): The string to search for, i.e. "chicken"
            categories_csv (str, optional): Comma separated list of category names or slugs to filter by
            tags_csv (str, optional): Comma separated list of tag names or slugs to filter by

        Returns:
            str: The list of recipes, or "No recipes found" if no recipes are found.
        """

        def parse_recipe_json(recipe) -> str:
            # print(json.dumps(recipe, indent=4))

            # id = recipe["id"]
            name = recipe["name"]
            slug = recipe["slug"]
            total_time = recipe["totalTime"]
            prep_time = recipe["prepTime"]
            description = recipe["description"]
            recipe_categories = ",".join([category['name'] for category in recipe["recipeCategory"]])
            recipe_tags = ",".join([tag['name'] for tag in recipe["tags"]])
            perform_time = recipe["performTime"]
            recipe_servings = recipe["recipeServings"]
            recipe_yield_quantity = recipe["recipeYieldQuantity"]
            recipe_original_url = recipe["orgURL"]

            return f"""---
    Name: {name}
    Slug: {slug}
    Original URL: {recipe_original_url}
    Prep Time: {prep_time}
    Perform Time: {perform_time}
    Total Time: {total_time}
    Categories: {recipe_categories}
    Tags: {recipe_tags}
    Servings: {recipe_servings}
    Yield: {recipe_yield_quantity}

    Description:

    {description}
    """
        endpoint = urljoin(self.base_url, '/api/recipes')

        params: dict[str, Any] = {
            'page': 1,
            'perPage': 10,
        }

        if search_term:
            stripped_term = search_term.strip()
            params['search'] = stripped_term

        if categories_csv:
            params['categories'] = [category.strip() for category in categories_csv.split(",")]

        if tags_csv:
            params['tags'] = [tag.strip() for tag in tags_csv.split(",")]

        response = requests.get(endpoint, headers=self.headers(), params=params)
        response.raise_for_status()

        recipes_json = response.json()
        items = recipes_json["items"]
        if len(items) == 0:
            return "No recipes found"
        else:
            recipes = ""
            for item in items:
                recipes += parse_recipe_json(item)
            return recipes

    def add_recipe_to_mealie_from_url(self, recipe_url: str, include_tags: bool = False):
        """
        Adds a recipe to Mealie from a URL of a cooking website containing the recipe.

        Use this function when you have found a recipe using Tavily and have the URL or the user has
        shared a recipe URL.

        Args:
            recipe_url (str): The URL of the recipe to add to Mealie.
            include_tags (bool, optional): Whether to include tags in the recipe. Defaults to False.

        Returns:
            str: The recipe slug of the added recipe. This can be used to update the recipe later.
        """
        body = {
            "include_tags": include_tags,
            "url": recipe_url,
        }
        response = requests.post(
            f"{self.base_url}/api/recipes/create/url",
            json=body,
            headers=self.headers()
        )
        return response.text.strip('\"')

    def get_recipe_in_mealie(self, slug: str):
        """
        Get a recipe from Mealie using its slug. This returns ingredients and instructions on the recipe.

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

        endpoint = urljoin(self.base_url, f'/api/recipes/{slug}')
        response = requests.get(endpoint, headers=self.headers())
        response.raise_for_status()

        recipe = response.json()
        return parse_recipe_json(recipe)

    def add_recipe_note(self, recipe_slug: str, note_title: str, note_text:str) -> dict:
        """Appends a new note to the given recipe in Mealie.

        Args:
            recipe_slug (str): The slug of the recipe to update.
            note_title (str): The title of the node (relevant to discussion).
            note_text (str): The text of the note (chef recommendation and summary,
                may be used for archival memory purposes).

        Returns:
            dict: The updated note.
        """

        recipe_response = requests.get(urljoin(self.base_url, f'/api/recipes/{recipe_slug}'), headers=self.headers())
        recipe_response.raise_for_status()
        recipe = recipe_response.json()
        notes = recipe["notes"]
        new_note = {
            "title": note_title,
            "text": note_text
        }
        notes.append(new_note)
        body = {
            "notes": notes
        }
        response = requests.patch(
            f"{self.base_url}/api/recipes/{recipe_slug}",
            json=body,
            headers=self.headers()
        )
        response.raise_for_status()
        return response.json()["notes"]

    def create_recipe_from_arguments(self, 
                                   name: str,                              
                                   directions: str,
                                   ingredients: str, 
                                   author: str = "",
                                   cook_time: str = "10m",
                                   prep_time: str = "10m",
                                   total_time: str = "20m",
                                   servings: str = "",
                                   source_url: str = "",
                                   description: str = "") -> str:
        """Creates a recipe in Mealie from raw text. Use this when you have Markdown or text recipes that you have to import into Mealie.

        Args:
            name (str): The name of the recipe.
            directions (str): The directions for the recipe, one direction per paragraph.
            ingredients (str): The ingredients for the recipe, one ingredient per line,
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
        recipe_dict = {
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
        recipe_json = json.dumps(recipe_dict, indent=2)

        endpoint = urljoin(self.base_url, '/api/recipes/create/html-or-json')
        response = requests.post(endpoint, json={
            "data": recipe_json,
            "includeTags": False
        }, headers=self.headers())

        response.raise_for_status()
        
        return response.text
