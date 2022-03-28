import os
import subprocess

import yaml


def set_kube_cred(credentials, projectID, region, zone, clusterName, appNamespace):
    '''
    Use gcloud SDK to set kuberenetes credentials and call helm for deployment.'
    '''
    os.environ['GCP_CREDENTIALS'] = credentials
    os.environ['PROJECTID'] = projectID
    os.environ['REGIONZONE'] = region + zone
    os.environ['CLUSTERNAME'] = clusterName
    os.environ['NAMESPACE'] = appNamespace

    script_list = ['#!/bin/bash', 'gcloud auth activate-service-account --key-file $GCP_CREDENTIALS', 'gcloud config set compute/zone $REGIONZONE', 'gcloud config set project $PROJECTID', 'gcloud container clusters get-credentials $CLUSTERNAME']
    with open('/tmp/gcloud_helper.sh', 'w+') as helperScript:
        helperScript.write('\n'.join(script_list))
    
    os.chmod('/tmp/gcloud_helper.sh', 0o750)
    gcHelperRun = subprocess.Popen(['/tmp/gcloud_helper.sh'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    gcHelper, gcHelperErr = gcHelperRun.communicate()
    if gcHelperRun.returncode != 0:
        print('stdout:', gcHelper)
        print('stderr:', gcHelperErr)
        raise RuntimeError(f'error: unable to set kubernetes cluster credentials')
    os.remove('/tmp/gcloud_helper.sh')

def create_namespace(namespaceTemplate, appNamespace):
    '''
    Use kubectl to create namespace.
    '''
    with open(namespaceTemplate, 'r') as namespaceFile:
        namespaceDict = yaml.safe_load(namespaceFile)
    namespaceDict['metadata']['name'] = appNamespace
    namespaceDict['metadata']['labels']['name'] = appNamespace
    with open('./namespace.yaml', 'w+') as outFile:
        yaml.safe_dump(namespaceDict, outFile)
    creatensRun = subprocess.Popen(['kubectl', 'apply', '-f', './namespace.yaml'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    createns, creatensErr = creatensRun.communicate()
    if creatensRun.returncode != 0:
        print('stdout:', createns)
        print('stderr:', creatensErr)
        raise RuntimeError(f'error: unable to create namespace')
