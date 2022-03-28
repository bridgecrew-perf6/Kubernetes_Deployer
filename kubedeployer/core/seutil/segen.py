import ipaddress
import sys

import yaml
from kubernetes import client, config

# CURRENT_ALLOCATED_IPS holds IPs current(this) process is going to allocate
# for generation of serviceentries.
# FIXME: Move this to central key-value store(e.g. redis) for proper
# distributed awareness of currenly reserved IPs
CURRENT_ALLOCATED_IPS = []

def get_available_ip():
    config.load_kube_config()
    api = client.CustomObjectsApi()
    resource = api.list_cluster_custom_object(
        group="networking.istio.io",
        version="v1alpha3",
        plural="serviceentries",
    )
    allocated_ips = CURRENT_ALLOCATED_IPS
    for item in resource['items']:
        try:
            allocated_ips.extend(item['spec']['addresses'])
        except KeyError:
            continue

    service_entry_network_ips = [
        str(ip) for ip in ipaddress.IPv4Network('240.0.0.0/24').hosts()
    ]
    available_ips = list(filter(lambda ip: ip not in allocated_ips,
                                service_entry_network_ips))
    if len(available_ips) > 0:
        return available_ips[0]
    else:
        return None


def generate_service_entries(overrides,
                             namespace,
                             default_se_template='./charts/input-templates/ftdr-backend/default_service_entry.yaml',
                             output_dir='charts/stable/ftdr-backend/templates'):
    ext_overrides = overrides['routing']['internal']['peers']

    with open(default_se_template, 'r') as f:
        se_template = yaml.safe_load(f)
    count = 1
    for ext_override in ext_overrides:
        app_identifier = f"{overrides['metadata']['app']}-{overrides['metadata']['revision']}" if 'revision' in overrides['metadata'] else overrides['metadata']['app']
        service_entry_name = app_identifier + '-se-' + str(count)
        se_template['metadata']['name'] = service_entry_name
        se_template['metadata']['namespace'] = namespace
        se_template['spec']['hosts'] = ext_override['hosts']
        se_template['spec']['ports'][0]['number'] = ext_override['ports'][0]
        se_ip = get_available_ip()
        if se_ip:
            se_template['spec']['addresses'] = [se_ip]
            CURRENT_ALLOCATED_IPS.extend([se_ip])
        else:
            print('No IPs available to allocate to ServiceEntry',
                file=sys.stderr)
            sys.exit(1)
        se_template['spec']['endpoints'][0]['address'] = ext_override['endpoints'][0]
        with open(output_dir + '/' + service_entry_name + '.yaml', 'w') as se:
            yaml.safe_dump(se_template, se, default_flow_style=False,
                    sort_keys=False)
        count += 1
