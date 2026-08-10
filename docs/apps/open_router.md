The most direct way to use OpenRouter. Send standard HTTP requests to the /api/v1/chat/completions endpoint — compatible with any language or framework.

You can use the interactive Request Builder to generate OpenRouter API requests in the language of your choice.


Python

TypeScript (fetch)

Shell


import requests
import json
response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": "Bearer <OPENROUTER_API_KEY>",
    "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    "X-OpenRouter-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
  },
  data=json.dumps({
    "model": "openai/gpt-5.2",
    "messages": [
      {
        "role": "user",
        "content": "What is the meaning of life?"
      }
    ]
  })
)
The API also supports streaming. You can also use the OpenAI SDK pointed at OpenRouter as a drop-in replacement.

Using the Client SDKs
The Client SDKs wrap the OpenRouter API with full type safety, auto-generated types from the OpenAPI spec, and zero boilerplate. It is intentionally lean — a thin layer over the REST API.

First, install the SDK:


npm

yarn

pnpm

pip


npm install @openrouter/sdk
Then use it in your code:


TypeScript

Python


import OpenRouter from '@openrouter/sdk';
const client = new OpenRouter({
  apiKey: '<OPENROUTER_API_KEY>',
  defaultHeaders: {
    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.
    'X-OpenRouter-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.
  },
});
const completion = await client.chat.send({
  model: 'openai/gpt-5.2',
  messages: [
    {
      role: 'user',
      content: 'What is the meaning of life?',
    },
  ],
});
console.log(completion.choices[0].message.content);
See the full Client SDKs documentation for streaming, embeddings, and the complete API reference.

Using the Agent SDK
The Agent SDK (@openrouter/agent) provides higher-level primitives for building AI agents. It handles multi-turn conversation loops, tool execution, and state management automatically via the callModel function.

Install the package:


npm

pnpm

yarn


npm install @openrouter/agent
Build an agent with tools:

import { callModel, tool } from '@openrouter/agent';
import { z } from 'zod';
const weatherTool = tool({
  name: 'get_weather',
  description: 'Get the current weather for a location',
  inputSchema: z.object({
    location: z.string().describe('City name'),
  }),
  execute: async ({ location }) => {
    return { temperature: 72, condition: 'sunny', location };
  },
});
const result = await callModel({
  model: 'anthropic/claude-sonnet-4',
  messages: [
    { role: 'user', content: 'What is the weather in San Francisco?' },
  ],
  tools: [weatherTool],
});
const text = await result.getText();
console.log(text);


The SDK sends the prompt, receives a tool call from the model, executes get_weather, feeds the result back, and returns the final response — all in one callModel invocation.

See the full Agent SDK documentation for stop conditions, streaming, dynamic parameters, and more.

Using the OpenAI SDK
You can also use the OpenAI SDK pointed at OpenRouter as a drop-in replacement. This is useful if you have existing code built on the OpenAI SDK and want to access OpenRouter’s model catalog without changing your code structure.


Typescript

Python


import OpenAI from 'openai';
const openai = new OpenAI({
  baseURL: 'https://openrouter.ai/api/v1',
  apiKey: '<OPENROUTER_API_KEY>',
  defaultHeaders: {
    'HTTP-Referer': '<YOUR_SITE_URL>', // Optional. Site URL for rankings on openrouter.ai.
    'X-OpenRouter-Title': '<YOUR_SITE_NAME>', // Optional. Site title for rankings on openrouter.ai.
  },
});
async function main() {
  const completion = await openai.chat.completions.create({
    model: 'openai/gpt-5.2',
    messages: [
      {
        role: 'user',
        content: 'What is the meaning of life?',
      },
    ],
  });
  console.log(completion.choices[0].message);
}
main();
Using third-party SDKs
For information about using third-party SDKs and frameworks with OpenRouter, please see our frameworks documentation.

Models

Copy page

One API for hundreds of models
Explore and browse 300+ models and providers on our website, or with our API. You can also subscribe to our RSS feed to stay updated on new models.

Query Parameters
The Models API supports query parameters to filter the list of models returned.

