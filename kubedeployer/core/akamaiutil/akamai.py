import json
import pprint
import os
import sys
import requests
import time
from jsonpath_ng import jsonpath,parse
from jsonpath_ng.ext import parse
from akamai.edgegrid import EdgeGridAuth
from urllib.parse import urljoin


def akamai_property(environment, effort, edge_path_list, akamai_switch, akamai_switch_east):
    baseurl = os.getenv('akamai_baseurl')
    client_token = os.getenv('akamai_client_token')
    client_secret = os.getenv('akamai_client_secret')
    access_token = os.getenv('akamai_access_token')
    s = requests.Session()
    s.auth = EdgeGridAuth(
        client_token=client_token,
        client_secret=client_secret,
        access_token=access_token
    )

    global property_id
    if environment in ['dev', 'development']:
         property_id = 'prp_505461'
    elif environment == 'test':
         property_id = 'prp_519595'
    elif environment == 'staging':
         property_id = 'prp_530626'
    elif environment == 'prod':
         property_id = 'prp_523094'
    else:
        None

    # Get the latest version 
    result = s.get(urljoin(baseurl, '/papi/v1/properties/{}/versions/latest?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)))
    result_data = result.json()
    version = result_data['versions']['items'][0]['propertyVersion']

    # Endpoint to get the latest version rule 
    get_rule_endpoint = '/papi/v1/properties/{}/versions/{}/rules?contractId=ctr_P-2OAZAJ5&groupId=grp_136194&validateRules=true&validateMode=fast'.format(property_id, version)
    create_new_version = '/papi/v1/properties/{}/versions?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)
    get_latest_rule = s.get(urljoin(baseurl, get_rule_endpoint))
    get_latest_rule_json = get_latest_rule.json()
    
    #Akamai new property version
    def akamai_new_property_version():
        # create new version based on the version activated on Production Network
        versionDict = {"createFromVersion": 1}
        versionDict['createFromVersion'] = version
        create_new_rule_version = s.post(urljoin(baseurl, create_new_version), json=versionDict)
        create_new_rule_version_data = create_new_rule_version.json()
        # Get new property created version
        newversionLink = create_new_rule_version_data['versionLink']
        get_version = s.get(urljoin(baseurl, newversionLink))
        get_version_data = get_version.json()
        global newpropertyVersion
        newpropertyVersion = get_version_data['versions']['items'][0]['propertyVersion']
        # Update rule endpoint
        global post_rule_endpoint
        post_rule_endpoint = '/papi/v1/properties/{}/versions/{}/rules?contractId=ctr_P-2OAZAJ5&groupId=grp_136194&validateRules=false&validateMode=fast'.format(property_id, newpropertyVersion)
    
    # Akamai staging network
    def akamai_staging():
        # Activate the property on Staging Network
        StagingActivation = {"propertyVersion":207,"network":"STAGING","note":"Akamai automation","notifyEmails":["devops@ahso365.onmicrosoft.com"],"acknowledgeWarnings":["msg_eac797d55da505d7f40dcd3857d003c83ba8d7c1","msg_c90a94ea24916879fec8813cc5745d6da2c6d1c0","msg_7a2aa72bca3f894607c126436861cb73fb82d677","msg_6414cc30ea3b4497374867fce960cd94528cf490","msg_718b5635c6b6c0104bb8d3191ac320d7c3c199e3","msg_95693b4a145202a186eb73f89f03e39014643beb","msg_f3209af9886d119fb0bcb9f872ded670e2d2cf5b","msg_ee289d54bfd9c80ad8d8c2fbe365b58e35d080c9","msg_3b9174ca9d001b7e9cc360ef7833707d90b92e20", "msg_f3209af9886d119fb0bcb9f872ded670e2d2cf5b", "msg_d45d9e908ec4efb885e237641d7af08cb8658e1c", "msg_063b9cfab0edfa91d029ed1d030df56ab3948f2c"]}              
        StagingActivation['propertyVersion'] = newpropertyVersion           
        staging = s.post(urljoin(baseurl, '/papi/v1/properties/{}/activations?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)), json=StagingActivation)
        print("Akamai Staging n/w status code", staging.status_code)

        if staging.status_code == 409:
            # get activationId of the previous activation/pending version
            get_activationId = s.get(urljoin(baseurl,'/papi/v1/properties/{}/activations?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)))
            get_activationId_json = get_activationId.json()
            activationId = get_activationId_json['activations']['items'][1]['activationId']
            # cancel pending activation of previous version
            s.delete(urljoin(baseurl, '/papi/v1/properties/{}/activations/{}?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id, activationId)))
            # Retry unrill status changes to ABORTED
            for x in range(0,4):
                print("previous version cancellation is still in progress")
                time.sleep(40)
                retry_status = s.get(urljoin(baseurl, '/papi/v1/properties/{}/activations/{}?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id, activationId)))
                retry_status_response = retry_status.json()
                if retry_status_response['activations']['items'][0]['status'] == "ABORTED":
                    break
            # Activate the latest version once the previous version is aborted
            staging_retry = s.post(urljoin(baseurl, '/papi/v1/properties/{}/activations?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)), json=StagingActivation)
            print("Akamai staging n/w status code", staging_retry.status_code)

        if staging.status_code == 400:
            # Error handling to acknowledge warnings
            staging_response = staging.json()
            jsonpath_expr = parse('warnings[*].messageId')
            messageId = [match.value for match in jsonpath_expr.find(staging_response)]
            StagingActivation['acknowledgeWarnings'].extend(messageId)
            staging_retry = s.post(urljoin(baseurl, '/papi/v1/properties/{}/activations?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)), json=StagingActivation)
            print("Akamai Staging n/w status code", staging_retry.status_code)

    # Akamai production network
    def akamai_production():
        # Activate the property on production Network
        productionActivation = {"propertyVersion":207,"network":"PRODUCTION","note":"Akamai automation","notifyEmails":["devops@ahso365.onmicrosoft.com"],"acknowledgeWarnings":["msg_eac797d55da505d7f40dcd3857d003c83ba8d7c1","msg_c90a94ea24916879fec8813cc5745d6da2c6d1c0","msg_7a2aa72bca3f894607c126436861cb73fb82d677","msg_6414cc30ea3b4497374867fce960cd94528cf490","msg_718b5635c6b6c0104bb8d3191ac320d7c3c199e3","msg_95693b4a145202a186eb73f89f03e39014643beb","msg_f3209af9886d119fb0bcb9f872ded670e2d2cf5b","msg_ee289d54bfd9c80ad8d8c2fbe365b58e35d080c9","msg_3b9174ca9d001b7e9cc360ef7833707d90b92e20", "msg_f3209af9886d119fb0bcb9f872ded670e2d2cf5b", "msg_d45d9e908ec4efb885e237641d7af08cb8658e1c", "msg_063b9cfab0edfa91d029ed1d030df56ab3948f2c"]}              
        productionActivation['propertyVersion'] = newpropertyVersion           
        production = s.post(urljoin(baseurl, '/papi/v1/properties/{}/activations?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)), json=productionActivation)
        print("Akamai Production n/w status code", production.status_code)

        if production.status_code == 409:
            # get activation Id of the previous activation/pending version
            get_activationId = s.get(urljoin(baseurl,'/papi/v1/properties/{}/activations?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)))
            get_activationId_json = get_activationId.json()
            activationId = get_activationId_json['activations']['items'][1]['activationId']
            # cancel pending activation of previous version
            s.delete(urljoin(baseurl, '/papi/v1/properties/{}/activations/{}?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id, activationId)))
            # Retry unrill status changes to ABORTED
            for x in range(0,4):
                print("previous version cancellation is still in progress")
                time.sleep(40)
                retry_status = s.get(urljoin(baseurl, '/papi/v1/properties/{}/activations/{}?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id, activationId)))
                retry_status_response = retry_status.json()
                if retry_status_response['activations']['items'][0]['status'] == "ABORTED":
                    break
            # Activate the latest version once the previous version is aborted
            production_retry = s.post(urljoin(baseurl, '/papi/v1/properties/{}/activations?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)), json=productionActivation)
            print("Akamai Production n/w status code", production_retry.status_code)

        if production.status_code == 400:
            # Error handling to acknowledge warnings
            production_response = production.json()
            jsonpath_expr = parse('warnings[*].messageId')
            messageId = [match.value for match in jsonpath_expr.find(production_response)]
            productionActivation['acknowledgeWarnings'].extend(messageId)
            production_retry = s.post(urljoin(baseurl, '/papi/v1/properties/{}/activations?contractId=ctr_P-2OAZAJ5&groupId=grp_136194'.format(property_id)), json=productionActivation)
            print("Akamai production n/w status code", production_retry.status_code)

    # 
    def akamai_check(sub_rule, edge_path_list, environment, effort):
        for x in get_latest_rule_json['rules']['children']:
            if x['name'] == sub_rule:
                jsonpath_expression = parse('criteria[*].options.values')
                akamaipathList = jsonpath_expression.find(x)[0].value
                edge_append_list = []
                for x in edge_path_list:
                    if x in akamaipathList:
                        print('Akamai is already configured for this path %s in %s.apis.frontdoorhome.com(%s)' % (x, environment, effort))
                    else:
                        print('Akamai configuration for this path %s is in progress, will be live in 10 to 15 minutes' % x)
                        edge_append_list.append(x)
                if edge_append_list:
                    # create new version based on the version activated on Production Network
                    akamai_new_property_version()
                    value_jsonpath_expression = parse("$.rules.children[?(@.name== '{}' )].criteria[*].options.values".format(sub_rule))
                    value_data = value_jsonpath_expression.find(get_latest_rule_json)[0].value
                    value_data.extend(edge_append_list)
                    # update rule with new property version
                    s.put(urljoin(baseurl, post_rule_endpoint), json=get_latest_rule_json)
                    akamai_staging()
                    akamai_production()

    def akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east):
        edge_remove_list = []
        edge_append_list_east = []
        # remove path from central sub rule 
        for x in get_latest_rule_json['rules']['children']:
            if x['name'] == sub_rule:
                jsonpath_expression = parse('criteria[*].options.values')
                akamaipathList = jsonpath_expression.find(x)[0].value
                for x in edge_path_list :
                    if x in akamaipathList:
                        print('removing path %s from central region in %s.apis.frontdoorhome.com(%s)' % (x, environment, effort))
                        edge_remove_list.append(x)
        # Add path to east sub-rule 
        for x in get_latest_rule_json['rules']['children']:
            if x['name'] == sub_rule_east:
                jsonpath_expression = parse('criteria[*].options.values')
                akamaipathList = jsonpath_expression.find(x)[0].value
                for x in edge_path_list:
                    if x in akamaipathList:
                        print('Akamai is already configured for this path %s in %s.apis.frontdoorhome.com(%s)' % (x, environment, effort))
                    else:
                        print('Akamai configuration for this path %s is in progress, will be live in 10 to 15 minutes' % x)
                        edge_append_list_east.append(x)
                if edge_remove_list and edge_append_list_east:
                    # create new version based on the version activated on Production Network
                    akamai_new_property_version()
                    #update in central sub rule
                    value_jsonpath_expression = parse("$.rules.children[?(@.name== '{}' )].criteria[*].options.values".format(sub_rule))
                    value_data = value_jsonpath_expression.find(get_latest_rule_json)[0].value
                    for i in edge_remove_list:
                        try: 
                            value_data.remove(i)
                        except ValueError:
                            pass
                    #update in east sub rule
                    value_jsonpath_expression = parse("$.rules.children[?(@.name== '{}' )].criteria[*].options.values".format(sub_rule_east))
                    value_data = value_jsonpath_expression.find(get_latest_rule_json)[0].value
                    value_data.extend(edge_append_list_east)
                    # update rule with new property version
                    s.put(urljoin(baseurl, post_rule_endpoint), json=get_latest_rule_json)
                    akamai_staging()
                    akamai_production()
                elif edge_append_list_east:
                    #update in east sub rule
                    akamai_new_property_version()
                    value_jsonpath_expression = parse("$.rules.children[?(@.name== '{}' )].criteria[*].options.values".format(sub_rule_east))
                    value_data = value_jsonpath_expression.find(get_latest_rule_json)[0].value
                    value_data.extend(edge_append_list_east)
                    # update rule with new property version
                    s.put(urljoin(baseurl, post_rule_endpoint), json=get_latest_rule_json)
                    akamai_staging()
                    akamai_production()
                else:
                    None
    
    if effort == 'ecomm':
        if environment in ['dev', 'development'] and len(akamai_switch_east) != 0:
            sub_rule = 'Ecomm Dev Properties'
            sub_rule_east = 'Ecomm Dev Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment in ['dev', 'development'] and len(akamai_switch) != 0:
            sub_rule = 'Ecomm Dev Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'test' and len(akamai_switch_east) != 0:
            sub_rule = 'Ecomm Test Properties'
            sub_rule_east = 'Ecomm Test Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'test' and len(akamai_switch) != 0:
            sub_rule = 'Ecomm Test Properties'
        elif environment == 'staging' and len(akamai_switch_east) != 0:
            sub_rule = 'Ecomm Staging Properties'
            sub_rule_east = 'Ecomm Staging Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'staging' and len(akamai_switch) != 0:
            sub_rule = 'Ecomm Staging Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'prod' and len(akamai_switch_east) != 0:
            sub_rule = 'Ecomm Prod Properties'
            sub_rule_east = 'Ecomm Prod Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'prod' and len(akamai_switch) != 0:
            sub_rule = 'Ecomm Prod Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        else:
            None


    if effort == 'b2b':
        if environment in ['dev', 'development'] and len(akamai_switch_east) != 0:
            sub_rule = 'B2B Dev Properties'
            sub_rule_east = 'B2B Dev Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment in ['dev', 'development'] and len(akamai_switch) != 0:
            sub_rule = 'B2B Dev Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'test' and len(akamai_switch_east) != 0:
            sub_rule = 'B2B Test Properties'
            sub_rule_east = 'B2B Test Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'test' and len(akamai_switch) != 0:
            sub_rule = 'B2B Test Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'staging' and len(akamai_switch_east) != 0:
            sub_rule = 'B2B Staging Properties'
            sub_rule_east = 'B2B Staging Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'staging' and len(akamai_switch) != 0:
            sub_rule = 'B2B Staging Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'prod' and len(akamai_switch_east) != 0:
            sub_rule = 'B2B Prod Properties'
            sub_rule_east = 'B2B Prod Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'prod' and len(akamai_switch) != 0:
            sub_rule = 'B2B Prod Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        else:
            None

    if effort == 'core':
        if environment in ['dev', 'development'] and len(akamai_switch_east) != 0:
            sub_rule = 'Core Dev Properties'
            sub_rule_east = 'Core Dev Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment in ['dev', 'development'] and len(akamai_switch) != 0:
            sub_rule = 'Core Dev Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'test' and len(akamai_switch_east) != 0:
            sub_rule = 'Core Test Properties'
            sub_rule_east = 'Core Test Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'test' and len(akamai_switch) != 0:
            sub_rule = 'Core Test Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'staging' and len(akamai_switch_east) != 0:
            sub_rule = 'Core Staging Properties'
            sub_rule_east = 'Core Staging Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'staging' and len(akamai_switch) != 0:
            sub_rule = 'Core Staging Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'prod' and len(akamai_switch_east) != 0:
            sub_rule = 'Core Prod Properties'
            sub_rule_east = 'Core Prod Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'prod' and len(akamai_switch) != 0:
            sub_rule = 'Core Prod Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        else:
            None   


    if effort == 'callcenter':
        if environment in ['dev', 'development'] and len(akamai_switch_east) != 0:
            sub_rule = 'Callcenter Dev Properties'
            sub_rule_east = 'Callcenter Dev Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east) 
        elif environment in ['dev', 'development'] and len(akamai_switch) != 0:
            sub_rule = 'Callcenter Dev Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'test' and len(akamai_switch_east) != 0:
            sub_rule = 'Callcenter Test Properties'
            sub_rule_east = 'Callcenter Test Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'test' and len(akamai_switch) != 0:
            sub_rule = 'CallCenter Test Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'staging' and len(akamai_switch_east) != 0:
            sub_rule = 'Callcenter Staging Properties'
            sub_rule_east = 'Callcenter Staging Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'staging' and len(akamai_switch) != 0:
            sub_rule = 'CallCenter Staging Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'prod' and len(akamai_switch_east) != 0:
            sub_rule = 'Callcenter Prod Properties'
            sub_rule_east = 'Callcenter Prod Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'prod' and len(akamai_switch) != 0:
            sub_rule = 'CallCenter Prod Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        else:
            None          


    if effort == 'od':
        if environment in ['dev', 'development'] and len(akamai_switch_east) != 0:
            sub_rule = 'OD Dev Properties'
            sub_rule_east = 'OD Dev Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)  
        elif environment in ['dev', 'development'] and len(akamai_switch) != 0:
            sub_rule = 'OD Dev Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'test' and len(akamai_switch_east) != 0:
            sub_rule = 'OD Test Properties'
            sub_rule_east = 'OD Test Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'test' and len(akamai_switch) != 0:
            sub_rule = 'OD Test Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'staging' and len(akamai_switch_east) != 0:
            sub_rule = 'OD Staging Properties'
            sub_rule_east = 'OD Staging Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'staging' and len(akamai_switch) != 0:
            sub_rule = 'OD Staging Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'prod' and len(akamai_switch_east) != 0:
            sub_rule = 'OD Prod Properties'
            sub_rule_east = 'OD Prod Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'prod' and len(akamai_switch) != 0:
            sub_rule = 'OD Prod Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)      
        else:
            None 


    if effort == 'paymenterp': 
        if environment in ['dev', 'development'] and len(akamai_switch_east) != 0:
            sub_rule = 'Paymenterp Dev Properties'
            sub_rule_east = 'Paymenterp Dev Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)  
        elif environment in ['dev', 'development'] and len(akamai_switch) != 0:
            sub_rule = 'Paymenterp Dev Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'test' and len(akamai_switch_east) != 0:
            sub_rule = 'Paymenterp Test Properties'
            sub_rule_east = 'Paymenterp Test Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'test' and len(akamai_switch) != 0:
            sub_rule = 'Paymenterp Test Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'staging' and len(akamai_switch_east) != 0:
            sub_rule = 'Paymenterp Staging Properties'
            sub_rule_east = 'Paymenterp Staging Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'staging' and len(akamai_switch) != 0:
            sub_rule = 'Paymenterp Staging Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'prod' and len(akamai_switch_east) != 0:
            sub_rule = 'Paymenterp Prod Properties'
            sub_rule_east = 'Paymenterp Prod Properties East'
            akamai_move_east(sub_rule, edge_path_list, environment, effort, sub_rule_east)
        elif environment == 'prod' and len(akamai_switch) != 0:
            sub_rule = 'Paymenterp Prod Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        else:
            None


    if effort == 'seceng': 
        if environment in ['dev', 'development']:
            sub_rule = 'SecEng Dev Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        elif environment == 'prod':
            sub_rule = 'SecEng Prod Properties'
            akamai_check(sub_rule, edge_path_list, environment, effort)
        else:
            None