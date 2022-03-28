import click
import yaml
import sys
import os
import shutil
import requests
import re
from io import StringIO
from deployinator.cli import pass_context
from deployinator.core.dictutil.keys import check_keys
from deployinator.core.dictutil.keys import read_key
from deployinator.core.gitutil.repo import clone_repo
from deployinator.core.gitutil.varapi import get_civar
from deployinator.core.envutil.envvars import softCheck_env, check_env

@click.command('make', short_help='Make input.yaml to pass to helm chart.')
@click.option('-u', '--user', 'user', default='gitlab-ci-token', show_default=True, help='Username to use when cloning gitlab ')
@click.option('-t', '--token', 'token', default=None, show_default=True, help='Gitlab token to use when cloning repositories. If not set, it will read CI_JOB_TOKEN environment var.')
@click.option('-f', '--file', 'valueFile' , default='./dev_values.yaml', show_default=True, type=click.File('r'), help='Path to the input values.')
@click.option('-o', '--output', 'outFile',  default = './values.yaml', show_default=True, type=click.File('w+'), help='Path to output file.')
@click.option('-p', '--policies-repo', 'policiesRepo', default='engineering/trust-reliability/security/iam/policies', show_default=True, help='Policies repo to clone')

@pass_context

def cli(ctx, user, token, valueFile, outFile, policiesRepo):
    '''
    Read input values (file) and create helm chart input values (file).
    '''
    inputDSL = yaml.safe_load(valueFile)
   
    # pull down a copy of the charts repo
    if not os.path.isdir('./charts'):
        if 'CHARTS_VERSION' in os.environ:
            ctx.log('Cloning charts repo ' + os.environ['CHARTS_VERSION'] + ' branch/tag')
            clone_repo('devops/charts', user, token, version=os.environ['CHARTS_VERSION'])
        else:
            ctx.log('Cloning charts repo master branch')
            clone_repo('devops/charts', user, token)

    # pull down a copy of the policies repo
    if not os.path.isdir('./policies'):
        ctx.log('Cloning policies repo.')
        clone_repo(policiesRepo, user, token)
    if (read_key(inputDSL, 'metadata', 'labels', 'applicationtype') == 'logstash'):
        if not os.path.isdir(os.environ['CI_PROJECT_NAME']):
            ctx.log('Cloning ' + os.environ['CI_PROJECT_NAME'] + ' repo.')
            clone_repo(os.path.relpath(os.environ['CI_PROJECT_PATH'], 'ftdr/'), user, token)

    # load the input template as a dictionary.
    supportedTypes = ['go-lang', 'dotnet', 'dotnetcore', 'angular', 'react', 'generic', 'logstash', 'function', 'jboss']  # update the linter schema too
    if read_key(inputDSL, 'metadata', 'labels', 'applicationtype') in supportedTypes:
        if read_key(inputDSL, 'metadata', 'labels', 'applicationtype') == 'logstash':
            with open('./charts/stable/logstash/values.yaml', 'r') as yamlFile:
                helmVars = yaml.safe_load(yamlFile)
        elif read_key(inputDSL, 'metadata', 'labels', 'applicationtype') == 'function':
            with open('./charts/stable/function/values.yaml', 'r') as yamlFile:
                helmVars = yaml.safe_load(yamlFile)
        else:
            with open('./charts/input-templates/ftdr-backend/values.yaml', 'r') as yamlFile:
                helmVars = yaml.safe_load(yamlFile)
    else:
        raise AttributeError(f"Only applicationtype: {' '.join(supportedTypes)} are supported at this time. I'll be back... with more features.")
    # load the inputDSL values into the helm chart input dictionary.
    if check_env('CI_REGISTRY_IMAGE'):
        helmVars['imageCredentials']['registry'] = os.environ['CI_REGISTRY_IMAGE']
    if check_env('FTDR_REGISTRY_USER'):
        helmVars['imageCredentials']['username'] = os.environ['FTDR_REGISTRY_USER']
    if check_env('FTDR_REGISTRY_PASSWORD'):
        helmVars['imageCredentials']['password'] = os.environ['FTDR_REGISTRY_PASSWORD']
    if check_env('DOCKER_IMAGE_TAG'):
        helmVars['deploymentDetails']['imageName'] = os.environ['DOCKER_IMAGE_TAG']
    if check_env('CI_COMMIT_SHORT_SHA'):
        helmVars['deploymentDetails']['commit_short_sha'] = os.environ['CI_COMMIT_SHORT_SHA']
    if check_keys(inputDSL, 'deployment', 'service_port') and check_keys(inputDSL, 'metadata', 'app'):
        helmVars['global'] = {'appName': read_key(inputDSL, 'metadata', 'app'), 'service_port': read_key(inputDSL, 'deployment', 'service_port'), 'service_protocol': read_key(inputDSL, 'deployment', 'service_protocol') if 'service_protocol' in inputDSL['deployment'] else 'http'}
    if check_keys(inputDSL, 'deployment', 'replicas'):
        helmVars['deploymentDetails']['replicas'] = read_key(inputDSL, 'deployment', 'replicas')
    if check_keys(inputDSL, 'deployment', 'maxsurge'):
        helmVars['deploymentDetails']['maxsurge'] = read_key(inputDSL, 'deployment', 'maxsurge')
    if check_keys(inputDSL, 'deployment', 'maxunavailable'):
        helmVars['deploymentDetails']['maxunavailable'] = read_key(inputDSL, 'deployment', 'maxunavailable')
    if check_keys(inputDSL, 'deployment', 'terminationgraceperiodseconds'):
        if read_key(inputDSL, 'deployment', 'terminationgraceperiodseconds') > 180:
            raise AttributeError("error: terminationgraceperiodseconds is set to more than 180 sec in service config. It should be less than 180 secs.")
        else:
            helmVars['deploymentDetails']['terminationgraceperiodseconds'] = read_key(inputDSL, 'deployment', 'terminationgraceperiodseconds')
    else:
        helmVars['deploymentDetails']['terminationgraceperiodseconds'] = 30
    if check_keys(inputDSL, 'metadata', 'labels'):
        helmVars['global']['labels'] = read_key(inputDSL, 'metadata', 'labels')
        helmVars['global']['labels']['env'] = read_key(inputDSL, 'metadata', 'env')
        helmVars['global']['labels']['app'] = read_key(inputDSL, 'metadata', 'app') # this is overwritten by the chart, but keeps older charts without .Release.Name functional
    if read_key(inputDSL, 'metadata', 'labels', 'applicationtype') != 'logstash' and check_keys(inputDSL, 'routing', 'allowCredentials'):
        helmVars['global']['allowCredentials'] = read_key(inputDSL, 'routing', 'allowCredentials')
    if check_keys(inputDSL, 'metadata', 'revision'):
        helmVars['global']['labels']['revision'] = read_key(inputDSL, 'metadata', 'revision')
    helmVars['deploymentDetails']['environment'] = read_key(inputDSL, 'metadata', 'env')
    if (read_key(inputDSL, 'metadata', 'labels', 'applicationtype') == 'function'):
        if check_keys(inputDSL, 'deployment', 'runtime'):
            helmVars['deploymentDetails']['runtime'] = read_key(inputDSL, 'deployment', 'runtime')
        if check_keys(inputDSL, 'deployment', 'handler'):
            helmVars['deploymentDetails']['handler'] = read_key(inputDSL, 'deployment', 'handler')
        if check_keys(inputDSL, 'deployment', 'deps'):
            reg = re.compile("python.+")
            runtime = read_key(inputDSL, 'deployment', 'runtime')
            match = bool(re.match(reg, runtime))
            if match == True :
                with open(read_key(inputDSL, 'deployment', 'deps'), 'r') as file:
                    data = file.read()
                    helmVars['deploymentDetails']['deps'] = data
            else:
                helmVars['deploymentDetails']['deps'] = read_key(inputDSL, 'deployment', 'deps')
        helmVars['deploymentDetails']['projectid'] = os.environ['CI_PROJECT_ID']
        helmVars['deploymentDetails']['jobid'] = os.environ['CI_JOB_ID']
        helmVars['deploymentDetails']['cijobtoken'] = os.environ['GITLAB_API_TOKEN']

    if read_key(inputDSL, 'metadata', 'labels', 'applicationtype') == 'logstash':
        if check_keys(inputDSL, "deployment", "jobConfig"):
            helmVars['appVars']['jobConfig'] = read_key(inputDSL, 'deployment', 'jobConfig')
        if check_keys(inputDSL, "deployment", "pipelineConfig"):
            helmVars['appVars']['pipelineConfig'] = read_key(inputDSL, 'deployment', 'pipelineConfig')
        if check_keys(inputDSL, "deployment", "logstashConfig"):
            helmVars['appVars']['logstashConfig'] = read_key(inputDSL, 'deployment', 'logstashConfig')

    # delete default values in helm template.
    helmVars['appVars']['env'] = {}
    helmVars['appVars']['envFrom'] = {}
    helmVars['appVars']['secrets'] = {}

    if check_keys(inputDSL, 'deployment', 'env'):
        if inputDSL['deployment']['env']:
            for foo in inputDSL['deployment']['env']:
                if check_keys(foo , 'type'):
                    if read_key(foo, 'type') == 'ci':
                        addVal = {}
                        addVal[foo['name']] = get_civar(os.environ['CI_PROJECT_ID'], foo['valueFrom'])
                        helmVars['appVars']['secrets'].update(addVal)
                    else:
                        raise AttributeError(f"Currently only type ci is suppport. The type declared is {foo['type']}.")
                else:
                    addVal = {}
                    if check_keys(foo , 'valueFrom'):
                        addVal[foo['name']] = foo['valueFrom']
                        helmVars['appVars']['envFrom'].update(addVal)
                    else:
                        addVal[foo['name']] = str(foo['value'])
                        helmVars['appVars']['env'].update(addVal)
        else:
            helmVars['appVars']['env'] = {'NO_VARS':'1'}
            helmVars['appVars']['secrets'] = {'NO_SECRETS':'1'}
    else:
        helmVars['appVars']['env'] = {'NO_VARS':'1'}
        helmVars['appVars']['secrets'] = {'NO_SECRETS':'1'}


    if not (read_key(inputDSL, 'metadata', 'labels', 'applicationtype') == 'logstash'):
        if not (read_key(inputDSL, 'metadata', 'labels', 'applicationtype') == 'function'):
            if not check_keys(inputDSL, 'routing', 'edge', 'hosts'):
                raise AttributeError("error: service config requires 'routing.edge.hosts' config")
            helmVars['global']['hosts'] = read_key(inputDSL, 'routing', 'edge', 'hosts')
            # TODO add logic in future for different routes, like tcp/grpc in addition to http
            #  (e.g. at least one of supported values)
            if not check_keys(inputDSL, 'routing', 'edge', 'routes', 'http'):
                raise AttributeError("error: service config requires 'routing.edge.routes.http' config")
            helmVars['virtualService']['routes']['http'] = [] # erase default values

            # initialize virtualserviceglobal section
            helmVars['virtualserviceglobal'] = {}
            helmVars['virtualserviceglobal']['routes'] = {}
            helmVars['virtualserviceglobal']['routes']['http'] = []

            # initialize virtualservicetyk section
            helmVars['virtualservicetyk'] = {}
            helmVars['virtualservicetyk']['routes'] = {}
            helmVars['virtualservicetyk']['routes']['http'] = []

            for route in inputDSL['routing']['edge']['routes']['http']:
                if not check_keys(route, 'gatewaySelectors'):
                    helmVars['virtualService']['routes']['http'].append(route.copy())
                else:
                    for gateway in route['gatewaySelectors']:
                        if gateway in 'local':
                            route.pop('gatewaySelectors')
                            helmVars['virtualService']['routes']['http'].append(route.copy())
                        elif gateway in 'global':
                            route.pop('gatewaySelectors')
                            helmVars['virtualserviceglobal']['routes']['http'].append(route.copy())

                        elif gateway in 'tyk':
                            route.pop('gatewaySelectors')
                            if check_keys(helmVars, 'virtualservicetyk', 'routes', 'http'):
                                helmVars['virtualservicetyk']['routes']['http'].append(route.copy())
                            else:
                                helmVars['virtualservicetyk']['routes']['http'].append(route.copy())
    # Copy OPA policy/config files that are used in
    # charts into the chart/policies/ directory.
    effort = read_key(inputDSL, 'metadata', 'effort')
    env = read_key(inputDSL, 'metadata', 'env')
    if env == 'development':
        env = 'dev'
    serviceName = read_key(inputDSL, 'metadata', 'app')
    defaultOpaConfigPath = "./policies/services/default/default/config.yaml"
    opaConfigPath = "./policies/services/{effort}/{service}/{env}/config.yaml".format(
        effort=effort, service=serviceName, env=env)
    defaultOpaRegoPath = "./policies/services/default/default/policy.rego"
    opaRegoPath = "./policies/services/{effort}/{service}/{env}/policy.rego".format(
        effort=effort, service=serviceName, env=env)
    opaStyraRegoPath = "./policies/services/{effort}/{service}/{env}/styra/istio/authz/policy.rego".format(
        effort=effort, service=serviceName, env=env)

    if read_key(inputDSL, 'metadata', 'labels', 'applicationtype') in supportedTypes:
        policyFound = False

        # where to write policy/config output
        targetConfigPath = ''
        targetPolicyPath = ''
        if (read_key(inputDSL, 'metadata', 'labels', 'applicationtype') == "function"):
            targetConfigPath = './charts/stable/function/policies/config.yaml'
            targetPolicyPath = './charts/stable/function/policies/policy.rego'
        else:
            targetConfigPath = './charts/stable/ftdr-backend/policies/config.yaml'
            targetPolicyPath = './charts/stable/ftdr-backend/policies/policy.rego'

        # logstash
        if (read_key(inputDSL, 'metadata', 'labels', 'applicationtype') == "logstash"):
            shutil.copytree(os.environ['CI_PROJECT_NAME'],'./charts/stable/logstash/'+ os.environ['CI_PROJECT_NAME'])
            policyFound = True

        ## See if this is a styra compatible service
        if not policyFound and os.path.isfile(opaStyraRegoPath):
            try:
                ctx.log("Configuring service with styra policies")
                req = "https://config-api.prod.ftdrinternal.com/config-api/opa/styra/{}/{}/{}".format(effort, serviceName, env)
                r = requests.get(req, verify='/usr/local/share/ca-certificates/frontdoorhomeCA.pem')
                if r.status_code != requests.codes.ok:
                    raise Exception("Config API returned an error: {}: {}".format(r.status_code, r.text))

                ## treat api response as a file
                with StringIO(r.json()['config']) as src:
                    with open(targetConfigPath, 'w+') as dst:
                        # write opa config and policy
                        shutil.copyfileobj(src, dst)
                        shutil.copyfile(opaStyraRegoPath, targetPolicyPath)
                policyFound = True

            except Exception as e:
                ctx.log("Failed to configure service: {}/{}/{} with styra: {}, falling back to local policy...".format(effort, serviceName, env, e))

        ## if a service policy exists for this service and we aren't using styra or if styra had an error
        if not policyFound and os.path.isfile(opaConfigPath) and os.path.isfile(opaRegoPath):
            try:
                ctx.log("Configuring service with normal policies")
                shutil.copyfile(opaRegoPath, targetPolicyPath)
                shutil.copyfile(opaConfigPath, targetConfigPath)
                policyFound = True

            except Exception as e:
                ctx.log("Failed to configure service: {}/{}/{} with normal policies: {}, falling back to default policy...".format(effort, serviceName, env, e))

        # default deny all policies because no other clause was satisfied
        if not policyFound:
            # No try catch here because it is better to fail then to accidentally have open policies
            ctx.log("Configuring service with default deny-all policies")
            shutil.copyfile(defaultOpaRegoPath, targetPolicyPath)
            with open(defaultOpaConfigPath, 'r') as defaultOpaConf:
                opaDict = yaml.safe_load(defaultOpaConf)
            opaDict['labels']['effort'] = effort
            opaDict['labels']['env'] = env
            opaDict['labels']['service'] = serviceName
            with open(targetConfigPath, 'w+') as configYaml:
                yaml.safe_dump(opaDict, configYaml)
            policyFound = True
    else:
        raise AttributeError(f"Only applicationtype: {' '.join(supportedTypes)} are supported at this time. I'll be back... with more features.")

    # Move virtualservice-global into subchart directory if virtualservice-global: exists in helmVars
    # if check_keys(helmVars, 'virtualservice-global') and not os.path.isdir('./charts/stable/ftdr-backend/charts/virtualservice-global'):
    #     ctx.log('Adding global virtualservice chart to parent chart.')
    #     shutil.copytree('./charts/stable/virtualservice-global', './charts/stable/ftdr-backend/charts/virtualservice-global')

    # Write out the compiled helm values file
    ctx.log('Writing to output file.')
    yaml.safe_dump(helmVars, outFile)
