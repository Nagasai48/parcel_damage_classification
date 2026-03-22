#!/usr/bin/env bash
# exit on error
set -o errexit
# Removed pip install from here as Railway does it automatically
# Download model from Google Drive
# Replace 'YOUR_GOOGLE_DRIVE_FILE_ID' below with the actual file ID from your shareable link!
python -c "
import os
import gdown

file_id = '1N9-cnWPOs2z0VGplxdJU1nuBQYoLXZHf'
dest_path = 'models/resnet34_model.h5'

if not os.path.exists('models'):
    os.makedirs('models')

print('Checking if model file exists and is valid...')
if not os.path.exists(dest_path) or os.path.getsize(dest_path) < 10000000:
    print('Downloading resnet34_model.h5 from Google Drive...')
    try:
        url = f'https://drive.google.com/uc?id={file_id}'
        gdown.download(url, dest_path, quiet=False)
    except Exception as e:
        print(f'Failed to download model: {e}')
else:
    print('Model already exists and seems valid.')
"

python manage.py collectstatic --no-input
python manage.py migrate
