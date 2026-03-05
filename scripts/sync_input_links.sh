#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/../credit-dataset-builder/datasets"
TARGET_DIR="$ROOT_DIR/data/input"

mkdir -p "$TARGET_DIR"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Source dataset directory not found: $SOURCE_DIR"
  exit 1
fi

for d in "$SOURCE_DIR"/*; do
  [[ -d "$d" ]] || continue
  name="$(basename "$d")"
  ln -sfn "$(realpath "$d")" "$TARGET_DIR/$name"
done

echo "Synced dataset links to: $TARGET_DIR"
ls -la "$TARGET_DIR"

