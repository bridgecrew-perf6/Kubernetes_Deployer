# Kube-deployer

CLI tool for helping deploy Services to our CaaS instances per Developer-Defined Service Config files

## Pre-reqs

- virtualenv
- pipx (pip install pipx)
- git
- gcloud cli
- kubectl
- Python 3 virtual environment.

## Installation

To install, run 'pipx install .'. To update, run 'pipx install --force .'

## Releasing

1. Create a feature branch
2. Add changes
3. Update [CHANGELOG.md](./CHANGELOG.md) to add a new version section and relevant details
4. Merge to master
5. Tag a version of your code, such as following.  Wait for any CICD jobs to finish before moving to step 6.

    ```bash
    git tag v1.0.0 master
    git push origin v1.0.0
    ```

6. Update version in DEPLOYINATOR_VERSION variable under `geek` group in Gitlab or CaaS helper container or any other location that needs to be updated.
7. [Optional] Select Charts repo version (tag/branch) using CHARTS_VERSION environment variable.

## Input DSL Example

```yaml
kind: thanos.internal.com/service/deployment
version: v1
metadata:
  app: someName
  effort: ahs
  env: infra-alpha
  labels:
    component: backend
    applicationtype: go-lang
deployment:
  service_port: 1337
  replicas: 1
  maxsurge: 1
  maxunavailable: 1
  regions:
    - name: us-central
      zone: 1
    - name: us-west
      zone: 1
  env:
    - name: test
      value: value
    - name: baz
      type: ci
      valueFrom: GITLAB_BAZ_VALUE
routing:
  edge:
    hosts:
    - host:
        type: global
        name: dev.apis.linuxgeekstuffs.com
    - host:
        type: local
        name: dev.apis.internal.com
    routes:
      # array of route objects
      http:
        - match:  # match uris
            - uri:
                prefix: /app/
            - uri:
                prefix: /bar/
          rewrite: 
            uri: /baz # optionally rewrite the matches
          gatewaySelectors:
            - local
        - match:  # match uris
            - uri:
                prefix: /v3/
            - uri:
                prefix: /v1/
          rewrite: 
            uri: /foo # optionally rewrite the matches
          gatewaySelectors:
            - global
        - match:  # match uris
            - uri:
                prefix: /v4/
            - uri:
                prefix: /v2/
  internal:
    peers:
    - hosts:
      - ratings.bookinfo.global
      ports:
      - 9080
      endpoints:
      - ingress.1.demo.mc-peltdemos-b.gcp.us-central1.mesh.internal.com
    - hosts:
      - service-bar.namespace-bar.global
      ports:
      - 9443
      endpoints:
      - ingress.1.cluster.project.gcp.us-central1.mesh.internal.com
```

## Schema validator

- https://github.com/23andMe/Yamale
