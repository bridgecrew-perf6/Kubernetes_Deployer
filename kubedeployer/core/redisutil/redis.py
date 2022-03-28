
import os
import subprocess
import yaml

def redis_setup(credentials, projectID, region, zone, deployName, redis_size, redis_config):

    '''
    Use gcloud SDK to set kuberenetes credentials and call helm for deployment.'
    '''
    os.environ['GCP_CREDENTIALS'] = credentials
    os.environ['PROJECTID'] = projectID
    os.environ['REGIONZONE'] = region + zone
    os.environ['NETWORKS'] = projectID + '-vpc'
    os.environ['INSTANCE_NAME'] = deployName
    os.environ['REDIS_SIZE'] = redis_size
    os.environ['REDIS_CONFIG'] = redis_config

    redisHostCheck = subprocess.Popen(["gcloud -q redis instances describe $INSTANCE_NAME --region=$REGIONZONE --project=$PROJECTID | grep host |  cut -c 7- "], stdout=subprocess.PIPE, shell=True)
    redisHost, redisErr = redisHostCheck.communicate()
    redisHost = redisHost.decode('utf-8').strip()
    print ('stderr1:',redisErr)

    if redisHost:
        print ('Redis instance already exists:',redisHost)
    else:
        os.system('gcloud -q redis instances create $INSTANCE_NAME --region=$REGIONZONE --size=$REDIS_SIZE --network=$NETWORKS')#default version is stable latest --redis-version=redis_4_0
        redisHostCheck = subprocess.Popen(["gcloud -q redis instances describe $INSTANCE_NAME --region=$REGIONZONE --project=$PROJECTID | grep host |  cut -c 7-"], stdout=subprocess.PIPE, shell=True)
        redisHost, redisErr = redisHostCheck.communicate()
        redisHost = redisHost.decode('utf-8').strip()
    os.environ['redis_host'] = redisHost
    if redis_config:
        os.system('gcloud -q --no-user-output-enabled redis instances update $INSTANCE_NAME --region=$REGIONZONE $REDIS_CONFIG')
    return redisHost