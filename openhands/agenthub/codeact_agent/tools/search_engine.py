from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

_SEARCH_ENGINE_DESCRIPTION = """Execute a web search query (similar to Google search).

NOTE: When you need to search for information online, please use the `search_engine` tool rather than the `browser` or `web_read` tools. The `search_engine` tool connects directly to a search engine, which will help avoid CAPTCHA challenges that would otherwise block your access.
"""

SearchEngineTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='search_engine',
        description=_SEARCH_ENGINE_DESCRIPTION,
        parameters={
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': 'The web search query (must be a non-empty string).',
                },
                'start_date': {
                    'type': 'string',
                    'description': 'Optional parameter to retrieve only those links published after the date specified by the start_date parameter. The start_date string MUST be specified in ISO 8601 format. Example formats: "2023-12-17T00:00:00.000Z" OR "2024-01-01"',
                },
            },
            'required': ['query'],
        },
    ),
)
