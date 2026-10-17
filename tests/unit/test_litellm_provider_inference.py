from pydantic import SecretStr

from openhands.app_server.utils.litellm_provider import (
    coerce_llm_api_key_for_model,
    infer_litellm_provider,
)


def test_infer_litellm_provider_bedrock_regional_model_id() -> None:
    provider = infer_litellm_provider(
        model="us.anthropic.claude-3-sonnet-20240229-v1:0",
        api_base=None,
    )
    assert provider == "bedrock"


def test_infer_litellm_provider_openai() -> None:
    provider = infer_litellm_provider(model="gpt-4o-mini", api_base=None)
    assert provider == "openai"


def test_coerce_llm_api_key_for_bedrock_model() -> None:
    forwarded_api_key = coerce_llm_api_key_for_model(
        api_key=SecretStr("sk-not-a-bedrock-token"),
        model="us.anthropic.claude-3-sonnet-20240229-v1:0",
        api_base=None,
    )
    assert forwarded_api_key is None
