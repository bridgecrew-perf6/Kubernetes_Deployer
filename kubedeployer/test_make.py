import pytest, os, yaml
from click.testing import CliRunner
from deployinator.commands.cmd_make import cli

def test_make():
    runner = CliRunner()
    result = runner.invoke(cli, ['-f', './tests/input.yaml'], catch_exceptions=False)
    assert 'Writing' in result.output
    print(result.output)
    assert os.path.exists('values.yaml')
    with open('values.yaml', 'r') as inFile:
        make_output = yaml.safe_load(inFile)
    with open('./tests/output/helm_values.yaml', 'r') as inputFile:
        test_values = yaml.safe_load(inputFile)
    assert make_output['appVars'] == test_values['appVars']
    assert make_output['global'] == test_values['global']
    assert make_output['virtualService'] == test_values['virtualService']
    assert make_output['virtualserviceglobal'] == test_values['virtualserviceglobal']