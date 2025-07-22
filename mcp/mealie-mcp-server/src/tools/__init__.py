from .mealplan_tools import register_mealplan_tools
from .recipe_tools import register_recipe_tools


def register_all_tools(mcp, mealie):
    """Register all tools with the MCP server."""
    register_recipe_tools(mcp, mealie)
    register_mealplan_tools(mcp, mealie)


__all__ = [
    "register_all_tools",
    "register_recipe_tools",
    "register_mealplan_tools",
]
