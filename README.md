# RecipeLLM

This is an "out of the box" system that sets up an AI agent with a recipe manager and a notification system.

I started working on this a few months ago to [learn how to cook](https://tersesystems.com/category/llm/) and [having it find recipes](https://tersesystems.com/blog/2025/03/01/integrating-letta-with-a-recipe-manager/).

## Requirements

You will need [Docker Compose](https://docs.docker.com/compose/install/) installed.

RecipeLLM requires an API key to a reasonably powerful LLM: either OpenAI, Anthropic, or Gemini.

If you want to use Google AI Gemini models, you will need a [Gemini API key](https://ai.google.dev/gemini-api/docs/api-key).

```
LETTA_CHAT_MODEL=google_ai/gemini-2.5-flash
```

If you want to use Claude Sonnet 4, you'll want an [Anthropic API Key](https://console.anthropic.com/settings/keys).

```
LETTA_CHAT_MODEL=anthropic/claude-sonnet-4-20250514
```

If you want to use OpenAI, you'll want an [OpenAI API Key](https://platform.openai.com/api-keys).

```
LETTA_CHAT_MODEL=openai/gpt-4.1
```

You can also download recipes from the web if you have [Tavily](https://www.tavily.com/) set up.  An API key is free and you can do 1000 searches a month.

## Running

Set up the system by running docker compose

```
docker compose up --build
```

The Docker Compose images may take a while to download and run, so give them a minute.  Once they're up, you'll have three web applications running:

* Open WebUI (how you chat with the agent): [http://localhost:3000](http://localhost:3000)
* ntfy (which handles real time notifications): [http://localhost:80](http://localhost:80)
* Mealie (the recipe manager): [http://localhost:9000](http://localhost:9000)

There's also the OpenAI proxy interface if you want to connect directly to the agent:

* OpenAI API: [http://localhost:1416/v1/models](http://localhost:1416/v1/models)

## Resetting

To delete the existing data and start from scratch, you can down and delete the volume and orphans:

```
docker compose down -v --remove-orphans 
```
