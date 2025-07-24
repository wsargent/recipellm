import re
import requests
import os
import json

def update_recipe_tags(recipe_slug: str, tags_csv: str) -> dict:
    """Updates a recipe in Mealie with the given tags.

    Args:
        recipe_slug (str): The slug of the recipe to update.
        tags_csv (str): A comma separated list of tags to add to the recipe.

    Returns:
        dict: The tags.
    """

    endpoint = os.getenv("MEALIE_ENDPOINT")
    api_key = os.getenv("MEALIE_API_KEY")
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key
    }

    def snake_case(text):
        # Replace spaces and other separators with underscores and convert to lowercase
        return re.sub(r'[^a-zA-Z0-9]+', '_', text).lower()

    def printd(data):
        print(json.dumps(data, indent=4, sort_keys=True))


    def get_tags() -> list:
        """
        Gets all tags in Mealie.

        Returns:
            list: A list of tags.
        """
        response = requests.get(
            f"{endpoint}/api/organizers/tags",
            params={
                "page": 1,
                "perPage": 1000
            },
            headers = headers
        )
        response.raise_for_status()
        return response.json()["items"]


    def create_tag(name: str):
        """
        Creates a new tag.

        Parameters
        ----------
        name : str
            The name of the tag to create.

        Returns
        -------
        dict
            The created tag.
        """
        body = {
            "name": name
        }
        response = requests.post(
            f"{endpoint}/api/organizers/tags",
            json=body,
            headers = headers
        )
        response.raise_for_status()

        # {
        #   "name": "new tag",
        #   "groupId": "f9fbf353-f4fa-494c-879c-e9a42ae1db6f",
        #   "id": "e282c0ca-c3cf-408a-a668-2fd5307898dd",
        #   "slug": "new-tag"
        # }
        return response.json()


    def get_recipe_tags(recipe_slug: str) -> list:
        """
        Gets the tags for a recipe.

        Parameters
        ----------
        recipe_slug : str
            The slug of the recipe to get.
            
        Returns
        -------
            list: the recipe's tags.
        """
        recipe_response = requests.get(
            f"{endpoint}/api/recipes/{recipe_slug}",
            headers = headers
        )
        recipe_response.raise_for_status()
        recipe = recipe_response.json()
        return recipe["tags"]


    def set_recipe_tags(recipe_slug: str, tags: list) -> list:
        """
        Sets the tags for a recipe.

        Parameters
        ----------
        recipe_slug : str
            The slug of the recipe to update.
        tags : list
            The tags to set for the recipe.

        Returns
        -------
            list: the tags that were set for the recipe.
        """
        body = {
            "tags": tags
        }
        response = requests.patch(
            f"{endpoint}/api/recipes/{recipe_slug}",
            json=body,
            headers = headers
        )
        response.raise_for_status()
        patched_recipe = response.json()
        if patched_recipe is not None:
            return patched_recipe["tags"]
        return tags


    def get_or_create_tag(tag_name) -> dict:
        """
        Gets a tag by name. If the tag does not exist, it will be created.
        
        Parameters
        ----------
        tag_name : str
            The name of the tag to get or create.

        Returns
        -------
            dict: the tag.
        """
        all_tags = get_tags()
        for tag in all_tags:
            if (tag["name"] == snake_case(tag_name)):
                return tag
        return create_tag(tag_name)
            

    def add_tag_to_recipe(recipe_slug: str, new_tag_name: str) -> list:
        """
        Adds a tag to a recipe. If the tag already exists, it will not be added again.
        
        Parameters
        ----------
        recipe_slug : str
            The slug of the recipe to add the tag to.
        new_tag_name : str
            The name of the tag to add to the recipe.

        Returns
        -------
            list: the list of tags for the recipe.
        """
        tags = get_recipe_tags(recipe_slug)    
        for tag in tags:
            # If the tag already exists, return the tags
            if (tag["name"] == new_tag_name):
                return tags
        
        new_tag = get_or_create_tag(new_tag_name)
        tags.append(new_tag)
        return set_recipe_tags(recipe_slug, tags)


  
    def get_recipe_notes(recipe_slug: str) -> list:
        """
        Gets the notes for a recipe.

        Parameters
        ----------
        recipe_slug : str
            The slug of the recipe to get the notes for.

        Returns
        -------
        list
            The list of notes for the recipe.
        """

        recipe_response = requests.get(
            f"{endpoint}/api/recipes/{recipe_slug}",
            headers = headers
        )
        recipe_response.raise_for_status()
        recipe = recipe_response.json()
        return recipe["notes"]


    def add_note_to_recipe(slug: str, note_title: str, note_text: str) -> list: 
        """
        Adds a note to a recipe. If the recipe already has a note with the same title, it will be overwritten.

        Parameters
        ----------
        slug : str
            The slug of the recipe to add the note to.
        note_title : str
            The title of the note to add.
        note_text : str
            The text of the note to add.

        Returns
        -------
        list
            The list of notes.
        """

        notes = get_recipe_notes(slug)
        new_note = {
            "title": note_title,
            "text": note_text
        }
        notes.append(new_note)
        body = {
            "notes": notes
        }
        response = requests.patch(
            f"{endpoint}/api/recipes/{slug}",
            json=body, 
            headers = headers
        )
        response.raise_for_status()
        return response.json()["notes"]

    tags = tags_csv.split(",")
    
    for tag in tags:
        add_tag_to_recipe(recipe_slug, tag.strip())

    return tags
