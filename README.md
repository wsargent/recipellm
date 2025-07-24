# RecipeLLM

Set up the system:

```
 docker compose down -v --remove-orphans && docker compose up --build
```

In another terminal, connect to the client to say hi.

```
uv run python cli_client.py  
```