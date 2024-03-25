from __future__ import print_function
import os
import zipfile
from tqdm import tqdm
import glob
import boto3
from botocore.exceptions import ClientError
import argparse

class AWSUploader(object):
    def __init__(self, dir, zip):
        self.s3_client = None
        self.dir = dir
        self.zip = zip
        self.bucket_name = None

    def check_prereqs(self):
        if not os.path.exists('.env'):
            print('Please create a .env file and populate AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and bucket_name fields.')
            return False
        self.aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.bucket_name = os.environ.get("BUCKET_NAME")

        if self.aws_access_key_id is None or self.aws_secret_access_key is None or self.bucket_name is None:
            print('Please create a .env file and populate AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and bucket_name values.')
            return False

        self.s3_client = boto3.client('s3', aws_access_key_id=self.aws_access_key_id,
                                      aws_secret_access_key=self.aws_secret_access_key)
        if self.s3_client is None:
            print('Error creating S3 client. Please check AWS credentials stored in .env file')
            return False

        return True

    def zipdir(self, path, ziph):
        for root, dirs, files in os.walk(path):
            for file in files:
                ziph.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(path, '..')))

    def upload(self):
        print('Uploading local folder: {} to S3 bucket {}'.format(self.dir, self.bucket_name))
        files_to_upload = []

        if self.zip == 'none':
            files_to_upload = list(glob.iglob(os.path.join(self.dir, '**', '*.*')))
            files_to_upload += list(glob.iglob(os.path.join(self.dir, '*.*')))

        elif self.zip == 'root':
            print('Compressing directory: {}'.format(self.dir))
            zipfile_name = self.dir + '.zip'
            zipf = zipfile.ZipFile(zipfile_name, 'w', zipfile.ZIP_DEFLATED)
            self.zipdir(self.dir, zipf)
            zipf.close()
            files_to_upload = [zipfile_name]

        elif self.zip == 'child':
            folders = glob.glob(os.path.join(self.dir, '*'))
            files_to_upload = []
            print('Compressing individual directories:')
            print('\t\n'.join(folders))
            for folder in tqdm(folders):
                zipfile_name = os.path.dirname(folder) + '-' + os.path.basename(folder) + '.zip'
                zipf = zipfile.ZipFile(zipfile_name, 'w', zipfile.ZIP_DEFLATED)
                self.zipdir(self.dir, zipf)
                zipf.close()
                files_to_upload.append(zipfile_name)

        print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')
        print('Uploading files to bucket: {}'.format(self.bucket_name))
        print('\t\n'.join(files_to_upload))

        for file in tqdm(files_to_upload):
            try:
                self.s3_client.upload_file(file, self.bucket_name, os.path.basename(os.path.dirname(file)) + '/' + os.path.basename(file))
            except ClientError as ex:
                print('\n... Error: {}'.format(ex))

        print('Upload complete.')
        print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ')

def main():
    print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
    parser = argparse.ArgumentParser(description='Upload folders to AWS S3')
    parser.add_argument('-d', '--dir', help='Local folder to be uploaded.', type=str, action='store', required=True)
    parser.add_argument('-z', '--zip', help='Zip folders (root | child | none)', type=str, action='store',
                        default='none')

    args = parser.parse_args()
    dir = args.dir
    zip = args.zip
    if not os.path.exists(dir):
        print('Error: Path {} does not exist'.format(dir))
        return -1

    # Create the AWS S3 Uploader Object
    aws_uploader = AWSUploader(dir, zip)

    # Check for pre-requisites.
    if aws_uploader.check_prereqs() is False:
        print('Pre-requisites not met. Exiting.')
        print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
        return -1

    # Upload folders
    if aws_uploader.upload() is False:
        print('Error occurred during upload. Exiting.')
        print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
        return -1

    # Done.
    print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')


if __name__ == '__main__':
    main()
