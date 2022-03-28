import pytest
from click.testing import CliRunner
from deployinator.commands.cmd_deploy import cli
from deployinator.commands.cmd_make import cli as make_cli

def test_deploy_debug():
    runner = CliRunner()
    result = runner.invoke(make_cli, ['-f', './tests/input.yaml'], catch_exceptions=False)
    print(result.output)
    result = runner.invoke(cli, ['--debug', '-f', 'values.yaml', '-d', './tests/input.yaml'])
    print(result.output)
    assert 'Debug' in result.output
    assert result.exit_code == 0