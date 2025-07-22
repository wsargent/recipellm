import asyncio
from fastmcp import Client

client = Client("http://localhost:8000/mcp/")

async def main():
    async with client:
        # Basic server interaction
        await client.ping()
        
        # List available operations
        tools = await client.list_tools()

        if len(tools) == 0:
            print("No tools found!")

        for tool in tools:
            print(tool)


if __name__ == "__main__":
    asyncio.run(main())