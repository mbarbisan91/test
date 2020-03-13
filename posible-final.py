#!/usr/bin/python

# Check if the user has the Access & Secret key configured
import boto3
from boto3 import Session
s3 = boto3.resource('s3')

session = Session()
credentials = session.get_credentials()
current_credentials = credentials.get_frozen_credentials()

# Break & Exit if any of the key is not present
if current_credentials.access_key is None:
    print("Access Key missing, use  `aws configure` to setup")
    exit()

if current_credentials.secret_key is None:
    print("Secret Key missing, use  `aws configure` to setup")
    exit()

# VPC design for multi az deployments
globalVars = {}
globalVars['REGION_NAME']              = "us-west-1"
globalVars['AZ1']                      = "us-west-1a"
globalVars['AZ2']                      = "us-west-1b"
globalVars['CIDRange']                 = "10.240.0.0/23"
globalVars['az1_pvtsubnet_CIDRange']   = "10.240.0.0/25"
globalVars['az1_pubsubnet_CIDRange']   = "10.240.0.128/26"
globalVars['az1_sparesubnet_CIDRange'] = "10.240.0.192/26"
globalVars['az2_pvtsubnet_CIDRange']   = "10.240.1.0/25"
globalVars['az2_pubsubnet_CIDRange']   = "10.240.1.128/26"
globalVars['az2_sparesubnet_CIDRange'] = "10.240.1.192/26"
globalVars['Project']                  = { 'Key': 'Name',        'Value': 'AutoScaling-Test'}
globalVars['tags']                     = [{'Key': 'Owner',       'Value': 'codermaster'},
                                          {'Key': 'Environment', 'Value': 'Test'},
                                          {'Key': 'Department',  'Value': 'Testing-department'}]
# EC2 Parameters
globalVars['EC2-Amazon-AMI-ID']        = "ami-0fc61db8544a617ed" 
globalVars['EC2-InstanceType']         = "t3.micro"
globalVars['EC2-KeyName']              = globalVars['Project']['Value']+'-Key'

# AutoScaling Parameters
globalVars['ASG-LaunchConfigName']     = "ASG-Test-LaunchConfig"
globalVars['ASG-AutoScalingGroupName'] = "ASG-Test-AutoScalingGrp"

# RDS Parameters
globalVars['RDS-DBIdentifier']         = "TestDb01"
globalVars['RDS-Engine']               = "postgres"
globalVars['RDS-DBName']               = "hello_world"
globalVars['RDS-DBMasterUserName']     = "postgres"
globalVars['RDS-DBMasterUserPass']     = "test123456"
globalVars['RDS-DBInstanceClass']      = "db.t2.micro"
globalVars['RDS-DBSubnetGroup']        = "RDS-TEST-DB-Subnet-Group"

# Creating a VPC, Subnet, and Gateway
ec2       = boto3.resource('ec2', region_name=globalVars['REGION_NAME'])
ec2Client = boto3.client('ec2',   region_name=globalVars['REGION_NAME'])
vpc       = ec2.create_vpc(CidrBlock=globalVars['CIDRange'])
asgClient = boto3.client('autoscaling', region_name=globalVars['REGION_NAME'])
rds       = boto3.client('rds', region_name=globalVars['REGION_NAME'])

# AZ1 Subnet
az1_pvtsubnet   = vpc.create_subnet(CidrBlock=globalVars['az1_pvtsubnet_CIDRange'],   AvailabilityZone=globalVars['AZ1'])
az1_pubsubnet   = vpc.create_subnet(CidrBlock=globalVars['az1_pubsubnet_CIDRange'],   AvailabilityZone=globalVars['AZ1'])
az1_sparesubnet = vpc.create_subnet(CidrBlock=globalVars['az1_sparesubnet_CIDRange'], AvailabilityZone=globalVars['AZ1'])
# AZ2 Subnet
az2_pvtsubnet   = vpc.create_subnet(CidrBlock=globalVars['az2_pvtsubnet_CIDRange'],   AvailabilityZone=globalVars['AZ2'])
az2_pubsubnet   = vpc.create_subnet(CidrBlock=globalVars['az2_pubsubnet_CIDRange'],   AvailabilityZone=globalVars['AZ2'])
az2_sparesubnet = vpc.create_subnet(CidrBlock=globalVars['az2_sparesubnet_CIDRange'], AvailabilityZone=globalVars['AZ2'])

# Enable DNS Hostnames in the VPC
vpc.modify_attribute(EnableDnsSupport={'Value': True})
vpc.modify_attribute(EnableDnsHostnames={'Value': True})

