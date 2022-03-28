import os
import sys
import subprocess
from deployinator.core.envutil.envvars import check_env

def clone_repo(projectPath, user, token, version="master"):
    '''
    Clone projectPath (str, path to gitlab repo relative to gitlab.com/ftdr/) into cwd.
    '''
    if len(projectPath) == 0:
        raise AttributeError('clone_repos() requires a path to a project relative to /ftdr/. None provided.')

    if token is None:
        if check_env('CI_JOB_TOKEN'):
            token = os.environ['CI_JOB_TOKEN']

    url = "https://{user}:{token}@gitlab.com:/ftdr/{projectPath}.git".format(user=user, token=token, projectPath=projectPath)
    stream = subprocess.Popen(['git', 'clone', url, '--branch', version ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    out, Err = stream.communicate()
    if stream.returncode != 0:
        print('stdout:', out)
        print('stderr:', Err)
        raise RuntimeError(f'error: unable to clone repository: {projectPath}')
