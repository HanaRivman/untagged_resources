import logging
import boto3
import smtplib
import itertools
import csv

logger = logging.getLogger()
logger.setLevel(logging.INFO)
session = boto3.Session()
client = session.client('ec2', region_name='us-east-1')

# write thק data to CSV
def write_to_csv(columns, dict_data, file_name):
    try:
        with open(file_name, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            for data in dict_data:
                writer.writerow(data)
    except IOError:
        print("I/O error")

# get a tag value if exists
def get_tag_value(tag_key, client):
    if 'Tags' in str(client):
        for tag in client['Tags']:
            if tag.values()[1] == tag_key:
                return tag.values()[0]
    return ' '

# get the tags of a client
def get_tags_for_client(tags_array):
    keys = []
    for tag in tags_array:
        keys.append(tag.values()[1])
    keys.sort()
    return keys

# get all tags the client lacks
def find_tag_diffs(client, default_tags):
    if 'Tags' in str(client):
        client_tags = get_tags_for_client(client['Tags'])
        tags_not_found = list(set(default_tags) - (set(client_tags)))
    else:
        tags_not_found = default_tags
    tags_not_found = " ".join(tags_not_found)
    return tags_not_found

# get all untagged volumes
def untagged_volumes(tags):
    csv_columns = ['InstanceName', 'VolumeID', 'AttachedDevice', 'TagsMissing']
    untagged_volumes = []
    response = client.describe_volumes()
    for volume in response['Volumes']:
        if len(volume['Attachments']):
            attached_device = volume['Attachments'][0]['InstanceId']
        else:
            attached_device = "None"
        instance_name = get_tag_value('instance_name', volume)
        tags_not_found = find_tag_diffs(volume,tags)
        if tags_not_found:
            untagged_volume = {'InstanceName': instance_name, 'VolumeID': volume['VolumeId'], 'AttachedDevice': attached_device, 'TagsMissing': tags_not_found}
            untagged_volumes.append(untagged_volume)

    write_to_csv(csv_columns, untagged_volumes, "untagged_volumes.csv")

# get all untagged EC2 instances
def untagged_ec2s(tags):
    csv_columns = ['Name', 'InstanceId', 'InstanceLifecycle', 'InstanceState', 'TagsMissing']
    untagged_ec2s = []
    response = client.describe_instances()
    for reservation in response['Reservations']:
        instance = reservation['Instances'][0]
        tags_not_found = find_tag_diffs(instance,tags)
        if 'InstanceLifecycle' in instance.keys():
            lifecycle = instance['InstanceLifecycle']
        else:
            lifecycle = 'normal'
        name = get_tag_value('Name', instance)
        if tags_not_found:
            untagged_ec2 = {'Name': name, 'InstanceId': instance['InstanceId'], 'InstanceLifecycle': lifecycle, 'InstanceState': instance['State']['Name'], 'TagsMissing': tags_not_found}
            untagged_ec2s.append(untagged_ec2)

    write_to_csv(csv_columns, untagged_ec2s, "untagged_ec2s.csv")


if __name__ == "__main__":
    EBS_tags = ['chef_role', 'component', 'fiverr_group', 'instance_name', 'team']
    EC2_tags = ['Name', 'chef_role', 'component', 'fiverr_group', 'group', 'team']
    untagged_volumes(EBS_tags)
    untagged_ec2s(EC2_tags)
