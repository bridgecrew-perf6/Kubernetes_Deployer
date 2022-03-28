import requests
import sys
import os
import json
import fnmatch
from deployinator.core.envutil.envvars import check_env

def merge_data(input_url, d):
    headers = {'PRIVATE-TOKEN': os.environ['GITLAB_API_TOKEN']}
    r2 = requests.get(input_url, headers=headers)
    data = d + r2.json()
    if r2.links.get('next'):
        data = merge_data(r2.links['next']['url'],data)
    return data

def get_civar(projectID, varName):
    '''
    Try getting variables from the environment. Failing that, send an api call.
    '''
    return get_gitvar(projectID, varName)
    # return os.environ[varName] if varName in os.environ else get_gitvar(projectID, varName)

def check_var_scope_match(gitlabVariable):
    if gitlabVariable['environment_scope'] == '*':
        return True

    try:
        environment = os.environ['CI_ENVIRONMENT_NAME']
    except KeyError:
        raise AttributeError(f'When using scoped environment variables, an environment name must be declared for the job. Please set environment: name: in your .gitlab-ci and try the job again')
    
    if fnmatch.fnmatch(environment, gitlabVariable['environment_scope']):
        return True

    return False

def get_gitvar(projectID, varName):
    '''
    Make an API call to gitlab variable api and return the value of varName (str).
    '''
    if check_env('GITLAB_API_TOKEN'):
        headers = {'PRIVATE-TOKEN': os.environ['GITLAB_API_TOKEN']}
    url = "https://gitlab.com/api/v4/projects/{projectID}/variables?per_page=100".format(projectID=projectID)
    req = requests.get(url, headers=headers)
    gitlabVariableList = req.json()
    if req.status_code != 200:
        errormsg = req.text
        raise RuntimeError(f'Call to gitlab api failed with {errormsg} please check your settings and try again.')

    if req.links.get('next'):
        gitlabVariableList = merge_data(req.links['next']['url'], gitlabVariableList)

    matchingVars = list(var for var in gitlabVariableList if varName in var.values() and check_var_scope_match(var))
    print(f"found {len(matchingVars)} matching gitlab variables for {varName}")

    if len(matchingVars) == 0:
        raise AttributeError(f'A variable named {varName} could not be found in the variables for project {projectID}.')

    # prefer more explicitly scoped variables over '*'
    sortedMatchingVars = sorted(matchingVars, key=lambda var: 1 if var['environment_scope'] == '*' else 0)
    return sortedMatchingVars[0]['value']

def write_gitvar(projectID, varName, environment, value):
    '''
    Make an API call to gitlab to write a new variable. 
    '''
    if check_env('GITLAB_API_TOKEN'):
        headers = {'PRIVATE-TOKEN': os.environ['GITLAB_API_TOKEN']}
    if environment == 'dev':
        environment = 'development'
    if environment == 'prod':
        environment = 'production'
    url = "https://gitlab.com/api/v4/projects/{projectID}/variables".format(projectID=projectID)
    putvar = requests.post(headers=headers, url=url, data={'key': varName,'variable_type': 'env_var','value': value,'environment_scope': environment})
    if putvar.status_code != 201:
        raise RuntimeError(f'An API call to gitlab to create a variable named {varName} failed with reason {putvar.reason}')