import pytest
from click.testing import CliRunner
from deployinator.commands.cmd_lint import cli

def test_lint():
    runner = CliRunner()
    result = runner.invoke(cli, ['-f', './tests/input.yaml'])
    assert 'Linting' in result.output
    assert result.exit_code == 0

def test_fail_lint():
    runner = CliRunner()
    result = runner.invoke(cli, ['-f', './tests/bad_input.yaml'], catch_exceptions=False)
    assert 'metadata.app: Required field missing' in result.output
    assert '\'us-west\' not in' in result.output
    assert result.exit_code == 1