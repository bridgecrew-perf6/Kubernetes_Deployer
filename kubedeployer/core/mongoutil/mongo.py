from pymongo import MongoClient
from requests.auth import HTTPDigestAuth
import os
import sys
import requests
import string
import random
import json
from deployinator.core.gitutil.varapi import write_gitvar
from deployinator.core.envutil.envvars import softCheck_env

def generatePassword(passLen=24):
    sampleSet = string.ascii_letters + string.digits
    return ''.join((random.choice(sampleSet) for i in range(passLen)))


def custom_role(environment, pubkey, privkey, dbname, rolename):
    headers = {'Content-Type': 'application/json'}
    data = {'actions': [{'action': 'FIND', 'resources':[{'collection': '', 'db': dbname}]},{'action': 'INSERT', 'resources': [{'collection': '', 'db': dbname}]},{'action': 'REMOVE', 'resources': [{'collection': '', 'db': dbname}]},{'action': 'UPDATE', 'resources':[{'collection': '', 'db': dbname}]}, {'action': 'BYPASS_DOCUMENT_VALIDATION', 'resources': [{'collection': '', 'db': dbname}]}, {'action': 'CREATE_COLLECTION', 'resources': [{'collection': '', 'db': dbname}]}, {'action': 'CREATE_INDEX', 'resources': [{'collection': '', 'db': dbname}]}, {'action': 'DROP_COLLECTION', 'resources': [{'collection': '', 'db': dbname}]}, {'action': 'LIST_COLLECTIONS', 'resources': [{'collection': '', 'db': dbname}]}, {'action': 'DB_STATS', 'resources': [{'collection':'', 'db': dbname}]}], 'roleName': rolename}
    dataJson = json.dumps(data)
    url = ''
    if environment in ['dev', 'development']:
        url = 'https://cloud.mongodb.com/api/atlas/v1.0/groups/5ec8620b98602632445a217e/customDBRoles/roles'

    if environment == 'test':
        url = 'https://cloud.mongodb.com/api/atlas/v1.0/groups/5ecee3f0a231252c9ff1dd4e/customDBRoles/roles'
    response = requests.post(url, headers=headers, data=dataJson, auth=HTTPDigestAuth(pubkey,privkey))
    response.raise_for_status()

def svc_account(environment, pubkey, privkey, rolename, svcaccount, password):
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    data = {"databaseName":"admin","password": password, "roles":[{"databaseName":"admin","roleName": rolename}],"username": svcaccount}
    dataJson = json.dumps(data)
    if environment in ['dev', 'development']:
        url = 'https://cloud.mongodb.com/api/atlas/v1.0/groups/5ec8620b98602632445a217e/databaseUsers'
    
    if environment == 'test':
        url = 'https://cloud.mongodb.com/api/atlas/v1.0/groups/5ecee3f0a231252c9ff1dd4e/databaseUsers'

    response = requests.post(url, headers=headers, data=dataJson, auth=HTTPDigestAuth(pubkey, privkey))
    response.raise_for_status()

def create_mongo(environ):
    role_name = 'svc-{mongodb_name}-role'.format(mongodb_name=os.environ['mongodb_name'])
    svcaccount = 'svc-{mongodb_name}'.format(mongodb_name=os.environ['mongodb_name'])
    pipeline_db_name = os.getenv('mongodb_name')
    pipeline_doc = os.getenv('mongodb_collection')
    collection_list = pipeline_doc.split(",")
    environment = environ
    db_password = ''
    if softCheck_env('mongodb_password'):
        db_password = os.environ['mongodb_password']
    else:
        db_password = generatePassword()
        write_gitvar(os.environ['CI_PROJECT_ID'], 'mongodb_password', environment, db_password)

    # assign var based on environment
    if environment in ['development', 'dev']:
        mongo_dev = os.getenv('mongo_dev_instance')
        pubkey = os.getenv('mongodev_pubkey')
        privkey = os.getenv('mongodev_privkey')
        client = MongoClient(mongo_dev)
        dblist = client.list_database_names()
    # assign based on the variables
    if environment == 'test':
        mongo_test = os.getenv('mongo_test_instance')
        pubkey = os.getenv('mongotest_pubkey')
        privkey = os.getenv('mongotest_privkey')
        client = MongoClient(mongo_test)
        dblist = client.list_database_names()
    if pipeline_db_name in dblist:
	    print("Database exists")
    else:
        db = client[pipeline_db_name]
        for each_val in collection_list:
            print(each_val)
            col = db[each_val]
            sample = { '_id': '1', 'name': 'John', 'address': 'Highway 37'}
            x = col.insert_one(sample)
            y = col.delete_one(sample)
        print("Database " + pipeline_db_name + " created")
        custom_role(environment, pubkey, privkey, pipeline_db_name, role_name)
        svc_account(environment, pubkey, privkey, role_name, svcaccount, db_password)