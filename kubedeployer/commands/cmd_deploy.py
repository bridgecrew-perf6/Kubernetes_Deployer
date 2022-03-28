import click
import sys
import os
import yaml
from deployinator.cli import pass_context
from deployinator.core.thanosutil.stackutil import get_stack
from deployinator.core.gitutil.repo import clone_repo
from deployinator.core.gitutil.varapi import get_civar
from deployinator.core.kubeutil.kube import set_kube_cred
from deployinator.core.kubeutil.kube import create_namespace
from deployinator.core.dictutil.keys import read_key, check_keys
from deployinator.core.envutil.envvars import check_env, softCheck_env
from deployinator.core.helmutil.helm import helm_test
from deployinator.core.helmutil.helm import helm_install
from deployinator.core.seutil.segen import generate_service_entries
from deployinator.core.mongoutil.mongo import create_mongo
from deployinator.core.redisutil.redis import redis_setup
from deployinator.core.akamaiutil.akamai import akamai_property
from jsonpath_ng import jsonpath,parse

@click.command('deploy', short_help='Deploy helm charts to caas clusters.')
@click.option('-c', '--credentials', 'credentials', default='./key.json', show_default=True, help='Path to the gcloud service account key.')
@click.option('-u', '--user', 'user', default='gitlab-ci-token', show_default=True, help='Username to use when cloning gitlab ')
@click.option('-t', '--token', 'token', default=None, show_default=True, help='Gitlab token to use when cloning repositories. If not set, it will read CI_JOB_TOKEN environment var.')
@click.option('-e', '--environment', 'environment', help='name of the target environment. If blank, environment will be read from input DSL.')
@click.option('--debug', 'debug', is_flag=True, help='Test helm install and print results to screen.')
@click.option('-f', '--file', 'helmFile', default='./values.yaml', show_default=True, help='Path to helm chart input values.')
@click.option('-d', '--dsl', 'dslFile', default='./input.yaml', show_default=True, type=click.File('r'), help='Path to input DSL values.')
@pass_context

def cli(ctx, credentials, user, token, environment, helmFile, dslFile, debug):
    """Set credentials and deploy to cluster."""
    if not os.path.isdir('./thanos'):
        ctx.log('Cloning thanos repo.')
        clone_repo('devops/thanos-2', user, token)
    stack_dir = './thanos-2/stacks'
    dslDict = yaml.safe_load(dslFile)
    deployName = read_key(dslDict, 'metadata', 'app')
    #Discuss with team for default effort
    projectType = read_key(dslDict, 'metadata', 'labels', 'applicationtype')
    if projectType == 'function':
        effort = 'core'
    else:
        effort = read_key(dslDict, 'metadata', 'effort')
    environment = read_key(dslDict, 'metadata', 'env')
    revision = read_key(dslDict, 'metadata', 'revision') if 'revision' in dslDict['metadata'] else None
    deployNamespace = deployName
    helmReleaseName = f"{deployName}-{revision}" if revision else deployName
    
    ## Read region dict and combine region and zone values into a list of strings
    deployRegions = []
    if check_keys(dslDict, 'deployment', 'regions'):
        deployRegionsList = read_key(dslDict, 'deployment', 'regions')
        for item in deployRegionsList:
            regionStr = "{name}-{zone}".format(name=item['name'], zone=item['zone'])
            deployRegions.append(regionStr)

    projectType = read_key(dslDict, 'metadata', 'labels', 'applicationtype')
    if not os.path.isfile(credentials):
        if environment in ['prod', 'production']:
            if check_env('GOOGLE_KEY_FTDR_OD_PROD_SVC'):
                keyEnv = os.environ['GOOGLE_KEY_FTDR_OD_PROD_SVC']
                with open('./key.json', 'w+') as keyFile:
                    keyFile.write(keyEnv)
        else:
            if check_env('GOOGLE_KEY_FTDR_OD_NONPROD_SVC_DEV'):
                keyEnv = os.environ['GOOGLE_KEY_FTDR_OD_NONPROD_SVC_DEV']
                with open('./key.json', 'w+') as keyFile:
                    keyFile.write(keyEnv)
    if softCheck_env('mongodb_name') and softCheck_env('mongodb_collection'):
        # Because we have no infra-alpha mongo environment, using dev here for testing purposes.
        if environment == 'infra-alpha':
            create_mongo('development')
        else:
            create_mongo(environment)
        with open(helmFile, 'r') as inputFile:
            helmVars = yaml.safe_load(inputFile)
        if check_keys(helmVars, 'appVars', 'secrets'):
            secretsDict = read_key(helmVars, 'appVars', 'secrets')
            if len(secretsDict) != 0:
                if 'mongodb_password' not in secretsDict.keys():
                    helmVars['appVars']['secrets'].update({'mongodb_password': get_civar(os.environ['CI_PROJECT_ID'], 'mongodb_password')})
                    with open(helmFile, 'r+') as writeHelm:
                        yaml.safe_dump(helmVars, writeHelm)
            else:
                helmVars['appVars']['secrets'] = {'mongodb_password': get_civar(os.environ['CI_PROJECT_ID'], 'mongodb_password')}
                with open(helmFile, 'r+') as writeHelm:
                    yaml.safe_dump(helmVars, writeHelm)
