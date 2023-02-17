# Binance-US Websocket Watchers (w/ Kubernetes)

This repo is used to record trades or k-lines from Binance US websockets to a postgres database.

This code is designed to be executed on a kubernetes cluster. For details on how to use kubernetes, [go here](https://kubernetes.io/docs/tutorials/kubernetes-basics/)

For development this code was written for Kubernetes being run with Docker Desktop. The yaml files in the [k8s](https://github.com/dansbot/binance_watcher/tree/main/k8s)
folder are written with this in mind.

## Run with Kubernetes on your local machine
1. Install Docker Desktop. Instructions found [here](https://docs.docker.com/desktop/install/mac-install/)
2. Install Kubernetes for Docker. Instructions found [here](https://docs.docker.com/desktop/kubernetes/)
3. Run Docker Desktop and confirm Kubernetes is running as well.
4. Sign up for Binance US, and get an API key and secret.
   1. [signup here](https://www.binance.us/register)
   2. [create api key instructions](https://support.binance.us/hc/en-us/articles/360051091473-How-To-Create-an-API-Key-on-Binance-US)
5. Update k8s/watcher-config.yaml with your API key and secret.
```yaml
  BINANCE_API_KEY: your_api_key
  BINANCE_API_SECRET: your_api_secret
```
5. (Optional) Update the watcher-deployments.yaml file with [configure_watcher_deployments.py](##Updating watcher-deployment.yaml)
6. Build the "binance-watcher" docker image.
```commandline
cd ./src
docker build -t binance-watcher .
```
7. Run the [deployment.py](##deploy.py) script from the root of the repo.
   

## Updating watcher-deployment.yaml
k8s/watcher-deployments.yaml contains deployments for the top 100 most traded pairs as of Feb. 17, 2023. These deployments can 
be modified by running **configure_watcher_deployments.py** as follows.

This Python script generates Kubernetes deployment YAML files for Binance assets that include USD. The generated deployment YAML files are based on a deployment template specified in a separate YAML file.

The script uses the Binance API to retrieve the list of assets, filters the ones that include USD, and then optionally ranks the filtered assets by the number of trades over the last 150 days. The top N assets (determined by an optional limit argument) are then used to generate deployment YAML files by substituting asset-specific information into the deployment template.

Install the required dependencies:
   - `pyyaml` library: can be installed using `pip install PyYAML==6.0`
   - `python-binance` library: can be installed using `pip install python-binance==1..16`

Run the **configure_watcher_deployments.py** script from the command line:
```commandline
python configure_watcher_deployments.py [--rank] [--limit NUMBER]
```
- If `--rank flag` is present, the script will sort the asset pairs by the number of trades.
- If `--limit flag` is present, the script will limit the number of asset pairs to NUMBER.

The script will create a YAML file named k8s/watcher-deployments.yaml that contains the deployment information.

### Notes
- The deployment template is expected to be located at k8s/templates/watcher-deployment-template.yaml. 
- The generated deployment YAML files will be based on the template, but with the name and command-line arguments of the container customized for each asset.
- The script expects the Binance API key and secret to be set as environment variables `BINANCE_API_KEY` and `BINANCE_API_SECRET`, respectively.


## deploy.py
This is a Python script that helps manage Kubernetes resources by applying a list of YAML files to a cluster, waiting for the resources to become available and cleaning up existing resources if necessary.

The script uses the `kubectl` command-line tool to apply YAML files to the cluster, and provides the following functions:

- `wait_until_running`: waits for a deployment to be in the "Running" state, or raises an error if the timeout is exceeded. The primary use of this function is to ensure that Kubernetes resources are populated in the correct order and that any dependencies are met before proceeding.
- `get_kinds`: extracts the kind from each of the YAML files and returns a set of unique kinds.
- `clean_start`: deletes existing resources and starts new resources, optionally skipping deletion of PersistentVolumes.
- `start`: applies the YAML files to the cluster.

### Prerequisites
To use this script, you will need to have kubectl installed and configured to communicate with your Kubernetes cluster.

- python dependencies:
  - `pyyaml` library: can be installed using `pip install PyYAML==6.0`
  - `python-binance` library: can be installed using `pip install python-binance==1.0.16`

### Usage
You can run the script using the following command:

```commandline
python deploy.py [OPTIONS]
```
The following options are available:

- `--clean` or `-c`: performs a clean start by deleting all existing resources and starting new resources.
- `--new_volume` or `-nv`: when used with the --clean option, skips the deletion of PersistentVolumes.

### Configuration
You can configure the list of YAML files to be applied to the cluster by modifying the YAML_FILES list at the top of the script. The default list includes the following files:

```python
YAML_FILES = [
    "k8s/postgres.yaml",    
    "k8s/watcher-config.yaml",
    "k8s/watcher-deployments.yaml",
]
```

Disclaimer
This script is provided as-is and without warranty of any kind. Use it at your own risk.
