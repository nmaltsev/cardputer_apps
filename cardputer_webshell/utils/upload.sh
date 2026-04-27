#!/bin/bash

# Usage: ./upload.sh <file> [remote_path]

HOST="192.168.1.62"

FILE="$1"
REMOTE_PATH="$2"

if [ -z "$FILE" ]; then
    echo "Usage: $0 <file> [remote_path]"
    exit 1
fi

if [ ! -f "$FILE" ]; then
    echo "File not found: $FILE"
    exit 1
fi

# default remote path = same filename in root
if [ -z "$REMOTE_PATH" ]; then
    BASENAME=$(basename "$FILE")
    REMOTE_PATH="/$BASENAME"
fi

echo "Uploading $FILE -> $REMOTE_PATH"

curl -X POST "http://$HOST/upload" \
    -F "path=$REMOTE_PATH" \
    -F "file=@$FILE"

echo ""
echo "Done"
