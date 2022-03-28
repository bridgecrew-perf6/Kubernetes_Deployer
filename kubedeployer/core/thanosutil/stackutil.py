import subprocess
import sys
import yaml

def get_stack(effort_name, environment, stack_dir):
    '''
    Provided effort_name, environment, and a directory to the stack definitions, this function will return the stack definition as a python dict.
    '''
    if len(effort_name) == 0:
        raise AttributeError('get_stack() expects at least 3 arguments, no effort provided.')
    
    if len(environment) == 0:
        raise AttributeError('get_stack() expects at least 3 arguments, no environment name provided')

    if len(stack_dir) == 0:
        raise AttributeError('get_stack() expects at least 3 arguments, no stack directory name provided')
    
    thanos_out = subprocess.Popen(['thanosctl', 'stacks', '--store.bleve.path', stack_dir, '--output', 'yaml', 'find', '--stack.effort', effort_name, '--stack.environment', environment], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    output, Err = thanos_out.communicate()
    if thanos_out.returncode != 0:
        print('stdout:', output)
        print('stderr:', Err)
        raise RuntimeError(f'Looking up target clusters failed. Please see thanosctl output above.')
    output_dict = yaml.safe_load(output)
    return output_dict
