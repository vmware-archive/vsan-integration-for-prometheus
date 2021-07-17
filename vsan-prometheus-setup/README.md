## vsan-prometheus-setup
The vsan-prometheus-setup container is used for vCenter authorization. It will generate a bearer token for a specified
vSAN cluster. After that, Prometheus will use the generated token as authorization header for scraping vSAN metrics.  

## The facts about bearer token?
* The token is 30 characters long random string.
* The token has no expiration date, unless it has been overwritten by a new one.
* The token value can be vSAN cluster specific, different vSAN clusters have different token values.
* The vCenter credential for generating token should have Administrator role for editing cluster configuration.

## Privilege
To run this container for generating metric token, the vCenter credential is required.
Several privilege should be considered:
*  `System.view` privilege on the RootFolder;
* `System.read` privilege on cluster objects for checking vSAN metrics capability;
* `Host.Inventory.EditCluster` privilege on cluster objects for applying metrics configuration


## Usage
To generate a bearer token for vCenter authorization, the vCenter credential is required, and it prompts for the password. 
```
docker run -it vmware/vsan-prometheus-setup:v20210717 --host 10.160.29.255 --username administrator@vsphere.local --cluster VSAN-Cluster
```

Please save the token value for later usage, here is a sample output:
```
Enter password for host 10.160.29.255 and username administrator@vsphere.local:
Successfully connected to vCenter!
Successfully generate a new token:
171892aa-24dc-450f-be6b-cdc5cf
```

To ignore the interactive mode for prompting password, please pass the password directly:
```
docker run vmware/vsan-prometheus-setup:v20210717 --host 10.160.29.255 --username administrator@vsphere.local --password 'Admin!23' --cluster VSAN-Cluster
```

The sample output: 
```
Successfully connected to vCenter!
Successfully generate a new token:
ce5264fb-e17d-4ac0-a09c-e340ea
```

## Development
This container is based Photon 3.0 image with Python3 installed. 
You can update python scripts based on your needs.
To rebuild the image, you can apply the commands:
```
cd vsan-prometheus-setup
docker build -t vsan-prometheus-setup . 
```

## Aruguments
 |  Short option |  Long option | Description  | 
|:---:|:---:|---|
|  -s | --host   | Remote host to connect to (vCenter address)  |
|  -0 | --port   | Port to connect on (vCenter address) with default 443  |
|  -u | --username  | vSphere (vCenter) user name  |
|  -p | --password  | vSphere (vCenter) password  |
|  -c | --cluster  | The vSAN cluster name with default VSAN-Cluster  |