import click
import yaml
import sys
import os
import yamale
from deployinator.cli import pass_context
from deployinator.core.dictutil.keys import check_keys
from deployinator.core.envutil.envvars import check_env
from deployinator.core.dictutil.keys import check_keys
from deployinator.core.dictutil.keys import read_key

@click.command('lint', short_help='Linting frontdoor input yaml file')
@click.option('-f', '--file', 'valueFile' , default='./dev_values.yaml', show_default=True, type=click.Path(dir_okay=False, exists=True), help='Path to the input values.')
@pass_context

def cli(ctx, valueFile):
    """Linting frontdoor input yaml file"""
    schemaFile = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../resources/dsl-schema.yaml"))
    ctx.log(f"Linting dsl {os.path.abspath(valueFile)} with schema {schemaFile}")
    valueFileStream = open(valueFile, "r")
    inputDict = yaml.safe_load(valueFileStream)
    # logstash validation
    if read_key(inputDict,'metadata', 'labels', 'applicationtype') == 'logstash':
        print('Linting : deployment.jobConfig')
        if not check_keys(inputDict, 'deployment', 'jobConfig'):
            raise AttributeError('Job Config not passed.')
        print('Linting : deployment.pipelineConfig')
        if not check_keys(inputDict, 'deployment', 'pipelineConfig'):
            raise AttributeError('Pipeline Config not passed.')
        print('Linting : deployment.logstashConfig')
        if not check_keys(inputDict, 'deployment', 'logstashConfig'):
            raise AttributeError('logstash Config not passed.')

    schema = yamale.make_schema(schemaFile)
    data = yamale.make_data(valueFile)

    failed = False

    try:
        yamale.validate(schema, data, strict=False)
        ctx.log('Validation success! 👍')
    except yamale.YamaleError as e:
        ctx.log('Validation failed!\n')
        for result in e.results:
            ctx.log("Error validating data '%s' with '%s'\n\t" % (result.data, result.schema))
            for error in result.errors:
                ctx.log('\t%s' % error)
        failed = True


    for variable in ['CI_REGISTRY_IMAGE', 'FTDR_REGISTRY_USER', 'FTDR_REGISTRY_PASSWORD', 'DOCKER_IMAGE_TAG', 'CI_COMMIT_SHORT_SHA', 'CI_PROJECT_ID', 'CI_JOB_TOKEN']:
        try:
            ctx.log('Checking variable: ' + variable)
            check_env(variable)
        except AttributeError as e:
            ctx.log(f"Failed to find required variable: {variable}")
            failed = True

    if failed:
        exit(1)
