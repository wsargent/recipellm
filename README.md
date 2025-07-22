# RecipeLLM

Set up the system:

```
 docker compose down -v --remove-orphans && docker compose up --build
```

Hit the MCP server with `POST /setup` to create chef agent:

```
curl -X POST http://localhost:8000/setup
```

And from there send a message to the chef agent saying anything and you'll see the stack trace.