# Create the Internet Gatway & Attach to the VPC
intGateway = ec2.create_internet_gateway()
intGateway.attach_to_vpc(VpcId=vpc.id)

# Create another route table for Public & Private traffic
routeTable = ec2.create_route_table(VpcId=vpc.id)
rtbAssn=[]
rtbAssn.append(routeTable.associate_with_subnet(SubnetId=az1_pubsubnet.id))
rtbAssn.append(routeTable.associate_with_subnet(SubnetId=az1_pvtsubnet.id))
rtbAssn.append(routeTable.associate_with_subnet(SubnetId=az2_pubsubnet.id))
rtbAssn.append(routeTable.associate_with_subnet(SubnetId=az2_pvtsubnet.id))

# Create a route for internet traffic to flow out
intRoute = ec2Client.create_route(RouteTableId=routeTable.id, DestinationCidrBlock='0.0.0.0/0', GatewayId=intGateway.id)

# Tag the resources
vpc.create_tags            (Tags=globalVars['tags'])
az1_pvtsubnet.create_tags  (Tags=globalVars['tags'])
az1_pubsubnet.create_tags  (Tags=globalVars['tags'])
az1_sparesubnet.create_tags(Tags=globalVars['tags'])
az2_pvtsubnet.create_tags  (Tags=globalVars['tags'])
az2_pubsubnet.create_tags  (Tags=globalVars['tags'])
az2_sparesubnet.create_tags(Tags=globalVars['tags'])
intGateway.create_tags     (Tags=globalVars['tags'])
routeTable.create_tags     (Tags=globalVars['tags'])

