from flask import Flask, request, jsonify
import os
import zipfile
from tqdm import tqdm
import glob
import boto3
from botocore.exceptions import ClientError
import subprocess
import pyodbc

conn_str = 'DRIVER={SQL Server};SERVER=LAPTOP-85732U6K;DATABASE=distributed;UID=RAZER;PWD=shail_123'

app = Flask(__name__)
def create_connection():
    try:
        # Replace 'server', 'database', 'username', and 'password' with your SQL Server credentials
        conn = pyodbc.connect('DRIVER={SQL Server};SERVER=LAPTOP-85732U6K;DATABASE=distributed;UID=RAZER;PWD=shail_123')
        return conn
    except Exception as e:
        print("Error connecting to SQL Server:", e)
        return None
def create_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS FileMetadata (
                id INT PRIMARY KEY IDENTITY,
                filename NVARCHAR(255),
                upload_time DATETIME,
                virus_scan_result BIT,
                user_details NVARCHAR(255)
            )
        ''')
        conn.commit()
    except Exception as e:
        print("Error creating table:", e)
def insert_file_upload_details(conn, filename, upload_time, virus_scan_result, user_details):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO FileMetadata (filename, upload_time, virus_scan_result, user_details)
            VALUES (?, ?, ?, ?)
        ''', (filename, upload_time, virus_scan_result, user_details))
        conn.commit()
        return True
    except Exception as e:
        print("Error inserting file upload details:", e)
        return False
class AWSUploader(object):
    def __init__(self, dir, zip):
        self.s3_client = None
        self.dir = dir
        self.zip = zip
        self.bucket_name = None

    def check_prereqs(self):
        # Check for AWS credentials and bucket name
        self.aws_access_key_id = "AKIAYAHFYGI7M6SYIVVL"
        self.aws_secret_access_key = "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"
        self.bucket_name = "mynewbucket.125"

        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.bucket_name]):
            return False
        else:
            self.s3_client = boto3.client('s3', aws_access_key_id=self.aws_access_key_id,
                                          aws_secret_access_key=self.aws_secret_access_key)
            return True

    def zipdir(self, path, ziph):
        # Function to zip directory
        for root, dirs, files in os.walk(path):
            for file in files:
                ziph.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(path, '..')))

    def upload(self):
        # Upload files to S3 bucket
        files_to_upload = []

        if self.zip == 'none':
            files_to_upload = list(glob.iglob(os.path.join(self.dir, '**', '*.*')))
            files_to_upload += list(glob.iglob(os.path.join(self.dir, '*.*')))

        elif self.zip == 'root':
            zipfile_name = self.dir + '.zip'
            zipf = zipfile.ZipFile(zipfile_name, 'w', zipfile.ZIP_DEFLATED)
            self.zipdir(self.dir, zipf)
            zipf.close()
            files_to_upload = [zipfile_name]

        elif self.zip == 'child':
            folders = glob.glob(os.path.join(self.dir, '*'))
            files_to_upload = []
            for folder in tqdm(folders):
                zipfile_name = os.path.dirname(folder) + '-' + os.path.basename(folder) + '.zip'
                zipf = zipfile.ZipFile(zipfile_name, 'w', zipfile.ZIP_DEFLATED)
                self.zipdir(self.dir, zipf)
                zipf.close()
                files_to_upload.append(zipfile_name)

        for file in tqdm(files_to_upload):
            try:
                self.s3_client.upload_file(file, self.bucket_name, os.path.basename(os.path.dirname(file)) + '/' + os.path.basename(file))
            except ClientError as ex:
                return False

        return True
def scan_file(file_path):
    try:
        result = subprocess.run(['clamscan', '--no-summary', file_path], capture_output=True)
        output = result.stdout.decode()
        if "Infected files: 0" in output:
            return True  # File is clean
        else:
            return False  # File is infected
    except Exception as e:
        print("Error scanning file:", e)
        return False


import requests

VIRUSTOTAL_API_KEY = 'da685dd89e6ce4af0c488d6930fc6b75f7c1b44cb1f511a0fb02fb5deaf6728e'


def scan_file_virustotal(file_path):
    url = 'https://www.virustotal.com/vtapi/v2/file/scan'
    params = {'apikey': VIRUSTOTAL_API_KEY}
    files = {'file': open(file_path, 'rb')}

    response = requests.post(url, files=files, params=params)
    if response.status_code == 200:
        scan_id = response.json().get('scan_id')
        return scan_id
    else:
        print('Error scanning file:', response.text)
        return None


@app.route('/upload', methods=['POST'])
def upload_files():
    # Handle file uploads
    dir = request.form.get('dir')
    zip = request.form.get('zip')

    if not os.path.exists(dir):
        return jsonify({'error': 'Path does not exist'}), 400

    # Scan the uploaded files for viruses using VirusTotal API
    try:
        for file_path in os.listdir(dir):
            scan_id = scan_file_virustotal(os.path.join(dir, file_path))
            if scan_id is None:
                return jsonify({'error': 'Error scanning file for viruses'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    aws_uploader = AWSUploader(dir, zip)

    if not aws_uploader.check_prereqs():
        return jsonify({'error': 'Pre-requisites not met'}), 400

    if not aws_uploader.upload():
        return jsonify({'error': 'Error occurred during upload'}), 500

    return jsonify({'message': 'Upload successful'})


def insert_metadata(filename, upload_time, virus_scan_result, user_details):
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO FileMetadata (filename, upload_time, virus_scan_result, user_details) VALUES (?, ?, ?, ?)",
                       (filename, upload_time, virus_scan_result, user_details))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print("Error inserting metadata:", e)
        return False

if __name__ == '__main__':
    app.run(debug=True)
