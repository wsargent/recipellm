from letta_client.types.sse_server_config import SseServerConfig
from letta_client import LettaEnvironment
from letta_client import AsyncLetta
import os
from typing import Optional

import datetime
from typing import Dict, List, Optional

from letta_client import (
    CreateBlock,
    LlmConfig,
)
from letta_client.types import Tool

import structlog

logger = structlog.get_logger()

DEFAULT_LETTA_MODEL = "letta/letta-free"

DEFAULT_LETTA_EMBEDDING = "letta/letta-free"

CHEF_AGENT_NAME = "chef-agent"

DEFAULT_RETURN_CHAR_LIMIT = 6000

CHEF_PERSONA = """
You are an experienced chef who is training and educating an inexperienced cook in the kitchen.  Your cook will ask you to help out with a recipe, and you will provide context and step by step instructions for your chef.

## Principles

Encourage prep work and mise en place. Encourage principles for efficient cooking:

Start long processes first (preheating, boiling water)
Group similar tasks (all chopping together)
Clean as you go during passive cooking time
Have all ingredients ready before starting active cooking

## Time Management

Your cook may need extra help at prepping and time management, especially understanding which parts of the instructions can be done in parallel and which should be done serially.

Take into account how long it take for water to boil (more water will take longer), and for the oven to preheat, but do not include appliances when they are not necessary in the recipe.  Any step involving passive cooking (baking or simmering) is a good place to look for parallel activities.
Any step involving active cooking or being in front of a stove (sautéing, grilling, stir-fry) requires your cook's full attention and so cannot be done in parallel.

## Recipe Planning

Planning may involve both a main dish and a side dish.  

At the beginning, review both recipes and create a clear timeline covering both dishes, identifying:

* Prep work for both dishes
* Marination or other waiting periods
* Active cooking times
* Passive cooking times

Organize tasks in order:

* Start with the dish that takes longest (including marination)
* Use marination or passive cooking time to prep the second dish
* Plan when to start cooking the side dish so it finishes with the main
* Be explicit about opportunities for parallel work, saying things like "While the chicken marinates, let's prep the carrots."

##Archival memory

Record significant events and important information using archival_memory_insert so you can access those memories later.  

For example, when cooking a recipe, record the recipe name, slug and the context of the conversation.  Record any changes you've made to core memory.

Always add a timestamp in the format format `YYYY-MM-DDThh:mm:ssX` (X indicating timezone offset) when using archival_memory_insert.

If your chef asks you about something you don't know, perform an archival_memory_search.

## Mealie

Mealie is a recipe manager and meal planner.  

When you add a new recipe to Mealie:

* Add a note summarizing your cooking recommendations for the user.
* Add the recipe slug, recipe name, and a brief description to your archival memory for later reference.

## Recipe Search

When your cook is looking for information that you don't have, such as recipes, ingredients, or expiration dates on food, use the web_search function and let your cook know you are looking it up. 

Search results can be unreliable. If you find an appropriate recipe, save it to Mealie *first* and then get the recipe details from the recipe slug to validate the recipe.


## Memory Search Protocol

When the user asks about something I don't immediately know or references previous conversations, always search BOTH conversational memory AND archival memory before responding. This ensures I have full context and don't miss important details from our cooking sessions.
"""

# https://docs.letta.com/llms.txt

# https://docs.letta.com/guides/agents/multi-agent.md
# https://github.com/letta-ai/letta-python/blob/HEAD/reference.md

