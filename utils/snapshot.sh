#!/usr/bin/env bash

# Usage: ./snapshot.sh /path/to/python/project
# source utils/snapshot.sh ./cardputer_webshell/webshell

#set -euo pipefail

# Check argument
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <project_path>"
  exit 1
fi

PROJECT_PATH="$1"

if [ ! -d "$PROJECT_PATH" ]; then
  echo "Error: '$PROJECT_PATH' is not a directory"
  exit 1
fi

OUTPUT_FILE="snapshot.md"

# Clear output file
> "$OUTPUT_FILE"

# Find all .py files excluding unwanted directories
find "$PROJECT_PATH" \
  -type d \( -name "__pycache__" -o -name ".git" -o -name ".venv" \) -prune -o \
  -type f -name "*.py" -print | while read -r file; do

  # Get relative path
  rel_path="${file#$PROJECT_PATH/}"

  echo "$rel_path:" >> "$OUTPUT_FILE"
  echo '```python' >> "$OUTPUT_FILE"
  cat "$file" >> "$OUTPUT_FILE"
  echo '' >> "$OUTPUT_FILE"
  echo '```' >> "$OUTPUT_FILE"
  echo '' >> "$OUTPUT_FILE"

done

echo "Snapshot created in $OUTPUT_FILE"