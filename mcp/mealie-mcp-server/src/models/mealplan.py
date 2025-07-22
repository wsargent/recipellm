from typing import Optional

from pydantic import BaseModel


class MealPlanEntry(BaseModel):
    date: str
    recipe_id: Optional[str] = None
    title: Optional[str] = None
    entry_type: str = "breakfast"