# This can't be right, there is no `send_message_async` method
# https://docs.letta.com/guides/agents/multi-agent-custom-tools.md
class LettaAgent:

    def __init__(self) -> None:
        self.client = self._get_letta()        
        return

    def _get_letta(self) -> AsyncLetta:
        base_url = os.getenv("LETTA_BASE_URL")
        token = os.getenv("LETTA_TOKEN")
        environment = LettaEnvironment.SELF_HOSTED
        project = None

        async_letta = AsyncLetta(base_url=base_url, environment=environment, project=project, token=token)
        return async_letta
    
    def _default_letta_model(self) -> str:
        return DEFAULT_LETTA_MODEL
    
    def _default_letta_embedding(self) -> str:
        return DEFAULT_LETTA_EMBEDDING

    async def chef_agent_id(self) -> Optional[str]:
        agents = await self.client.agents.list(name=CHEF_AGENT_NAME)
        if len(agents) == 0:
            return None
        else:
            return agents[0].id

    async def create_chef_agent(self) -> str:
        logger.info("Creating chef agent")
        
        timezone = "UTC"
        letta_model = self._default_letta_model()
        letta_embedding = self._default_letta_embedding()
        requested_tools = [
            "find_recipes_in_mealie",
            "add_recipe_to_mealie_from_url",
            "get_recipe_in_mealie"
        ]
        env_vars = {}

        agent_id = await self._create_agent(
            agent_name=CHEF_AGENT_NAME, 
            human_block_content="", 
            persona_block_content=CHEF_PERSONA, 
            letta_model=letta_model,
            letta_embedding=letta_embedding,
            requested_tools=requested_tools,
            timezone=timezone,
            tool_exec_environment_variables=env_vars
        )

        return agent_id

    async def _create_agent(
            self, 
            agent_name: str, 
            human_block_content: str, 
            persona_block_content: str,
            letta_model: str, 
            letta_embedding: str, 
            requested_tools: List[str],
            timezone: str, 
            tool_exec_environment_variables: dict
        ) -> str:
        """Creates a new Letta agent with the specified configuration and tools.

        Args:
        ----
        agent_name:
            The name for the new agent.
        human_block_content:
            Content for the 'human' memory block.
        persona_block_content:
            Content for the 'persona' memory block.
        letta_model:
            The identifier for the chat model.
        letta_embedding:
            The identifier for the embedding model.
        requested_tools:
            The requested tools to attach to the agent upon creation.
        timezone:
            The agent's timezone
        tool_exec_environment_variables:
            Tool environment variables.

        Returns:
        -------
        str:
            The ID of the newly created agent.

        Raises:
        ------
        ValueError:
            If the specified chat model is not available.
        RuntimeError:
            If agent creation fails for other reasons.

        """
        memory_blocks = [
            CreateBlock(
                value=human_block_content,
                label="human",
                limit=self._set_block_limit(human_block_content),
            ),
            CreateBlock(
                value=persona_block_content,
                label="persona",
                limit=self._set_block_limit(persona_block_content),
            ),
        ]

        tool_ids = await self._find_tools_id(requested_tools)
        available_llms: List[LlmConfig] = await self.client.models.list()
        available_model_names = {llm.handle for llm in available_llms}

        if letta_model in available_model_names:
            selected_model = letta_model
            logger.info(f"Using configured LETTA_MODEL: {selected_model}")
        else:
            raise ValueError(f"Model {letta_model} not found in available models: {available_model_names}")

        # Use reasoning model if we got it (gemini 2.5 pro does not support)
        enable_reasoner = None
        max_reasoning_tokens = None
        max_tokens = None
        enable_sleeptime = False # https://github.com/letta-ai/letta/issues/2694 prevents this from working

        # Still not sure if reasoning model is an advantage here
        # if "claude-3-7-sonnet" in selected_model:
        #     enable_reasoner = True
        #     max_reasoning_tokens = 1024
        #     max_tokens = 8192

        # Is there a way to set the context window size from here?
        # https://github.com/letta-ai/letta-python/blob/main/reference.md
        agent = await self.client.agents.create(
            name=agent_name,
            memory_blocks=memory_blocks,
            model=selected_model,
            embedding=letta_embedding,
            enable_reasoner=enable_reasoner,
            max_reasoning_tokens=max_reasoning_tokens,
            max_tokens=max_tokens,
            tool_ids=tool_ids,
            enable_sleeptime=enable_sleeptime,
            timezone=timezone,
            tool_exec_environment_variables=tool_exec_environment_variables,
        )
        logger.info(f"Successfully created agent '{agent_name}' (ID: {agent.id}) with {len(tool_ids)} tools.")
        # Add a note so we can see when it was created
        # self.client.agents.passages.create(
        #     agent_id=agent.id,
        #     text=f"Created at {datetime.datetime.now()}Z",
        # )
        return agent.id

    def _set_block_limit(self, block_content: str) -> int:
        if block_content is None:
            return 5000
        if len(block_content) < 5000:
            return 5000
        return len(block_content) + 1000

    async def _find_tool(self, name: str) -> Optional[Tool]:
        # List tools from an MCP server
        #tools = self.client.tools.list_mcp_tools_by_server(mcp_server_name="recipellm-mcp")
        # Add a specific tool from the MCP server
        tool = await self.client.tools.add_mcp_tool(
            mcp_server_name="recipellm-mcp",
            mcp_tool_name=name
        )
        return tool

    async def _find_tools_id(self, requested_tools: List[str]) -> List[str]:
        found_tools = []
        for tool_name in requested_tools:
            tool = await self._find_tool(tool_name)
            if tool is not None:
                found_tools.append(tool.id)
            else:
                logger.warning(f"Could not find tool '{tool_name}'")
        return found_tools

    async def setup_mcp_server(self, letta_mcp_server_url: str) -> list:                
        servers_dict = await self.client.tools.list_mcp_servers()
        server = servers_dict.get("recipellm-mcp")
        if server:
            return server
        else:
            streamable_config = SseServerConfig(
                server_name="recipellm-mcp",
                server_url=letta_mcp_server_url       
            )
            return await self.client.tools.add_mcp_server(request=streamable_config)
