"""
CLI utility for deploying frontdoor services to thanos clusters.
"""
from setuptools import find_packages, setup

dependencies = [
    'click',
    'pyyaml',
    'requests',
    'jsonpath-ng',
    'kubernetes',
    'edgegrid-python',
    'google-cloud',
    'pymongo',
    'dnspython',
    'yamale'
]

test_dependencies = [
    'coverage',
    'pytest'
]

setup(
    name='deployinator',
    version='1.2.54',
    url='https://gitlab.com/ftdr/devops/tools/deployinator.git',
    license='Apache2',
    author='devops@ahso365.onmicrosoft.com',
    author_email='devops@ahso365.onmicrosoft.com',
    description='CLI utility for deploying frontdoor services to thanos clusters.',
    long_description=__doc__,
    packages=find_packages(exclude=['tests', 'test_lint.py', 'test_deploy.py', 'test_make.py']),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=dependencies,
    tests_require=test_dependencies,
    entry_points={
        'console_scripts': [
            'deployinator = deployinator.cli:cli',
        ],
    },
    package_data={
        "": ["*.yaml"]
    },
    classifiers=[
        # As from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        # 'Development Status :: 1 - Planning',
        # 'Development Status :: 2 - Pre-Alpha',
        # 'Development Status :: 3 - Alpha',
        # 'Development Status :: 4 - Beta',
        'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: License',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Operating System :: Windows',
        'Programming Language :: Python',
        # 'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
