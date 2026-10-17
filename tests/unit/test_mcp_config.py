import pytest
from pydantic import ValidationError

from openhands.core.config.mcp_config import MCPConfig, MCPSSEConfig, MCPStdioConfig


def test_valid_sse_config():
    """Test a valid SSE configuration."""
    config = MCPSSEConfig(mcp_servers=['http://server1:8080', 'http://server2:8080'])
    config.validate_servers()  # Should not raise any exception


def test_empty_sse_config():
    """Test SSE configuration with empty servers list."""
    config = MCPSSEConfig(mcp_servers=[])
    config.validate_servers()


def test_invalid_sse_url():
    """Test SSE configuration with invalid URL format."""
    config = MCPSSEConfig(mcp_servers=['not_a_url'])
    with pytest.raises(ValueError) as exc_info:
        config.validate_servers()
    assert 'Invalid URL' in str(exc_info.value)


def test_duplicate_sse_urls():
    """Test SSE configuration with duplicate server URLs."""
    config = MCPSSEConfig(mcp_servers=['http://server1:8080', 'http://server1:8080'])
    with pytest.raises(ValueError) as exc_info:
        config.validate_servers()
    assert 'Duplicate MCP server URLs are not allowed' in str(exc_info.value)


def test_valid_stdio_config():
    """Test a valid stdio configuration."""
    config = MCPStdioConfig(
        commands=['python', 'python3'],
        args=[['-m', 'server1'], ['-m', 'server2']],
        envs=[[('KEY1', 'value1')], [('KEY2', 'value2')]],
    )
    config.validate_stdio()  # Should not raise any exception


def test_empty_stdio_config():
    """Test stdio configuration with empty commands list."""
    config = MCPStdioConfig(commands=[], args=[], envs=[])
    config.validate_stdio()


def test_mismatched_stdio_lengths():
    """Test stdio configuration with mismatched number of commands and args."""
    config = MCPStdioConfig(
        commands=['python', 'python3'],
        args=[['-m', 'server1']],  # Only one args list for two commands
        envs=[[('KEY1', 'value1')], [('KEY2', 'value2')]],
    )
    with pytest.raises(ValueError) as exc_info:
        config.validate_stdio()
    assert 'Number of commands (2) does not match number of args lists (1)' in str(
        exc_info.value
    )


def test_mismatched_envs_lengths():
    """Test stdio configuration with mismatched number of commands and envs."""
    config = MCPStdioConfig(
        commands=['python', 'python3'],
        args=[['-m', 'server1'], ['-m', 'server2']],
        envs=[[('KEY1', 'value1')]],  # Only one envs list for two commands
    )
    with pytest.raises(ValueError) as exc_info:
        config.validate_stdio()
    assert 'Number of commands (2) does not match number of envs lists (1)' in str(
        exc_info.value
    )


def test_invalid_env_tuple_format():
    """Test stdio configuration with invalid environment variable tuple format."""
    with pytest.raises(ValidationError) as exc_info:
        MCPStdioConfig(
            commands=['python'],
            args=[['-m', 'server1']],
            envs=[[('KEY1', 'value1', 'extra')]],  # Invalid tuple with 3 elements
        )
    assert 'Tuple should have at most 2 items' in str(exc_info.value)


def test_invalid_env_tuple_types():
    """Test stdio configuration with invalid environment variable types."""
    with pytest.raises(ValidationError) as exc_info:
        MCPStdioConfig(
            commands=['python'],
            args=[['-m', 'server1']],
            envs=[[(123, 'value1')]],  # Invalid key type (integer instead of string)
        )
    assert 'Input should be a valid string' in str(exc_info.value)


def test_valid_combined_config():
    """Test a valid combined MCP configuration with both SSE and stdio."""
    MCPConfig(
        sse=MCPSSEConfig(mcp_servers=['http://server1:8080']),
        stdio=MCPStdioConfig(
            commands=['python'], args=[['-m', 'server1']], envs=[[('KEY1', 'value1')]]
        ),
    )
    # Should not raise any exception


def test_from_toml_section_valid():
    """Test creating config from valid TOML section."""
    data = {
        'mcp-sse': {'mcp_servers': ['http://server1:8080']},
        'mcp-stdio': {
            'commands': ['python'],
            'args': [['-m', 'server1']],
            'envs': [[('KEY1', 'value1')]],
        },
    }
    result = MCPConfig.from_toml_section(data)
    assert 'mcp' in result
    assert result['mcp'].sse.mcp_servers == ['http://server1:8080']
    assert result['mcp'].stdio.commands == ['python']
    assert result['mcp'].stdio.args == [['-m', 'server1']]
    assert result['mcp'].stdio.envs == [[('KEY1', 'value1')]]


def test_from_toml_section_invalid_sse():
    """Test creating config from TOML section with invalid SSE URL."""
    data = {
        'mcp-sse': {'mcp_servers': ['not_a_url']},
        'mcp-stdio': {
            'commands': ['python'],
            'args': [['-m', 'server1']],
            'envs': [[('KEY1', 'value1')]],
        },
    }
    with pytest.raises(ValueError) as exc_info:
        MCPConfig.from_toml_section(data)
    assert 'Invalid URL' in str(exc_info.value)