output_modalities
Filter models by their output capabilities. Accepts a comma-separated list of modalities or "all" to include every model regardless of output type.

Value	Description
text	Models that produce text output (default)
image	Models that generate images
audio	Models that produce audio output
embeddings	Embedding models
all	Include all models, skip modality filtering
Examples:

# Default — text models only
curl "https://openrouter.ai/api/v1/models"
# Image generation models only
curl "https://openrouter.ai/api/v1/models?output_modalities=image"
# Text and image models
curl "https://openrouter.ai/api/v1/models?output_modalities=text,image"
# All models regardless of modality
curl "https://openrouter.ai/api/v1/models?output_modalities=all"


The same parameter is available on the /v1/models/count endpoint so that counts stay consistent with list results.

supported_parameters
Filter models by the API parameters they support. For example, to find models that support tool calling:

curl "https://openrouter.ai/api/v1/models?supported_parameters=tools"


Models API Standard
Our Models API makes the most important information about all LLMs freely available as soon as we confirm it.

API Response Schema
The Models API returns a standardized JSON response format that provides comprehensive metadata for each available model. This schema is cached at the edge and designed for reliable integration with production applications.

Root Response Object
{
  "data": [
    /* Array of Model objects */
  ]
}


Model Object Schema
Each model in the data array contains the following standardized fields:

Field	Type	Description
id	string	Unique model identifier used in API requests (e.g., "google/gemini-2.5-pro-preview")
canonical_slug	string	Permanent slug for the model that never changes
name	string	Human-readable display name for the model
created	number	Unix timestamp of when the model was added to OpenRouter
description	string	Detailed description of the model’s capabilities and characteristics
context_length	number	Maximum context window size in tokens
architecture	Architecture	Object describing the model’s technical capabilities
pricing	Pricing	Lowest price structure for using this model
top_provider	TopProvider	Configuration details for the primary provider
per_request_limits	Rate limiting information (null if no limits)	
supported_parameters	string[]	Array of supported API parameters for this model
default_parameters	object | null	Default parameter values for this model (null if none)
expiration_date	string | null	Deprecation date for the model endpoint (null if not deprecated)
Architecture Object
{
  "input_modalities": string[], // Supported input types: ["file", "image", "text"]
  "output_modalities": string[], // Supported output types: ["text"]
  "tokenizer": string,          // Tokenization method used
  "instruct_type": string | null // Instruction format type (null if not applicable)
}


Pricing Object
All pricing values are in USD per token/request/unit. A value of "0" indicates the feature is free.

{
  "prompt": string,           // Cost per input token
  "completion": string,       // Cost per output token
  "request": string,          // Fixed cost per API request
  "image": string,           // Cost per image input
  "web_search": string,      // Cost per web search operation
  "internal_reasoning": string, // Cost for internal reasoning tokens
  "input_cache_read": string,   // Cost per cached input token read
  "input_cache_write": string   // Cost per cached input token write
}


Top Provider Object
{
  "context_length": number,        // Provider-specific context limit
  "max_completion_tokens": number, // Maximum tokens in response
  "is_moderated": boolean         // Whether content moderation is applied
}


Supported Parameters
The supported_parameters array indicates which OpenAI-compatible parameters work with each model:

tools - Function calling capabilities
tool_choice - Tool selection control
max_tokens - Response length limiting
temperature - Randomness control
top_p - Nucleus sampling
reasoning - Internal reasoning mode
include_reasoning - Include reasoning in response
structured_outputs - JSON schema enforcement
response_format - Output format specification
stop - Custom stop sequences
frequency_penalty - Repetition reduction
presence_penalty - Topic diversity
seed - Deterministic outputs
Different models tokenize text in different ways
Some models break up text into chunks of multiple characters (GPT, Claude, Llama, etc), while others tokenize by character (PaLM). This means that token counts (and therefore costs) will vary between models, even when inputs and outputs are the same. Costs are displayed and billed according to the tokenizer for the model in use. You can use the usage field in the response to get the token counts for the input and output.

If there are models or providers you are interested in that OpenRouter doesn’t have, please tell us about them in our Discord channel.

For Providers
If you’re interested in working with OpenRouter, you can learn more on our providers page.