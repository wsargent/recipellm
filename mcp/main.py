import asyncio
import json
import logging
import os
from typing import Optional

import httpx
import structlog
from fastmcp import FastMCP
from fastmcp.client.transports import StdioTransport
from fastmcp.server.proxy import ProxyClient
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from letta_mcp import LettaAgent
from mealie_mcp import MealieMCP

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.dev.ConsoleRenderer(colors=True)
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()

# Token storage
TOKEN_FILE = "/app/data/mealie_api_token.json"

def save_api_token(token: str, token_data: dict):
    """Save API token to persistent storage"""
    try:
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            json.dump({
                "token": token,
                "token_data": token_data
            }, f)
        logger.info("API token saved successfully", file=TOKEN_FILE)
    except Exception as e:
        logger.error("Failed to save API token", error=str(e))

def load_api_token() -> Optional[str]:
    """Load API token from persistent storage"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
                logger.info("API token loaded successfully")
                return data.get("token")
    except Exception as e:
        logger.error("Failed to load API token", error=str(e))
        return None

async def validate_api_token(mealie_base_url: str, token: str) -> bool:
    """Validate that the API token is still working"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{mealie_base_url}/api/users/self",
                headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 200:
                logger.info("API token validation successful")
                return True
            else:
                logger.warning("API token validation failed", status_code=response.status_code)
                return False
    except Exception as e:
        logger.error("Error validating API token", error=str(e))
        return False

async def get_auth_token(mealie_base_url: str, username: str, password: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{mealie_base_url}/api/auth/token",
                data={
                    "username": username,
                    "password": password
                },
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
            )

            json_response = response.json()
            auth_token = json_response["access_token"]
            return auth_token
    except Exception as e:
        logger.error("Error creating Mealie Auth token", error=str(e), exc_info=True)
        return None

async def create_mealie_api_token(mealie_base_url: str, auth_token: str) -> Optional[str]:
    """Create an API token in Mealie using authenticated API"""
    try:
        async with httpx.AsyncClient() as client:
            token_data = {
                "name": "API Token for RecipeLLM",
                "integration_id": "generic"
            }

            response = await client.post(
                f"{mealie_base_url}/api/users/api-tokens",
                json=token_data,
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {auth_token}"       
                }
            )

            if response.status_code == 201:
                token_response = response.json()
                api_token = token_response.get("token")
                if api_token:
                    save_api_token(api_token, token_response)
                    logger.info("Successfully created and saved Mealie API token")
                    return api_token
                else:
                    logger.error("API token not found in response", response=token_response)
                    return None
            else:
                logger.error("Failed to create Mealie API token", 
                           status_code=response.status_code, 
                           response=response.text)
                return None
                
    except Exception as e:
        logger.error("Error creating Mealie API token", error=str(e), exc_info=True)
        return None

# Create main server
mcp = FastMCP("Main", 
    instructions="""
        This server provides data analysis tools and Mealie recipe management.
        Use mealie_ prefixed tools to interact with the Mealie recipe server.
    """)

@mcp.custom_route("/health", methods=["GET"])
async def health_check(_: Request) -> PlainTextResponse:
    logger.debug("Health check requested")
    return PlainTextResponse("OK")

