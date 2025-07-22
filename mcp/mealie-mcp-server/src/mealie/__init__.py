from .client import MealieClient
from .group import GroupMixin
from .mealplan import MealplanMixin
from .recipe import RecipeMixin
from .user import UserMixin


class MealieFetcher(
    RecipeMixin,
    UserMixin,
    GroupMixin,
    MealplanMixin,
    MealieClient,
):
    pass
