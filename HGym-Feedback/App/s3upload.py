import gzip
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

class Uploader:
    def __init__(self, projectId, userId, file, path, bucket, compress=False):
        if compress:
            with open(path, 'rb') as inf:
                with gzip.open(path + '.gz', 'wb') as outf:
                    outf.writelines(inf)
            file += '.gz'
            path += '.gz'
        self.s3 = boto3.resource('s3')
        self.bucket = bucket
        self.key = f'{projectId}/Trials/{userId}/'
        bucket = self.bucket
        key = self.key + file
        self.s3.meta.client.upload_file(path, bucket, key)