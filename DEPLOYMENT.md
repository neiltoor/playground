# Deployment Guide

This project uses Docker for containerization with multi-architecture support.

## Architecture
- **Development (Mac)**: ARM64 images, uses `docker-compose.yml`
- **Production (Intel Server)**: AMD64 images, uses `docker-compose.prod.yml`

## Files
- `docker-compose.yml` - Development setup (uses `build:` for live development)
- `docker-compose.prod.yml` - Production setup (uses pre-built `image:`)
- `build-images.sh` - Builds multi-arch images and saves them
- `transfer-images.sh` - Transfers images and config to production server

## Deployment Workflow

### Step 1: Build Images on Mac
```bash
./build-images.sh
```

This creates:
- ARM64 images for your Mac
- AMD64 images for Intel production server
- Saves all images to `./docker-images/` as compressed tar.gz files

### Step 2: Transfer to Production Server
```bash
./transfer-images.sh
```

This:
- Transfers AMD64 images to `root@192.168.1.186:/tmp/docker-images/`
- Transfers project files to `root@192.168.1.186:/tmp/the-pipeline-deploy/`
- Creates helper scripts on the remote server

### Step 3: Deploy on Production Server

SSH into the server:
```bash
ssh root@192.168.1.186
```

Load the Docker images:
```bash
cd /tmp/docker-images
./load-images.sh
```

Deploy the application:
```bash
cd /tmp/the-pipeline-deploy
docker-compose -f docker-compose.prod.yml up -d
```

Check status:
```bash
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

## Environment Variables

Make sure to set your `.env` file with:
```
ANTHROPIC_API_KEY=your_key_here
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpassword
POSTGRES_DB=ragdb
```

## Local Development

For local development on Mac:
```bash
docker-compose up
```

This uses the regular `docker-compose.yml` which builds images locally and mounts volumes for hot-reloading.

## Updating Production

When you make changes:
1. Test locally with `docker-compose up`
2. Rebuild images: `./build-images.sh`
3. Transfer to production: `./transfer-images.sh`
4. On production server, reload:
   ```bash
   cd /tmp/docker-images && ./load-images.sh
   cd /tmp/the-pipeline-deploy
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Ports
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- Postgres: 5432 (internal only)
