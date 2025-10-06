# Cloud Providers Guide

Cloud NetTest Framework supports multiple cloud providers for hosting probe nodes. This guide covers provider-specific details and best practices.

## Supported Providers

- ✅ **AWS** (Amazon Web Services) - Fully supported
- ✅ **Azure** (Microsoft Azure) - Configuration ready
- ✅ **GCP** (Google Cloud Platform) - Configuration ready

## AWS (Amazon Web Services)

### Default Configuration

```yaml
provider: aws
ssh_user: ubuntu          # For Ubuntu AMIs
pkg_mgr: apt
free_tier_instance: t2.micro
metadata_url: http://169.254.169.254/latest/meta-data/
```

### Provisioning Free-Tier Probes

#### Using AWS Console

1. Launch EC2 Instance
   - AMI: Ubuntu 22.04 LTS
   - Instance Type: t2.micro (free tier eligible)
   - VPC: Default or custom
   - Security Group: Allow SSH (port 22)
   - Key Pair: Use existing or create new

2. Configure Security Group
   ```
   Inbound Rules:
   - SSH (22) from your IP
   
   Outbound Rules:
   - All traffic (for testing)
   ```

3. Note instance details:
   - Instance ID
   - Public IP
   - Private IP
   - Region

#### Using AWS CLI

```bash
# Create security group
aws ec2 create-security-group \
  --group-name cnf-probes \
  --description "CNF probe nodes"

# Allow SSH
aws ec2 authorize-security-group-ingress \
  --group-name cnf-probes \
  --protocol tcp \
  --port 22 \
  --cidr your-ip/32

# Launch instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \  # Ubuntu 22.04 (check for latest)
  --instance-type t2.micro \
  --key-name your-key \
  --security-groups cnf-probes \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=cnf-probe01}]'
```

### Instance Metadata

The framework can automatically fetch AWS metadata:

```python
from cnf.providers.aws import AWSProvider
metadata = await AWSProvider.get_instance_metadata(host)
```

Fetches:
- Instance ID
- Instance Type
- Availability Zone
- Region
- Public IPv4
- Private IPv4
- AMI ID

### Regions

Optimal regions for Oracle OCI testing:

| AWS Region | Best For | Oracle Endpoint | Baseline Latency |
|------------|----------|-----------------|------------------|
| **us-east-1** | Oracle Ashburn | us-ashburn-1 | ~1ms |
| **us-west-1** | Oracle San Jose | us-sanjose-1 | <1ms |
| **us-west-2** | Oracle Phoenix | us-phoenix-1 | ~19ms |
| **us-east-2** | Balanced | Multiple | ~14ms |

### Free Tier Limits

- **750 hours/month** of t2.micro (Linux)
- 30 GB storage
- 15 GB bandwidth out
- Covers ~3 instances running 24/7

### Tool Installation

```bash
# Bootstrap script
./scripts/bootstrap_hosts.sh apt
```

Or manually:
```bash
sudo apt-get update
sudo apt-get install -y iputils-ping traceroute mtr-tiny curl dnsutils iperf3 tcpdump
```

## Azure (Microsoft Azure)

### Default Configuration

```yaml
provider: azure
ssh_user: azureuser       # Default for Azure VMs
pkg_mgr: apt
free_tier_instance: B1s
metadata_url: http://169.254.169.254/metadata/instance?api-version=2021-02-01
```

### Provisioning Free-Tier Probes

#### Using Azure Portal

1. Create Virtual Machine
   - Image: Ubuntu 22.04 LTS
   - Size: B1s (free tier eligible)
   - Authentication: SSH public key
   - Inbound ports: SSH (22)

2. Network Security Group
   ```
   Inbound Security Rules:
   - SSH (22) from your IP
   
   Outbound Security Rules:
   - Allow all (default)
   ```

#### Using Azure CLI

```bash
# Create resource group
az group create --name cnf-probes --location eastus

# Create VM
az vm create \
  --resource-group cnf-probes \
  --name cnf-eastus-probe01 \
  --image UbuntuLTS \
  --size Standard_B1s \
  --admin-username azureuser \
  --ssh-key-values @~/.ssh/id_rsa.pub \
  --public-ip-sku Standard

# Get public IP
az vm list-ip-addresses \
  --resource-group cnf-probes \
  --name cnf-eastus-probe01 \
  --output table
```

### Instance Metadata

```python
from cnf.providers.azure import AzureProvider
metadata = await AzureProvider.get_instance_metadata(host)
```

Fetches:
- VM ID
- VM Size
- Location (region)
- Subscription ID
- Resource Group

### Regions

Recommended regions for Oracle testing:

| Azure Region | Oracle Proximity | Use Case |
|--------------|------------------|----------|
| **East US** | Medium | Oracle Ashburn testing |
| **West US 2** | Good | Oracle Phoenix/San Jose |
| **Central US** | Balanced | Multi-region testing |

### Free Tier Limits

- **750 hours/month** of B1S Linux VM
- 64 GB storage (managed disk)
- 15 GB bandwidth out
- Covers 1 instance running 24/7

### Adding to Framework

```yaml
# configs/inventory.yaml
hosts:
  - id: azure-eastus-probe01
    provider: azure
    region: eastus
    hostname: probe01
    public_ip: 20.x.x.x
    ssh_user: azureuser
    ssh_key: ~/.ssh/id_rsa
    status: active
    capabilities:
      - icmp_ping
      - tcp_connect
      - https_timing
      - traceroute
```

