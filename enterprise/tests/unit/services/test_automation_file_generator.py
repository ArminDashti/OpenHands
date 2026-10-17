"""Tests for automation file generator."""

import ast

from services.automation_config import extract_config, validate_config
from services.automation_file_generator import generate_automation_file


class TestGenerateAutomationFile:
    def test_generates_valid_python(self):
        source = generate_automation_file(
            name='Daily Report',
            schedule='0 9 * * 1',
            timezone='UTC',
            prompt='Generate the daily status report.',
        )
        # Must parse without error
        ast.parse(source)

    def test_contains_config(self):
        source = generate_automation_file(
            name='Test Automation',
            schedule='*/5 * * * *',
            timezone='America/New_York',
            prompt='Do something useful.',
        )
        cfg = extract_config(source)
        assert cfg['name'] == 'Test Automation'
        assert cfg['triggers']['cron']['schedule'] == '*/5 * * * *'
        assert cfg['triggers']['cron']['timezone'] == 'America/New_York'

    def test_round_trip(self):
        """Generate → extract → validate must succeed."""
        source = generate_automation_file(
            name='Round Trip',
            schedule='30 14 * * 0',
            timezone='Europe/London',
            prompt='Weekly summary please.',
        )
        cfg = extract_config(source)
        model = validate_config(cfg)
        assert model.name == 'Round Trip'
        assert model.triggers.cron is not None
        assert model.triggers.cron.schedule == '30 14 * * 0'
        assert model.triggers.cron.timezone == 'Europe/London'

    def test_contains_prompt(self):
        source = generate_automation_file(
            name='Prompt Test',
            schedule='0 0 * * *',
            timezone='UTC',
            prompt='Hello world!',
        )
        assert 'Hello world!' in source

    def test_contains_docstring(self):
        source = generate_automation_file(
            name='Doc Test',
            schedule='0 0 * * *',
            timezone='UTC',
            prompt='test',
        )
        assert 'Doc Test' in source
        assert 'auto-generated automation' in source

    def test_special_characters_in_prompt(self):
        source = generate_automation_file(
            name='Special Chars',
            schedule='0 0 * * *',
            timezone='UTC',
            prompt='Check the "status" of \\n stuff',
        )
        # Must still be valid Python
        ast.parse(source)
        cfg = extract_config(source)
        assert cfg['name'] == 'Special Chars'

    def test_triple_quotes_in_name(self):
        """Names containing triple quotes must not break the generated file."""
        source = generate_automation_file(
            name='Test """Demo""" Name',
            schedule='0 0 * * *',
            timezone='UTC',
            prompt='hello',
        )
        # Must still be valid Python
        ast.parse(source)
        cfg = extract_config(source)
        assert 'Demo' in cfg['name']  # name preserved in config

    def test_triple_quotes_in_prompt(self):
        """Prompts containing triple quotes must not break the generated file."""
        source = generate_automation_file(
            name='Triple Quote Test',
            schedule='0 0 * * *',
            timezone='UTC',
            prompt='Use """triple quotes""" and \'\'\'single triples\'\'\' safely',
        )
        # Must parse without error
        ast.parse(source)
        cfg = extract_config(source)
        assert cfg['name'] == 'Triple Quote Test'
        # The prompt must survive round-trip
        assert '"""triple quotes"""' in source or "triple quotes" in source
