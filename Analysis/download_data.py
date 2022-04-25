import os
import re
import boto3

BUCKET_NAME = 'projects.irll'
SAVE_DIR = 'data/trials'
PROJECT_IDS = [
    'exp-mario-binary-feedback',
    'exp-breakout-binary-feedback',
    'exp-pong-binary-feedback',
    'exp-lunar-lander-binary-feedback',
]

# Source: https://stackoverflow.com/questions/49772151/download-a-folder-from-s3-using-boto3
def download_directory(bucketName, remote_dir, save_dir, exclude=None):
    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket(bucketName)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    if exclude is not None:
        exclude = re.compile(exclude)

    for obj in bucket.objects.filter(Prefix=remote_dir):
        if exclude and exclude.search(obj.key):
            continue
        obj_save_dir = os.path.join(save_dir, os.path.dirname(obj.key))
        if not os.path.exists(obj_save_dir):
            os.makedirs(obj_save_dir)
        # download to save_dir
        bucket.download_file(obj.key, os.path.join(save_dir, obj.key)) # save to same path

def download_aws_data():
    for project_id in PROJECT_IDS:
        print('Downloading data for project: {}'.format(project_id))
        download_directory(BUCKET_NAME, project_id, SAVE_DIR, exclude='\.html$')

if __name__ == '__main__':
    download_aws_data()