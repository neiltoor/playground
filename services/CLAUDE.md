# OpenRouter Integration

The Resume Comparison Tool now uses OpenRouter to provide access to multiple LLM providers.

## Supported Models

You can switch between these models by setting the `LLM_MODEL` environment variable:

### 1. **Google Gemini Flash 1.5** (Default)
- **Model ID**: `google/gemini-flash-1.5-8b`
- **Description**: Fast and efficient, great for quick comparisons
- **Cost**: Very low cost per token
- **Best for**: High-volume resume screening

### 2. **xAI Grok Beta**
- **Model ID**: `x-ai/grok-beta`
- **Description**: Fast coding-focused model from xAI
- **Cost**: Moderate cost per token
- **Best for**: Technical resume analysis

## Setup

### 1. Get an OpenRouter API Key

Visit [https://openrouter.ai/keys](https://openrouter.ai/keys) to create an account and get your API key.

### 2. Update Environment Variables

Edit your `.env` file:

```bash
# Set your OpenRouter API key
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Choose your model (default: google/gemini-flash-1.5-8b)
LLM_MODEL=google/gemini-flash-1.5-8b
```

### 3. Rebuild and Restart

```bash
docker compose down
docker compose build backend
docker compose up -d
```

## Switching Models

To switch between models without rebuilding:

```bash
# Switch to Grok
docker compose down
export LLM_MODEL=x-ai/grok-beta
docker compose up -d

# Switch to Gemini
docker compose down
export LLM_MODEL=google/gemini-flash-1.5-8b
docker compose up -d
```

Or update the `.env` file and restart:

```bash
# Edit .env and change LLM_MODEL
docker compose restart backend
```

## Verify Model Selection

Check which model is active:

```bash
curl http://localhost:8000/api/health
```

The response will include the current model in the message field.

## Cost Comparison

OpenRouter pricing varies by model. Check current rates at [https://openrouter.ai/models](https://openrouter.ai/models):

- **Gemini Flash 1.5**: Very low cost, ideal for high-volume usage
- **Grok Beta**: Moderate cost, optimized for technical content

## Troubleshooting

### API Key Not Working

Make sure your API key starts with `sk-or-v1-` and has credits available.

### Model Not Found

Verify the model ID is correct. OpenRouter model IDs are case-sensitive.

### Rate Limits

OpenRouter has rate limits based on your account tier. Check your dashboard at [https://openrouter.ai/activity](https://openrouter.ai/activity).

## Adding More Models

To add support for additional OpenRouter models:

1. Find the model ID at [https://openrouter.ai/models](https://openrouter.ai/models)
2. Update `.env` with the new model ID:
   ```bash
   LLM_MODEL=provider/model-name
   ```
3. Restart the backend:
   ```bash
   docker compose restart backend
   ```

Popular alternatives:
- `anthropic/claude-3.5-sonnet` - Anthropic Claude (higher quality, higher cost)
- `meta-llama/llama-3.1-70b-instruct` - Meta Llama (open source)
- `openai/gpt-4-turbo` - OpenAI GPT-4 Turbo
