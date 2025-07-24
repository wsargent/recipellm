from typing import Any

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

    def add_recipe_note(self, recipe_slug: str, note_title: str, note_text:str) -> str:
        """Appends a new note to the given recipe in Mealie.

        Args:
            recipe_slug (str): The slug of the recipe to update.
            note_title (str): The title of the node (relevant to discussion).
            note_text (str): The text of the note (chef recommendation and summary,
                may be used for archival memory purposes).
        """

        endpoint = urljoin(self.base_url, f'/api/recipes/{recipe_slug}')
        recipe_response = requests.get(endpoint, headers=self.headers())
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
            f"{endpoint}/api/recipes/{recipe_slug}",
            json=body,
            headers=self.headers()
        )
        response.raise_for_status()
        return response.json()["notes"]
