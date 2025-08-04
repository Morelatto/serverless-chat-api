#!/bin/bash
# Optimized Lambda layer builder using Docker for consistent builds

set -e

echo "Building Lambda layer for Python 3.11..."

# Clean previous builds
rm -rf layer lambda_layer.zip

# Create layer structure
mkdir -p layer/python

# Build dependencies in Lambda-compatible environment
docker run --rm \
  -v "$PWD/../../requirements.txt:/tmp/requirements.txt:ro" \
  -v "$PWD/layer:/tmp/layer" \
  public.ecr.aws/lambda/python:3.11 \
  sh -c "
    pip install -r /tmp/requirements.txt \
      -t /tmp/layer/python \
      --platform manylinux2014_x86_64 \
      --implementation cp \
      --python-version 3.11 \
      --only-binary=:all: \
      --upgrade \
    && find /tmp/layer -type f -name '*.pyc' -delete \
    && find /tmp/layer -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true \
    && find /tmp/layer -type d -name '*.dist-info' -exec rm -rf {} + 2>/dev/null || true \
    && find /tmp/layer -type d -name 'tests' -exec rm -rf {} + 2>/dev/null || true
  "

# Create the zip
cd layer
zip -r ../lambda_layer.zip . -q
cd ..

echo "Lambda layer created: $(du -h lambda_layer.zip | cut -f1)"

# Verify the layer
echo "Layer contents:"
unzip -l lambda_layer.zip | head -20