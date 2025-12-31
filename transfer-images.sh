#!/bin/bash

# Transfer Docker images to remote server
# Usage: ./transfer-images.sh [remote_host] [remote_path]

set -e

# Default values
REMOTE_HOST="${1:-root@192.168.1.186}"
REMOTE_PATH="${2:-/tmp}"
IMAGE_DIR="./docker-images"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if images directory exists
if [ ! -d "$IMAGE_DIR" ]; then
    echo -e "${YELLOW}Error: $IMAGE_DIR directory not found!${NC}"
    echo "Please run ./build-images.sh first"
    exit 1
fi

# Check if there are any images to transfer
if [ -z "$(ls -A $IMAGE_DIR/*.tar.gz 2>/dev/null)" ]; then
    echo -e "${YELLOW}Error: No image files found in $IMAGE_DIR${NC}"
    echo "Please run ./build-images.sh first"
    exit 1
fi

echo -e "${BLUE}Transferring images to ${REMOTE_HOST}:${REMOTE_PATH}${NC}"
echo -e "${BLUE}Images to transfer:${NC}"
ls -lh "$IMAGE_DIR"/*.tar.gz

# Create remote directory if it doesn't exist
echo -e "${GREEN}Creating remote directory...${NC}"
ssh "$REMOTE_HOST" "mkdir -p $REMOTE_PATH/docker-images"

# Transfer AMD64 images (for Intel production server)
echo -e "${GREEN}Transferring AMD64 backend image...${NC}"
scp "$IMAGE_DIR/the-pipeline_backend_amd64.tar.gz" "$REMOTE_HOST:$REMOTE_PATH/docker-images/"

echo -e "${GREEN}Transferring postgres image...${NC}"
scp "$IMAGE_DIR/pgvector_pg15_amd64.tar.gz" "$REMOTE_HOST:$REMOTE_PATH/docker-images/"

echo -e "${GREEN}Transferring nginx image...${NC}"
scp "$IMAGE_DIR/nginx_alpine_amd64.tar.gz" "$REMOTE_HOST:$REMOTE_PATH/docker-images/"

# Transfer production docker-compose and related files
echo -e "${GREEN}Transferring production configuration files...${NC}"
ssh "$REMOTE_HOST" "mkdir -p $REMOTE_PATH/the-pipeline-deploy"
scp docker-compose.prod.yml "$REMOTE_HOST:$REMOTE_PATH/the-pipeline-deploy/"
scp -r frontend "$REMOTE_HOST:$REMOTE_PATH/the-pipeline-deploy/" 2>/dev/null || echo "Skipping frontend (not found)"
scp nginx.conf "$REMOTE_HOST:$REMOTE_PATH/the-pipeline-deploy/" 2>/dev/null || echo "Skipping nginx.conf (not found)"
scp -r db "$REMOTE_HOST:$REMOTE_PATH/the-pipeline-deploy/" 2>/dev/null || echo "Skipping db (not found)"
scp .env "$REMOTE_HOST:$REMOTE_PATH/the-pipeline-deploy/" 2>/dev/null || echo "Skipping .env (not found)"

# Create a load script on the remote server
echo -e "${GREEN}Creating load script on remote server...${NC}"
ssh "$REMOTE_HOST" "cat > $REMOTE_PATH/docker-images/load-images.sh << 'EOF'
#!/bin/bash
set -e

echo \"Loading Docker images...\"

echo \"Loading backend image...\"
docker load < the-pipeline_backend_amd64.tar.gz

echo \"Loading postgres image...\"
docker load < pgvector_pg15_amd64.tar.gz

echo \"Loading nginx image...\"
docker load < nginx_alpine_amd64.tar.gz

echo \"All images loaded successfully!\"
echo \"\"
echo \"Loaded images:\"
docker images | grep -E \"the-pipeline_backend|pgvector|nginx\"

echo \"\"
echo \"To use the backend image, update your docker-compose.yml:\"
echo \"  backend:\"
echo \"    image: the-pipeline_backend:amd64\"
EOF
chmod +x $REMOTE_PATH/docker-images/load-images.sh"

echo -e "${GREEN}Transfer complete!${NC}"
echo -e "${BLUE}Images transferred to: ${REMOTE_HOST}:${REMOTE_PATH}/docker-images/${NC}"
echo -e "${BLUE}Project files transferred to: ${REMOTE_HOST}:${REMOTE_PATH}/the-pipeline-deploy/${NC}"
echo -e "\n${YELLOW}Next steps on the remote server:${NC}"
echo -e "1. SSH to the server: ${GREEN}ssh $REMOTE_HOST${NC}"
echo -e "2. Load the Docker images:"
echo -e "   ${GREEN}cd $REMOTE_PATH/docker-images${NC}"
echo -e "   ${GREEN}./load-images.sh${NC}"
echo -e "3. Deploy the application:"
echo -e "   ${GREEN}cd $REMOTE_PATH/the-pipeline-deploy${NC}"
echo -e "   ${GREEN}docker-compose -f docker-compose.prod.yml up -d${NC}"
echo -e "4. Check the status:"
echo -e "   ${GREEN}docker-compose -f docker-compose.prod.yml ps${NC}"
echo -e "   ${GREEN}docker-compose -f docker-compose.prod.yml logs -f${NC}"
