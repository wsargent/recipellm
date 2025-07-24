import re
import requests
import os
import json

import logging

#logging.basicConfig(level=logging.DEBUG)

def update_recipe_categories(recipe_slug: str, categories_csv: str) -> None:
    """Updates a recipe in Mealie with the given categories.

    Args:
        recipe_slug (str): The slug of the recipe to update.
        categories_csv (str): A comma-separated list of categories to add to the recipe.
    """

    logger = logging.getLogger(__name__)

    endpoint = os.getenv("MEALIE_ENDPOINT")
    api_key = os.getenv("MEALIE_API_KEY")
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key
    }

    def to_slug(text):
        return re.sub(r'[^a-zA-Z0-9]+', '-', text.strip()).lower()

    def printd(data):
        print(json.dumps(data, indent=4, sort_keys=True))

    def get_categories() -> list:
        """
        Gets all categories in Mealie.

        Returns:
            list: A list of categories.
        """
        response = requests.get(
            f"{endpoint}/api/organizers/categories",
            params={
                "perPage": 1000
            },
            headers = headers
        )
        response.raise_for_status()
        return response.json()["items"]


    def create_category(name: str) -> dict:
        """
        Creates a new category in Mealie.

        Parameters
        ----------
        name : str
            The name of the category to create.

        Returns
        -------
        dict
            The created category.
        """
        body = {
            "name": name
        }
        response = requests.post(
            f"{endpoint}/api/organizers/categories",
            json=body,
            headers = headers
        )
        response.raise_for_status()
        #     {
        #   "name": "new category",
        #   "id": "7fe3b1d7-b2ab-47b9-945d-822492f4f93c",
        #   "slug": "new-category",
        #   "groupId": "f9fbf353-f4fa-494c-879c-e9a42ae1db6f"
        # }
        return response.json()
        
    def find_category_by_name(categories: list, category_name: str) -> dict:
        """
        Finds a category by name.

        Parameters
        ----------
        categories : list
            The list of categories to search through.
        category_name : str
            The name of the category to find.
        
        Returns
        -------
        dict
            The category, or None if it doesn't exist.
        """
        category_slug = to_slug(category_name)
        for category in categories:
            #logger.info("category = %s, category_slug = %s", category["slug"], category_slug)
            if category["slug"] == category_slug:
                return category
        return None

    def set_recipe_categories(recipe_slug: str, categories: list) -> list:
        """
        Sets the categories for a recipe.
        Parameters
        ----------
        recipe_slug : str
            The slug of the recipe to set the categories for.
        category_names : list
            The names of the categories to set for the recipe.
        Returns
        -------
            list: the list of categories for the recipe.
        """ 

        #printd(categories)
        body = {
            "recipeCategory": categories
        }
        response = requests.patch(
            f"{endpoint}/api/recipes/{recipe_slug}",
            json=body,
            headers = headers
        )
        response.raise_for_status()
        #print(f"response_code = {response.status_code}")
        
        patched_recipe = response.json()
        if patched_recipe is not None:
            return patched_recipe["recipeCategory"]
        return categories


    def get_recipe_categories(recipe_slug: str) -> list:
        """
        Gets the categories for a recipe.

        Parameters
        ----------
        recipe_slug : str
            The slug of the recipe to get the categories for.

        Returns
        -------
            list: the list of categories for the recipe.
        """

        recipe_response = requests.get(
            f"{endpoint}/api/recipes/{recipe_slug}",
            headers = headers
        )
        recipe_response.raise_for_status()
        recipe = recipe_response.json()
        return recipe["recipeCategory"]

    
    categories_names = categories_csv.split(",")
    categories = get_categories()
    recipe_categories = get_recipe_categories(recipe_slug)
    for category_name in categories_names:
        # skip categories that are already set
        if (find_category_by_name(recipe_categories, category_name) is not None):
            logger.info(f"Skipping already added category {category_name} to recipe {recipe_slug}")
            continue

        existing_category = find_category_by_name(categories, category_name)
        if existing_category is None:
            logger.info(f"Adding new category {category_name} to recipe {recipe_slug}")
            new_category = create_category(category_name)
            recipe_categories.append(new_category)
        else:
            logger.info(f"Adding existing category {category_name} to recipe {recipe_slug}")
            recipe_categories.append(existing_category)
        
    set_recipe_categories(recipe_slug, recipe_categories)
    return recipe_categories