## GCP (Google Cloud Platform)

### Default Configuration

```yaml
provider: gcp
ssh_user: debian          # Or your GCP username
pkg_mgr: apt
free_tier_instance: e2-micro
metadata_url: http://metadata.google.internal/computeMetadata/v1/
```

### Provisioning Free-Tier Probes

#### Using GCP Console

1. Create Compute Engine Instance
   - Boot disk: Ubuntu 22.04 LTS
   - Machine type: e2-micro (free tier)
   - Region: us-west1, us-central1, or us-east1
   - Firewall: Allow SSH

2. Firewall Rules
   ```
   Ingress:
   - tcp:22 from your IP
   
   Egress:
   - Allow all
   ```

#### Using gcloud CLI

```bash
# Create firewall rule
gcloud compute firewall-rules create allow-ssh-cnf \
  --allow tcp:22 \
  --source-ranges=your-ip/32 \
  --description="SSH for CNF probes"

# Create instance
gcloud compute instances create cnf-us-east1-probe01 \
  --machine-type e2-micro \
  --zone us-east1-b \
  --image-family ubuntu-2204-lts \
  --image-project ubuntu-os-cloud \
  --boot-disk-size 30GB \
  --tags cnf-probe

# Get external IP
gcloud compute instances describe cnf-us-east1-probe01 \
  --zone us-east1-b \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

### Instance Metadata

```python
from cnf.providers.gcp import GCPProvider
metadata = await GCPProvider.get_instance_metadata(host)
```

Fetches:
- Instance ID
- Instance Name
- Machine Type
- Zone
- Project ID

### Regions

Free tier eligible regions:

| GCP Region | Zone | Oracle Proximity |
|------------|------|------------------|
| **us-west1** | us-west1-a | Good for San Jose/Phoenix |
| **us-central1** | us-central1-a | Balanced |
| **us-east1** | us-east1-b | Medium for Ashburn |

### Free Tier Limits

- **1 e2-micro instance** per month (specific regions only)
- 30 GB storage
- 1 GB egress (North America)
- Must be in us-west1, us-central1, or us-east1

### SSH Key Setup

GCP uses project or instance metadata for SSH keys:

```bash
# Add SSH key to project
gcloud compute project-info add-metadata \
  --metadata ssh-keys="your-username:$(cat ~/.ssh/id_rsa.pub)"
```

## Multi-Provider Strategy

### Optimal Configuration

```yaml
# configs/inventory.yaml
hosts:
  # AWS - Oracle Ashburn optimal
  - id: aws-us-east-1-probe01
    provider: aws
    region: us-east-1
    notes: "1ms to Oracle Ashburn"
  
  # AWS - Oracle San Jose optimal
  - id: aws-us-west-1-probe01
    provider: aws
    region: us-west-1
    notes: "<1ms to Oracle San Jose"
  
  # Azure - Additional coverage
  - id: azure-eastus-probe01
    provider: azure
    region: eastus
    notes: "Azure east coast perspective"
  
  # GCP - West coast coverage
  - id: gcp-us-west1-probe01
    provider: gcp
    region: us-west1
    notes: "GCP west coast perspective"
```

### Cost Optimization

**Free Tier Strategy**:
1. AWS: 3x t2.micro instances (750 hours/month each)
2. Azure: 1x B1s instance (750 hours)
3. GCP: 1x e2-micro instance (744 hours)

**Total**: 5 probe nodes, $0/month within free tiers

**Cost if exceeding**:
- AWS t2.micro: ~$8/month
- Azure B1s: ~$8/month
- GCP e2-micro: ~$6/month

## Provider-Specific Considerations

### AWS

**Pros**:
- Best Oracle OCI connectivity
- Most regions
- Easy automation
- Comprehensive free tier

**Cons**:
- Complex pricing
- Many service options

**Best For**: Primary Oracle OCI testing

### Azure

**Pros**:
- Simple VM management
- Good global coverage
- Integrated monitoring

**Cons**:
- Fewer free tier hours than AWS
- Limited free tier regions

**Best For**: Secondary testing, multi-cloud validation

### GCP

**Pros**:
- Simple pricing
- Fast instance creation
- Good network performance

**Cons**:
- Limited free tier (1 instance)
- Specific region requirement
- Smaller region selection

**Best For**: West coast testing, multi-cloud perspective

## Comparison Matrix

| Feature | AWS | Azure | GCP |
|---------|-----|-------|-----|
| **Free Tier Instances** | 750h (unlimited instances) | 750h (1 instance) | 1 instance always free |
| **Regions for Oracle** | Excellent | Good | Good |
| **Setup Complexity** | Medium | Medium | Low |
| **CLI Tools** | aws-cli | az-cli | gcloud |
| **Metadata Service** | IMDSv2 | Standard | Metadata server |
| **SSH User** | ubuntu | azureuser | Project username |

## Migration Between Providers

To move a test plan to different providers:

```yaml
# Before (AWS only)
probes:
  include:
    - provider: aws
      regions: ["us-east-1"]

# After (Multi-cloud)
probes:
  include:
    - provider: aws
      regions: ["us-east-1"]
    - provider: azure
      regions: ["eastus"]
    - provider: gcp
      regions: ["us-east1"]
```

---

**Recommendation**: Start with AWS for Oracle OCI testing (best performance), then add Azure/GCP for multi-cloud validation.