# code to trigger Akamai automation
    if environment in ['dev', 'development', 'test', 'staging', 'prod']:
        if check_keys(dslDict, 'deployment', 'akamai_switch_east') and check_keys(dslDict, 'deployment', 'akamai_switch'):
            raise Exception('only one akamai switch field is allowed.')
        
        elif check_keys(dslDict, 'deployment', 'akamai_switch_east'):
            akamai_switch = ""
            akamai_switch_east = read_key(dslDict, 'deployment', 'akamai_switch_east')
            if read_key(dslDict, 'metadata', 'labels', 'component') == 'backend' and read_key(dslDict, 'deployment', 'akamai_switch_east') == 'yes':
                for prefix in dslDict['routing']['edge']['routes']['http']:
                    try:
                        if prefix['gatewaySelectors'][0] == 'global':
                            jsonpath_expression = parse('match[*].uri.prefix')
                            akamai_path_value = [match.value for match in jsonpath_expression.find(prefix)]
                            edge_path_list = []
                            for akamai_path in akamai_path_value:         
                                if akamai_path.endswith('/'):
                                    akamai_path += '*'
                                    edge_path_list.append(akamai_path)
                                else:
                                    edge_path_list.append(akamai_path)
                            akamai_property(environment, effort, edge_path_list, akamai_switch, akamai_switch_east)
                    except KeyError:
                        continue

        elif check_keys(dslDict, 'deployment', 'akamai_switch'):
            akamai_switch_east = ""
            akamai_switch = read_key(dslDict, 'deployment', 'akamai_switch')
            if read_key(dslDict, 'metadata', 'labels', 'component') == 'backend' and read_key(dslDict, 'deployment', 'akamai_switch') == 'yes':
                for prefix in dslDict['routing']['edge']['routes']['http']:
                    try:
                        if prefix['gatewaySelectors'][0] == 'global':
                            jsonpath_expression = parse('match[*].uri.prefix')
                            akamai_path_value = [match.value for match in jsonpath_expression.find(prefix)]
                            edge_path_list = []
                            for akamai_path in akamai_path_value:         
                                if akamai_path.endswith('/'):
                                    akamai_path += '*'
                                    edge_path_list.append(akamai_path)
                                else:
                                    edge_path_list.append(akamai_path)
                            akamai_property(environment, effort, edge_path_list, akamai_switch, akamai_switch_east)
                    except KeyError:
                        continue
        else: 
            None

    if environment == 'development':
        environment = 'dev'
    if environment == 'production': 
        environment = 'prod'
 

    stack_def = {}
    stack_def = get_stack(effort, environment, stack_dir)
    if not os.path.isdir('./charts'):
        if 'CHARTS_VERSION' in os.environ:
            ctx.log('Cloning charts repo ' + os.environ['CHARTS_VERSION'] + ' branch/tag')
            clone_repo('devops/charts', user, token, version=os.environ['CHARTS_VERSION'])
        else:
            ctx.log('Cloning charts repo master branch')
            clone_repo('devops/charts', user, token)
    ctx.log('Deploying: '+ deployName)
    for item in stack_def:
        for cluster in item['clusters']:
            if cluster['provider']['type'] == 'gcp':
                project = cluster['provider']['config']['tfvars']['project_id']
                region = cluster['region']
                zone = cluster['zone']
                clusterRegionZone = "{region}-{zone}".format(region=region, zone=zone)
                clusterName = cluster['name']
                if clusterRegionZone in deployRegions:
                    ctx.log('Setting up cluster credentials.')
                    set_kube_cred(credentials, project, region, zone, clusterName, deployName)
                    if check_keys(dslDict, 'deployment', 'cache', 'type'):
                        if read_key(dslDict, 'deployment', 'cache', 'type') == 'redis':
                            ctx.log('Creating Redis instance - Hold tight.')
                            if check_keys(dslDict, 'deployment', 'cache', 'size'):
                                if len(read_key(dslDict, 'deployment', 'cache', 'size')) != 0:
                                    redis_size = dslDict['deployment']['cache']['size']
                                else:
                                    redis_size = '1' #default set to 1G
                            else:
                                redis_size = '1' #default set to 1G
                            if check_keys(dslDict, 'deployment', 'cache', 'redis_config'):
                                redis_config = dslDict['deployment']['cache']['redis_config']
                            else:
                                redis_config = ''
                        redis_host = redis_setup(credentials, project, region, zone, deployName, redis_size, redis_config)
                        with open(helmFile, 'r+') as f:
                            filesource = yaml.safe_load(f)
                            filesource['appVars']['env'].update({'REDIS_HOST': redis_host})
                            yaml.safe_dump(filesource, f)
                    if check_keys(dslDict, 'routing', 'internal', 'peers'):
                        ctx.log('Genering service entries')
                        generate_service_entries(dslDict, deployNamespace)
                else:
                    print(f'{clusterName} is not in desired region(s).')
                projectType = read_key(dslDict, 'metadata', 'labels', 'applicationtype')
                supportedTypes = ['go-lang', 'dotnet', 'dotnetcore', 'angular', 'react', 'generic', 'logstash', 'function', 'jboss']
                if projectType in supportedTypes:
                    chartName = './charts/stable/ftdr-backend'
                    namespaceTemplate = './charts/input-templates/ftdr-backend/namespace.yaml'
                    if projectType == "logstash":
                        chartName = './charts/stable/logstash/'
                        deployNamespace = 'default'
                        namespaceTemplate = './charts/input-templates/ftdr-backend/namespace.yaml'
                    if projectType == "function":
                        chartName = './charts/stable/function/'
                        namespaceTemplate = './charts/input-templates/ftdr-backend/namespace.yaml'
                else:
                    raise AttributeError(f"Currently only applicationTypes {' '.join(supportedTypes)} are supported by deployinator. I'll be back... with more features.")
                print("reached for deployment")
                print("deployRegions: ",deployRegions)
                print("clusterRegionZone: ", clusterRegionZone)
                if not len(deployRegions) == 0:
                    if clusterRegionZone in deployRegions:
                        if debug:
                            ctx.log('Debug only. Rendering template against {clusterName}'.format(clusterName=clusterName))
                            helm_test(helmReleaseName, deployNamespace, helmFile, chartName)
                        else:
                            ctx.log('Deploying service to cluster {clusterName}'.format(clusterName=clusterName))
                            if not (deployNamespace == '' or deployNamespace == "default"):
                                create_namespace(namespaceTemplate, deployNamespace)
                            helm_install(helmReleaseName, deployNamespace, helmFile, chartName)
                    else:
                        print(f'{clusterName} is not in desired region(s).')
                        continue
                else:
                    if debug:
                        ctx.log('Debug only. Rendering template against {clusterName}'.format(clusterName=clusterName))
                        helm_test(helmReleaseName, deployNamespace, helmFile, chartName)
                    else:
                        ctx.log('Deploying service to cluster {clusterName}'.format(clusterName=clusterName))
                        if not (deployNamespace == '' or deployNamespace == "default"):
                            create_namespace(namespaceTemplate, deployNamespace)
                        helm_install(helmReleaseName, deployNamespace, helmFile, chartName)
            else:
                raise AttributeError("Currently only GCP clusters are supported by deployinator. I'll be back... with more features.")
