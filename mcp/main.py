from fastmcp import FastMCP
import asyncio
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from fastmcp.server.proxy import ProxyClient

from letta_mcp import LettaAgent

import os
from fastmcp.client.transports import StdioTransport
import structlog
import logging


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
        logger.info("MCP Server Set up", server_list=server_list)

        logger.info("Letta server setup completed")

        # Use proxy server from mealie-mcp-server directory
        logger.info("Setting up Mealie MCP proxy")
        mealie_mcp = FastMCP.as_proxy(
            ProxyClient(transport=StdioTransport(
                command="uv",
                args=["run", "src/server.py"],
                env={
                    "MEALIE_BASE_URL": mealie_base_url,
                    "MEALIE_API_KEY": mealie_api_key
                },
                cwd="./mealie-mcp-server"
            )),
            name="Mealie Proxy"
        )
        
        # Mount the filtered server instead
        mcp.mount(mealie_mcp, prefix="mealie")
        logger.info("Mealie MCP proxy mounted successfully")
        
    except Exception as e:
        logger.error("Failed to setup server", error=str(e), exc_info=True)
        raise

@mcp.tool
async def create_chef_agent():
    letta_agent = LettaAgent()
    chef_agent_id = await letta_agent.chef_agent_id()
    if not chef_agent_id:
        chef_agent_id = await letta_agent.create_chef_agent()

    logger.info("Chef agent id", chef_agent_id=chef_agent_id)

@mcp.custom_route("/setup", methods=["POST"])
async def setup_route(request: Request) -> PlainTextResponse:
    create_chef_agent()
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