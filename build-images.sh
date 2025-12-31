#!/bin/bash

# Build multi-architecture Docker images for the-pipeline project
# Usage: ./build-images.sh [--mac|--intel]
#   --mac    Build only ARM64 (Apple Silicon/Mac)
#   --intel  Build only AMD64 (Intel server)
#   (no flag) Build both architectures

set -e

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export BUILDKIT_STEP_LOG_MAX_SIZE=50000000
export BUILDKIT_STEP_LOG_MAX_SPEED=100000000

PROJECT_NAME="the-pipeline"
IMAGE_DIR="./docker-images"

# Parse command line arguments
BUILD_MAC=false
BUILD_INTEL=false

if [ "$1" == "--mac" ]; then
    BUILD_MAC=true
elif [ "$1" == "--intel" ]; then
    BUILD_INTEL=true
elif [ -z "$1" ]; then
    # No argument, build both
    BUILD_MAC=true
    BUILD_INTEL=true
else
    echo "Usage: $0 [--mac|--intel]"
    echo "  --mac    Build only ARM64 (Apple Silicon/Mac)"
    echo "  --intel  Build only AMD64 (Intel server)"
    echo "  (no flag) Build both architectures"
    exit 1
fi

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ "$BUILD_MAC" = true ] && [ "$BUILD_INTEL" = true ]; then
    echo -e "${BLUE}Starting multi-architecture build (ARM64 + AMD64)...${NC}"
elif [ "$BUILD_MAC" = true ]; then
    echo -e "${BLUE}Building for ARM64 (Mac) only...${NC}"
elif [ "$BUILD_INTEL" = true ]; then
    echo -e "${BLUE}Building for AMD64 (Intel) only...${NC}"
fi

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
if [ "$BUILD_MAC" = true ]; then
    echo -e "${GREEN}Building backend for ARM64 (Apple Silicon/Mac)...${NC}"
    docker buildx build \
        --platform linux/arm64 \
        -t ${PROJECT_NAME}_backend:arm64 \
        --load \
        ./backend

    echo -e "${GREEN}Saving ARM64 image...${NC}"
    docker save ${PROJECT_NAME}_backend:arm64 | gzip > "$IMAGE_DIR/${PROJECT_NAME}_backend_arm64.tar.gz"
fi

# Build backend for AMD64 (Intel)
if [ "$BUILD_INTEL" = true ]; then
    echo -e "${GREEN}Building backend for AMD64 (Intel)...${NC}"
    docker buildx build \
        --platform linux/amd64 \
        -t ${PROJECT_NAME}_backend:amd64 \
        --load \
        ./backend

    echo -e "${GREEN}Saving AMD64 image...${NC}"
    docker save ${PROJECT_NAME}_backend:amd64 | gzip > "$IMAGE_DIR/${PROJECT_NAME}_backend_amd64.tar.gz"

    # Pull and save other required images for AMD64 (for production server)
    echo -e "${GREEN}Pulling and saving postgres image for AMD64...${NC}"
    docker pull --platform linux/amd64 pgvector/pgvector:pg15
    docker save pgvector/pgvector:pg15 | gzip > "$IMAGE_DIR/pgvector_pg15_amd64.tar.gz"

    echo -e "${GREEN}Pulling and saving nginx image for AMD64...${NC}"
    docker pull --platform linux/amd64 nginx:alpine
    docker save nginx:alpine | gzip > "$IMAGE_DIR/nginx_alpine_amd64.tar.gz"
fi

# Display results
echo -e "${GREEN}Build complete!${NC}"
echo -e "${BLUE}Saved images in $IMAGE_DIR:${NC}"
ls -lh "$IMAGE_DIR"

echo -e "\n${GREEN}Image sizes:${NC}"
du -h "$IMAGE_DIR"/*.tar.gz
