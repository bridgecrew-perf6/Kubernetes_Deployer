import subprocess
import os

def helm_test(deployName, deployNamespace, inputValues, chartName):
    '''
    Use helm to create a deployment called deployName. This function will run helm with the --dry-run --debug flags in order to evaluate the output.
    '''
    helmTestRun = subprocess.Popen(['helm', 'upgrade', '--install', '--debug', '--dry-run', '-v', '3', '--namespace', deployNamespace, '-f', inputValues, deployName, chartName], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    helmTest, helmTestErr = helmTestRun.communicate()
    if not helmTestRun.returncode == 0:
        print(helmTest, helmTestErr)
        raise RuntimeError(f'Helm failed to deploy {deployName} in namespace {deployNamespace} and exited with return code: {helmTestRun.returncode} , please see the error message above.')
    print(helmTest, helmTestErr)

def helm_install(deployName, deployNamespace, inputValues, chartName):
    '''
    Use helm to create a deployment called deployName.
    '''
    helmInstallRun = subprocess.Popen(['helm', 'upgrade', '--install', '--namespace', deployNamespace, '-f', inputValues, deployName, chartName], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    helmInstall, helmInstallErr = helmInstallRun.communicate()
    if not helmInstallRun.returncode == 0:
        if "field is immutable" in str(helmInstallErr):
            print("uninstall release due to immutable field")
            helmRunUninstall = subprocess.Popen(['helm', 'uninstall', deployName, '--namespace', deployNamespace], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = helmRunUninstall.communicate()
            print(stdout, stderr)
            helmInstallRunForce = subprocess.Popen(['helm', 'upgrade', '--install', '--namespace', deployNamespace, '-f', inputValues, deployName, chartName], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            helmInstallForce, helmInstallErrForce = helmInstallRunForce.communicate()
            print(helmInstallForce, helmInstallErrForce)
        else:
            print(helmInstall, helmInstallErr)
            raise RuntimeError(f'Helm failed to deploy {deployName} in namespace {deployNamespace} and exited with return code: {helmInstallRun.returncode} Please review the helm errors and try again.')
    print(helmInstall)

