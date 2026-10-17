"""Tests for automation config extraction and validation."""

import pytest
from pydantic import ValidationError
from services.automation_config import extract_config, validate_config


# ---------------------------------------------------------------------------
# extract_config
# ---------------------------------------------------------------------------

class TestExtractConfig:
    def test_plain_dict(self):
        source = '''
__config__ = {
    "name": "Daily Report",
    "triggers": {"cron": {"schedule": "0 9 * * 1"}},
}
'''
        cfg = extract_config(source)
        assert cfg['name'] == 'Daily Report'
        assert cfg['triggers']['cron']['schedule'] == '0 9 * * 1'

    def test_annotated_assignment(self):
        source = '''
__config__: dict = {
    "name": "Annotated",
    "triggers": {"cron": {"schedule": "*/5 * * * *"}},
    "description": "annotated config",
}
'''
        cfg = extract_config(source)
        assert cfg['name'] == 'Annotated'
        assert cfg['description'] == 'annotated config'

    def test_no_config_raises(self):
        source = 'x = 1\ny = 2\n'
        with pytest.raises(ValueError, match='__config__ not found'):
            extract_config(source)

    def test_non_literal_value_raises(self):
        source = '__config__ = some_function()\n'
        with pytest.raises(ValueError, match='literal expression'):
            extract_config(source)

    def test_bad_syntax_raises(self):
        source = 'def foo(\n'
        with pytest.raises(ValueError, match='Failed to parse'):
            extract_config(source)

    def test_config_not_dict_raises(self):
        source = '__config__ = [1, 2, 3]\n'
        with pytest.raises(ValueError, match='must be a dict'):
            extract_config(source)

    def test_config_with_surrounding_code(self):
        source = '''
import os

__config__ = {"name": "Mixed", "triggers": {"cron": {"schedule": "0 0 * * *"}}}

def main():
    pass
'''
        cfg = extract_config(source)
        assert cfg['name'] == 'Mixed'


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

class TestValidateConfig:
    def test_valid_cron_config(self):
        cfg = {
            'name': 'My Automation',
            'triggers': {
                'cron': {'schedule': '0 9 * * 1', 'timezone': 'America/New_York'},
            },
        }
        model = validate_config(cfg)
        assert model.name == 'My Automation'
        assert model.triggers.cron is not None
        assert model.triggers.cron.schedule == '0 9 * * 1'
        assert model.triggers.cron.timezone == 'America/New_York'

    def test_valid_cron_default_timezone(self):
        cfg = {
            'name': 'Simple',
            'triggers': {'cron': {'schedule': '*/5 * * * *'}},
        }
        model = validate_config(cfg)
        assert model.triggers.cron is not None
        assert model.triggers.cron.timezone == 'UTC'

    def test_valid_with_description(self):
        cfg = {
            'name': 'Described',
            'triggers': {'cron': {'schedule': '0 0 * * *'}},
            'description': 'A helpful description',
        }
        model = validate_config(cfg)
        assert model.description == 'A helpful description'

    def test_missing_name_raises(self):
        cfg = {
            'triggers': {'cron': {'schedule': '0 0 * * *'}},
        }
        with pytest.raises(ValidationError):
            validate_config(cfg)

    def test_empty_name_raises(self):
        cfg = {
            'name': '',
            'triggers': {'cron': {'schedule': '0 0 * * *'}},
        }
        with pytest.raises(ValidationError):
            validate_config(cfg)

    def test_name_too_long_raises(self):
        cfg = {
            'name': 'x' * 201,
            'triggers': {'cron': {'schedule': '0 0 * * *'}},
        }
        with pytest.raises(ValidationError):
            validate_config(cfg)

    def test_missing_triggers_raises(self):
        cfg = {'name': 'No Triggers'}
        with pytest.raises(ValidationError):
            validate_config(cfg)

    def test_empty_triggers_raises(self):
        cfg = {'name': 'Empty', 'triggers': {}}
        with pytest.raises(ValidationError, match='Exactly one trigger'):
            validate_config(cfg)

    def test_invalid_cron_expression_raises(self):
        cfg = {
            'name': 'Bad Cron',
            'triggers': {'cron': {'schedule': 'not-a-cron'}},
        }
        with pytest.raises(ValidationError, match='Invalid cron expression'):
            validate_config(cfg)

    def test_invalid_cron_too_few_fields(self):
        cfg = {
            'name': 'Short Cron',
            'triggers': {'cron': {'schedule': '* *'}},
        }
        with pytest.raises(ValidationError, match='Invalid cron expression'):
            validate_config(cfg)

    def test_name_at_boundary_200(self):
        cfg = {
            'name': 'x' * 200,
            'triggers': {'cron': {'schedule': '0 0 * * *'}},
        }
        model = validate_config(cfg)
        assert len(model.name) == 200