def test_from_toml_section_invalid_stdio():
    """Test creating config from TOML section with mismatched stdio config."""
    data = {
        'mcp-sse': {'mcp_servers': ['http://server1:8080']},
        'mcp-stdio': {
            'commands': ['python', 'python3'],
            'args': [['-m', 'server1']],  # Only one args list for two commands
            'envs': [[('KEY1', 'value1')], [('KEY2', 'value2')]],
        },
    }
    with pytest.raises(ValueError) as exc_info:
        MCPConfig.from_toml_section(data)
    assert 'Number of commands (2) does not match number of args lists (1)' in str(
        exc_info.value
    )


def test_complex_urls():
    """Test SSE configuration with complex URLs."""
    config = MCPSSEConfig(
        mcp_servers=[
            'https://user:pass@server1:8080/path?query=1',
            'wss://server2:8443/ws',
            'http://subdomain.example.com:9090',
        ]
    )
    config.validate_servers()  # Should not raise any exception


def test_mcp_sse_server_config_with_api_key():
    """Test MCPSSEServerConfig with API key."""
    config = MCPSSEServerConfig(url='http://server1:8080', api_key='test-api-key')
    assert config.url == 'http://server1:8080'
    assert config.api_key == 'test-api-key'


def test_mcp_sse_server_config_without_api_key():
    """Test MCPSSEServerConfig without API key."""
    config = MCPSSEServerConfig(url='http://server1:8080')
    assert config.url == 'http://server1:8080'
    assert config.api_key is None


def test_mcp_stdio_server_config_basic():
    """Test basic MCPStdioServerConfig."""
    config = MCPStdioServerConfig(name='test-server', command='python')
    assert config.name == 'test-server'
    assert config.command == 'python'
    assert config.args == []
    assert config.env == {}


def test_mcp_stdio_server_config_with_args_and_env():
    """Test MCPStdioServerConfig with args and env."""
    config = MCPStdioServerConfig(
        name='test-server',
        command='python',
        args=['-m', 'server'],
        env={'DEBUG': 'true', 'PORT': '8080'},
    )
    assert config.name == 'test-server'
    assert config.command == 'python'
    assert config.args == ['-m', 'server']
    assert config.env == {'DEBUG': 'true', 'PORT': '8080'}


def test_mcp_config_with_stdio_servers():
    """Test MCPConfig with stdio servers."""
    stdio_server = MCPStdioServerConfig(
        name='test-server',
        command='python',
        args=['-m', 'server'],
        env={'DEBUG': 'true'},
    )
    config = MCPConfig(stdio_servers=[stdio_server])
    assert len(config.stdio_servers) == 1
    assert config.stdio_servers[0].name == 'test-server'
    assert config.stdio_servers[0].command == 'python'
    assert config.stdio_servers[0].args == ['-m', 'server']
    assert config.stdio_servers[0].env == {'DEBUG': 'true'}


def test_from_toml_section_with_stdio_servers():
    """Test creating config from TOML section with stdio servers."""
    data = {
        'sse_servers': ['http://server1:8080'],
        'stdio_servers': [
            {
                'name': 'test-server',
                'command': 'python',
                'args': ['-m', 'server'],
                'env': {'DEBUG': 'true'},
            }
        ],
    }
    result = MCPConfig.from_toml_section(data)
    assert 'mcp' in result
    assert len(result['mcp'].sse_servers) == 1
    assert result['mcp'].sse_servers[0].url == 'http://server1:8080'
    assert len(result['mcp'].stdio_servers) == 1
    assert result['mcp'].stdio_servers[0].name == 'test-server'
    assert result['mcp'].stdio_servers[0].command == 'python'
    assert result['mcp'].stdio_servers[0].args == ['-m', 'server']
    assert result['mcp'].stdio_servers[0].env == {'DEBUG': 'true'}


def test_mcp_config_with_both_server_types():
    """Test MCPConfig with both SSE and stdio servers."""
    sse_server = MCPSSEServerConfig(url='http://server1:8080', api_key='test-api-key')
    stdio_server = MCPStdioServerConfig(
        name='test-server',
        command='python',
        args=['-m', 'server'],
        env={'DEBUG': 'true'},
    )
    config = MCPConfig(sse_servers=[sse_server], stdio_servers=[stdio_server])
    assert len(config.sse_servers) == 1
    assert config.sse_servers[0].url == 'http://server1:8080'
    assert config.sse_servers[0].api_key == 'test-api-key'
    assert len(config.stdio_servers) == 1
    assert config.stdio_servers[0].name == 'test-server'
    assert config.stdio_servers[0].command == 'python'


def test_mcp_config_model_validation_error():
    """Test MCPConfig validation error with invalid data."""
    with pytest.raises(ValidationError):
        # Missing required 'url' field
        MCPSSEServerConfig()

    with pytest.raises(ValidationError):
        # Missing required 'name' and 'command' fields
        MCPStdioServerConfig()


def test_mcp_config_extra_fields_forbidden():
    """Test that extra fields are forbidden in MCPConfig."""
    with pytest.raises(ValidationError):
        MCPConfig(extra_field='value')

    # Note: The nested models don't have 'extra': 'forbid' set, so they allow extra fields
    # We're only testing the main MCPConfig class here
