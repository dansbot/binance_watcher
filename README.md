# Binance Trade Websocket Watchers (w/ Kubernetes)

This repo is used to connect to record trades or k-lines from Binance US websockets to a postgres database.

This code is designed to be executed on a kubernetes cluster. For details on how to use kubernetes, [go here](https://kubernetes.io/docs/tutorials/kubernetes-basics/)

For development this code was written for Kubernetes being run with Docker Desktop. The yaml files in the [k8s](https://github.com/dansbot/binance_watcher/tree/main/k8s)
folder are written with this in mind. Details on how to change these are provided in [k8s/README.md](https://github.com/dansbot/binance_watcher/tree/main/k8s) and [srd/README.md](https://github.com/dansbot/binance_watcher/tree/main/src) files.

## Updating watcher-deployment.yaml
k8s/watcher-deployments.yaml contains deployments for the top 100 most traded pairs as of Feb. 14, 2023. These deployments can 
be modified by running **configure_watcher_deployments.py** as follows. 

Install the required dependencies:
   - `pyyaml` library: can be installed using `pip install PyYAML==6.0`
   - `python-binance` library: can be installed using `pip install python-binance==1.0.16`

Run the **configure_watcher_deployments.py** script from the command line:
```commandline
python configure_watcher_deployments.py [--rank] [--limit NUMBER]
```
- If --rank flag is present, the script will sort the asset pairs by the number of trades.
- If --limit flag is present, the script will limit the number of asset pairs to NUMBER.

The script will create a YAML file named k8s/watcher-deployments.yaml that contains the deployment information.

## Run with Kubernetes on your local machine
1. Install Docker Desktop. Instructions found [here](https://docs.docker.com/desktop/install/mac-install/)
2. Install Kubernetes for Docker. Instructions found [here](https://docs.docker.com/desktop/kubernetes/)
3. Sign up for Binance US, and get an API key and secret.
   1. [signup here](https://www.binance.us/register)
   2. [create api key instructions](https://support.binance.us/hc/en-us/articles/360051091473-How-To-Create-an-API-Key-on-Binance-US)
4. Update k8s/watcher-config.yaml with your API key and secret.
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
4. Run the deployment.py script from the root of the repo.
- Install the required dependencies:
   - `pyyaml` library: can be installed using `pip install PyYAML==6.0`
   - `python-binance` library: can be installed using `pip install python-binance==1.0.16`
```commandline
python deploy.py
```
This will create a postgres service that can be accessed 