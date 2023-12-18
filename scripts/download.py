from azure.storage.blob import BlobServiceClient, BlobPrefix
from InquirerPy import inquirer
import tqdm
import os

def list_directories(container_client):
    blob_iter = container_client.walk_blobs(name_starts_with='', delimiter='/')
    directories = set()
    for blob in blob_iter:
        if isinstance(blob, BlobPrefix):
            directories.add(blob.name)
    return directories

def download_blobs(container_client, directory, download_path):
    for blob in container_client.walk_blobs(name_starts_with=directory):
        print(blob.name)
        if not isinstance(blob, BlobPrefix):  # Checking if the blob is not a directory
            local_file_path = os.path.join(download_path, blob.name)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            blob_client = container_client.get_blob_client(blob)
            with open(local_file_path, "wb") as download_file:
                d = blob_client.download_blob()
                p = tqdm.tqdm(total=d.size, unit='B', unit_scale=True, desc=blob.name, leave=True)
                for chunk in blob_client.download_blob().chunks():
                    download_file.write(chunk)
                    p.update(len(chunk))
                p.close()
        else:
            download_blobs(container_client, blob.name, download_path)

def download_models(config):
    blob_service_client = BlobServiceClient(account_url=f"https://{config['storage_account_name']}.blob.core.windows.net", credential=config['storage_account_key'])
    container_client = blob_service_client.get_container_client(config['storage_container_name'])

    directories = list_directories(container_client)
    selected_dirs = inquirer.checkbox(
        message="Select directories to download:",
        choices=list(directories),
    ).execute()

    for dir in selected_dirs:
        print(f"Downloading {dir}...")
        download_blobs(container_client, dir, config['local_download_path'])
        print(f"Downloaded {dir} to {config['model_dir']}")
