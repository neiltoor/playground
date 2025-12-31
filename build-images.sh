#!/bin/bash

# Build multi-architecture Docker images for the-pipeline project
# Builds for both ARM64 (Mac) and AMD64 (Intel server)

set -e

PROJECT_NAME="the-pipeline"
IMAGE_DIR="./docker-images"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting multi-architecture build...${NC}"

# Create directory for saved images
mkdir -p "$IMAGE_DIR"

# Create buildx builder if it doesn't exist
if ! docker buildx inspect multiarch-builder > /dev/null 2>&1; then
    echo -e "${BLUE}Creating buildx builder...${NC}"
    docker buildx create --name multiarch-builder --use
else
    echo -e "${BLUE}Using existing buildx builder...${NC}"
    docker buildx use multiarch-builder
fi

# Build backend for ARM64 (Mac)
echo -e "${GREEN}Building backend for ARM64 (Apple Silicon/Mac)...${NC}"
docker buildx build \
    --platform linux/arm64 \
    -t ${PROJECT_NAME}_backend:arm64 \
    --load \
    ./backend

# Build backend for AMD64 (Intel)
echo -e "${GREEN}Building backend for AMD64 (Intel)...${NC}"
docker buildx build \
    --platform linux/amd64 \
    -t ${PROJECT_NAME}_backend:amd64 \
    --load \
    ./backend

# Save images to tar files
echo -e "${GREEN}Saving ARM64 image...${NC}"
docker save ${PROJECT_NAME}_backend:arm64 | gzip > "$IMAGE_DIR/${PROJECT_NAME}_backend_arm64.tar.gz"

echo -e "${GREEN}Saving AMD64 image...${NC}"
docker save ${PROJECT_NAME}_backend:amd64 | gzip > "$IMAGE_DIR/${PROJECT_NAME}_backend_amd64.tar.gz"

# Pull and save other required images for AMD64 (for production server)
echo -e "${GREEN}Pulling and saving postgres image for AMD64...${NC}"
docker pull --platform linux/amd64 pgvector/pgvector:pg15
docker save pgvector/pgvector:pg15 | gzip > "$IMAGE_DIR/pgvector_pg15_amd64.tar.gz"

echo -e "${GREEN}Pulling and saving nginx image for AMD64...${NC}"
docker pull --platform linux/amd64 nginx:alpine
docker save nginx:alpine | gzip > "$IMAGE_DIR/nginx_alpine_amd64.tar.gz"

# Display results
echo -e "${GREEN}Build complete!${NC}"
echo -e "${BLUE}Saved images in $IMAGE_DIR:${NC}"
ls -lh "$IMAGE_DIR"

echo -e "\n${GREEN}Image sizes:${NC}"
du -h "$IMAGE_DIR"/*.tar.gz
