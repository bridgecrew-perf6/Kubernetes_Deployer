import os
import sys

def check_env(envVar):
    '''
    Check if an environment variable is set and fail with a sensible message otherwise.
    '''
    if len(envVar) == 0:
            raise AttributeError('check_env() expects atleast 1 argument, none given.')

    try:
        foo = os.environ[envVar]
    except KeyError:
        raise AttributeError(f'Failed parsing environment variables. No variable found matching: {envVar}. Please resolve this and try again.')
    
    return True

def softCheck_env(envVar):
    '''
    Check if an environment variable is set and fail with a sensible message otherwise.
    '''
    if len(envVar) == 0:
            raise AttributeError('check_env() expects atleast 1 argument, none given.')

    try:
        foo = os.environ[envVar]
    except KeyError:
        return False
    
    return True