async def setup(mealie_base_url, mealie_api_key, recipellm_mcp_server_url):
    try:
        logger.info("Starting server setup", 
                   mealie_base_url=mealie_base_url,
                   recipellm_mcp_server_url=recipellm_mcp_server_url)

        letta_agent = LettaAgent()
        server_list = await letta_agent.setup_mcp_server(recipellm_mcp_server_url)
        logger.info("Setup Letta server with server_list")

        # Try to load existing API token
        api_token = load_api_token()
        
        # If token exists, validate it
        if api_token:
            logger.info("Found existing API token, validating...")
            if not await validate_api_token(mealie_base_url, api_token):
                logger.info("Existing token is invalid, creating new one")
                api_token = None
        
        # If no token exists or validation failed, create a new one
        if not api_token:
            logger.info("Creating new API token")
            auth_token = await get_auth_token(mealie_base_url=mealie_base_url,
                                               username="changeme@example.com",
                                               password="MyPassword")
            api_token = await create_mealie_api_token(
                mealie_base_url=mealie_base_url, 
                auth_token=auth_token
            )
        else:
            logger.info("Using existing valid API token")
        
        # Use the API token (either loaded or newly created)
        if api_token:
            # Update the environment variable for the MCP server
            os.environ["MEALIE_API_KEY"] = api_token
            mealie_api_key = api_token
            logger.info("API token set for MCP server use")
        else:
            logger.error("No API token available, using fallback from environment")
            # Keep using the original mealie_api_key from environment

        # Initialize MealieMCP instance and register tools
        mealie_client = MealieMCP(mealie_base_url, mealie_api_key)
        
        @mcp.tool
        async def find_recipes_in_mealie(
            search_term: str,
            categories_csv: str = None,
            tags_csv: str = None
        ) -> str:
            """
            Search for recipes in Mealie using various filters.

            Args:
                search_term (str): The string to search for, i.e. "chicken"
                categories_csv (str, optional): Comma separated list of category names or slugs to filter by
                tags_csv (str, optional): Comma seperated list of tag names or slugs to filter by

            Returns:
                str: The list of recipes, or "No recipes found" if no recipes are found.
            """
            return mealie_client.find_recipes_in_mealie(search_term, categories_csv, tags_csv)

        @mcp.tool
        async def add_recipe_to_mealie_from_url(
            recipe_url: str,
            include_tags: bool = False
        ) -> str:
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
            return mealie_client.add_recipe_to_mealie_from_url(recipe_url, include_tags)

        @mcp.tool
        async def get_recipe_in_mealie(slug: str) -> str:
            """
            Get a recipe from Mealie using its slug. This returns ingredients and instructions on the recipe.

            Args:
                slug (str): The slug of the recipe to retrieve.

            Returns:
                str: The text of the recipe.
            """
            return mealie_client.get_recipe_in_mealie(slug)

    except Exception as e:
        logger.error("Failed to setup server", error=str(e), exc_info=True)
        raise

async def create_chef_agent():
    letta_agent = LettaAgent()
    chef_agent_id = await letta_agent.chef_agent_id()
    if not chef_agent_id:
        chef_agent_id = await letta_agent.create_chef_agent()

    logger.info("Chef agent id", chef_agent_id=chef_agent_id)

@mcp.custom_route("/setup", methods=["POST"])
async def setup_route(_: Request) -> PlainTextResponse:
    # Create chef agent
    letta_agent = LettaAgent()
    chef_agent_id = await letta_agent.chef_agent_id()
    if not chef_agent_id:
        chef_agent_id = await letta_agent.create_chef_agent()
    logger.info("Chef agent id", chef_agent_id=chef_agent_id)
    
    return PlainTextResponse("OK")

# Use "python main.py" -- don't use "fastmcp run" as it won't pick up the transport
if __name__ == "__main__":
    try:
        logger.info("Starting RecipeLLM MCP Server")
        
        mealie_base_url = os.getenv("MEALIE_BASE_URL")
        mealie_api_key = os.getenv("MEALIE_API_KEY")
        recipellm_mcp_server_url = os.getenv("RECIPELLM_MCP_SERVER_URL")
        
        # Validate required environment variables
        if not mealie_base_url:
            logger.error("MEALIE_BASE_URL environment variable is required")
            exit(1)
        if not mealie_api_key:
            logger.error("MEALIE_API_KEY environment variable is required")
            exit(1)
        if not recipellm_mcp_server_url:
            logger.error("RECIPELLM_MCP_SERVER_URL environment variable is required")
            exit(1)
            
        logger.info("Environment variables loaded successfully")
        
        asyncio.run(setup(mealie_base_url, mealie_api_key, recipellm_mcp_server_url))
        
        logger.info("Starting HTTP server on port 8000")
        mcp.run(transport="sse", host="0.0.0.0", port=8000)
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error("Failed to start server", error=str(e), exc_info=True)
        exit(1)