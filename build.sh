#!/usr/bin/env bash
# exit on error
set -o errexit

# Removed pip install from here as Railway does it automatically
# Download model from Google Drive
mkdir -p models
export FILE_ID="1N9-cnWPOs2z0VGplxdJU1nuBQYoLXZHf"
export DEST_PATH="models/resnet34_model.h5"

echo "Checking if model file exists and is valid..."

python -c "
import os, sys
dest = os.environ['DEST_PATH']
if os.path.exists(dest) and os.path.getsize(dest) > 10000000:
    print('Model already exists and seems valid.')
    sys.exit(0)
else:
    print('Model file missing or incomplete. Starting download...')
    sys.exit(1)
" || gdown --id "$FILE_ID" -O "$DEST_PATH"

python manage.py collectstatic --no-input
python manage.py migrate