vpc.create_tags            (Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-vpc'}])
az1_pvtsubnet.create_tags  (Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-az1-private-subnet'}])
az1_pubsubnet.create_tags  (Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-az1-public-subnet'}])
az1_sparesubnet.create_tags(Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-az1-spare-subnet'}])
az2_pvtsubnet.create_tags  (Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-az2-private-subnet'}])
az2_pubsubnet.create_tags  (Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-az2-public-subnet'}])
az2_sparesubnet.create_tags(Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-az2-spare-subnet'}])
intGateway.create_tags     (Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-igw'}])
routeTable.create_tags     (Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-rtb'}])

# Let create the Public & Private Security Groups
elbSecGrp = ec2.create_security_group(DryRun=False,
                                      GroupName='elbSecGrp',
                                      Description='ElasticLoadBalancer_Security_Group',
                                      VpcId=vpc.id
                                      )

pubSecGrp = ec2.create_security_group(DryRun=False,
                                      GroupName='pubSecGrp',
                                      Description='Public_Security_Group',
                                      VpcId=vpc.id
                                      )

pvtSecGrp = ec2.create_security_group(DryRun=False,
                                      GroupName='pvtSecGrp',
                                      Description='Private_Security_Group',
                                      VpcId=vpc.id
                                      )

elbSecGrp.create_tags(Tags=globalVars['tags'])
pubSecGrp.create_tags(Tags=globalVars['tags'])
pvtSecGrp.create_tags(Tags=globalVars['tags'])

elbSecGrp.create_tags(Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-elb-security-group'}])
pubSecGrp.create_tags(Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-public-security-group'}])
pvtSecGrp.create_tags(Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-private-security-group'}])

# Add a rule that allows inbound SSH, HTTP, HTTPS traffic ( from any source )
ec2Client.authorize_security_group_ingress(GroupId=elbSecGrp.id,
                                           IpProtocol='tcp',
                                           FromPort=8000,
                                           ToPort=8000,
                                           CidrIp='0.0.0.0/0'
                                           )

# Allow Public Security Group to receive traffic from ELB Security group
ec2Client.authorize_security_group_ingress(GroupId=pubSecGrp.id,
                                           IpPermissions=[{'IpProtocol': 'tcp',
                                                           'FromPort': 8000,
                                                           'ToPort': 8000,
                                                           'UserIdGroupPairs': [{'GroupId': elbSecGrp.id}]
                                                           }]
                                           )
# Allow Private Security Group to receive traffic from Application Security group
ec2Client.authorize_security_group_ingress(GroupId=pvtSecGrp.id,
                                           IpPermissions=[{'IpProtocol': 'tcp',
                                                           'FromPort': 5432,
                                                           'ToPort': 5432,
                                                           'UserIdGroupPairs': [{'GroupId': pubSecGrp.id}]
                                                           }]
                                           )

ec2Client.authorize_security_group_ingress(GroupId=pubSecGrp.id,
                                           IpProtocol='tcp',
                                           FromPort=8000,
                                           ToPort=8000,
                                           CidrIp='0.0.0.0/0'
                                           )
ec2Client.authorize_security_group_ingress(GroupId=pubSecGrp.id,
                                           IpProtocol='tcp',
                                           FromPort=443,
                                           ToPort=443,
                                           CidrIp='0.0.0.0/0'
                                           )
ec2Client.authorize_security_group_ingress(GroupId=pubSecGrp.id,
                                           IpProtocol='tcp',
                                           FromPort=22,
                                           ToPort=22,
                                           CidrIp='0.0.0.0/0'
                                           )



# Creation of bucket on S3 
bucket_name = 's3storage-{}'
print('Creating new bucket with name: {}'.format(bucket_name))

s3.create_bucket(Bucket=bucket_name)
s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={
    'LocationConstraint': 'us-west-1'})

customEC2Keys = ec2Client.describe_key_pairs()['KeyPairs']
if not next((key for key in customEC2Keys if key["KeyName"] == globalVars['EC2-KeyName']), False):
    ec2_key_pair = ec2.create_key_pair(KeyName=globalVars['EC2-KeyName'])
    print("New Private Key created,Save the below key-material\n\n")
    print(ec2_key_pair.key_material)

userDataCode = """
#!/bin/bash
set -e -x

sudo yum update
sudo amazon-linux-extras install epel
sudo yum install s3fs-fuse docker -y

mkdir -p /var/log/helloworld

# Target Bucket
aws s3 mb s3://s3storage

# Mount the S3 Bucket as filesystem
s3fs s3storage /var/log/helloworld -o iam_role=ec2-to-s3 

# Verify with Command
df -h /var/log/helloworld

# Create Object
cd /var/log/helloworld
touch "write-test"

#Docker configure 
sudo usermod -a -G docker ec2-user
sudo service docker start
sudo chkconfig docker on

#Docker user config
useradd dockeradmin
passwd dockeradmin
usermod -aG docker dockeradmin

#Docker-compose installation
sudo curl -L https://github.com/docker/compose/releases/download/1.25.0/docker-compose-`uname -s`-`uname -m` | sudo tee /usr/local/bin/docker-compose > /dev/null

sudo chmod +x /usr/local/bin/docker-compose

ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

#Clon and setup application 
git clone https://github.com/scm-spain/devops-test-helloworld-app

cd devops-test-helloworld-app

docker-compose up
 
./gradlew run
"""

# Create the Public App Test Instance
instanceLst = ec2.create_instances(ImageId=globalVars['EC2-Amazon-AMI-ID'],
                                   MinCount=1,
                                   MaxCount=1,
                                   KeyName=globalVars['EC2-KeyName'],
                                   UserData=userDataCode,
                                   InstanceType=globalVars['EC2-InstanceType'],
                                   NetworkInterfaces=[
                                       {
                                           'SubnetId': az1_pubsubnet.id,
                                           'Groups': [pubSecGrp.id],
                                           'DeviceIndex': 0,
                                           'DeleteOnTermination': True,
                                           'AssociatePublicIpAddress': True,
                                       }
                                   ]
                                   )

asgLaunchConfig = asgClient.create_launch_configuration(
    LaunchConfigurationName=globalVars['ASG-LaunchConfigName'],
    ImageId=globalVars['EC2-Amazon-AMI-ID'],
    KeyName=globalVars['EC2-KeyName'],
    SecurityGroups=[pubSecGrp.id],
    UserData=userDataCode,
    InstanceType=globalVars['EC2-InstanceType'],
    InstanceMonitoring={'Enabled': False },
    EbsOptimized=False,
    AssociatePublicIpAddress=False
)

# create Auto-Scaling Group
ASGSubnets = az1_pubsubnet.id + "," +az2_pubsubnet.id
asGroup=asgClient.create_auto_scaling_group(
    AutoScalingGroupName=globalVars['ASG-AutoScalingGroupName'],
    LaunchConfigurationName=globalVars['ASG-LaunchConfigName'],
    MinSize=1,
    MaxSize=3,
    DesiredCapacity=2,
    DefaultCooldown=120,
    HealthCheckType='EC2',
    HealthCheckGracePeriod=60,
    Tags=globalVars['tags'],
    VPCZoneIdentifier=ASGSubnets
    )

asgClient.create_or_update_tags(
    Tags=[
        {
            'ResourceId': globalVars['ASG-AutoScalingGroupName'],
            'ResourceType': 'auto-scaling-group',
            'Key': 'Name',
            'Value': globalVars['Project']['Value'] + '-ASG-Group',
            'PropagateAtLaunch': True
        },
    ]
)

## First lets create the RDS Subnet Groups
rdsDBSubnetGrp = rds.create_db_subnet_group(DBSubnetGroupName=globalVars['RDS-DBSubnetGroup'],
                                            DBSubnetGroupDescription=globalVars['RDS-DBSubnetGroup'],
                                            SubnetIds=[az1_pvtsubnet.id, az2_pvtsubnet.id],
                                            Tags=[{'Key': 'Name',
                                                   'Value': globalVars['Project']['Value'] + '-DB-Subnet-Group'}]
                                            )

rdsInstance = rds.create_db_instance(DBInstanceIdentifier=globalVars['RDS-DBIdentifier'],
                       AllocatedStorage=5,
                       DBName=globalVars['RDS-DBName'],
                       Engine=globalVars['RDS-Engine'],
                       Port=5432,
                       StorageType='gp2',
                       StorageEncrypted=False,
                       AutoMinorVersionUpgrade=False,
                       MultiAZ=True,
                       MasterUsername=globalVars['RDS-DBMasterUserName'],
                       MasterUserPassword=globalVars['RDS-DBMasterUserPass'],
                       DBInstanceClass=globalVars['RDS-DBInstanceClass'],
                       VpcSecurityGroupIds=[pvtSecGrp.id],
                       DBSubnetGroupName=globalVars['RDS-DBSubnetGroup'],
                       CopyTagsToSnapshot=True,
                       Tags=[{'Key': 'Name', 'Value': globalVars['Project']['Value'] + '-RDS-Instance'}])

waiter = rds.get_waiter('db_instance_available')
waiter.wait(DBInstanceIdentifier=globalVars['RDS-DBIdentifier'])

resp = rds.describe_db_instances(DBInstanceIdentifier= globalVars['RDS-DBIdentifier'])
db_instances = resp['DBInstances']
if len(db_instances) != 1:
    raise Exception('This should not have happened')
db_instance = db_instances[0]
status = db_instance['DBInstanceStatus']
if status == 'available':
    rdsEndpointDict = db_instance['Endpoint']
    globalVars['Endpoint'] = rdsEndpointDict['Address']

###### Print to Screen ########
print("VPC ID                    : {0}".format(vpc.id))
print("AZ1 Public Subnet ID      : {0}".format(az1_pubsubnet.id))
print("AZ1 Private Subnet ID     : {0}".format(az1_pvtsubnet.id))
print("AZ1 Spare Subnet ID       : {0}".format(az1_sparesubnet.id))
print("Internet Gateway ID       : {0}".format(intGateway.id))
print("Route Table ID            : {0}".format(routeTable.id))
print("Public Security Group ID  : {0}".format(pubSecGrp.id))
print("Private Security Group ID : {0}".format(pvtSecGrp.id))
print("EC2 Key Pair              : {0}".format(globalVars['EC2-KeyName']))
print("EC2 PublicIP              : {0}".format(globalVars['EC2-KeyName']))
print("RDS Endpoint              : {0}".format(globalVars['Endpoint']))
###### Print to Screen ########

###Clean Up Resources 

def cleanAll(resourcesDict=None):
    # Delete the RDS Instance
    waiter = rds.get_waiter('db_instance_deleted')
    waiter.wait(DBInstanceIdentifier=globalVars['RDS-DBIdentifier'])
    rds.delete_db_instance(DBInstanceIdentifier=globalVars['RDS-DBIdentifier'], SkipFinalSnapshot=True)
    # Delete the instances
    ids = []
    for i in instanceLst:
        ids.append(i.id)

    ec2.instances.filter(InstanceIds=ids).terminate()

    # Wait for the instance to be terminated
    waiter = ec2Client.get_waiter('instance_terminated')
    waiter.wait(InstanceIds=[ids])
    ec2Client.delete_key_pair(KeyName=globalVars['EC2-KeyName'])

    # Delete Routes & Routing Table
    for assn in rtbAssn:
        ec2Client.disassociate_route_table(AssociationId=assn.id)

    routeTable.delete()

    # Delete Subnets
    az1_pvtsubnet.delete()
    az1_pubsubnet.delete()
    az1_sparesubnet.delete()

    # Detach & Delete internet Gateway
    ec2Client.detach_internet_gateway(InternetGatewayId=intGateway.id, VpcId=vpc.id)
    intGateway.delete()

    # Delete Security Groups
    pubSecGrp.delete()
    pvtSecGrp.delete()

    vpc.delete()