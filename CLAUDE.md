# Project Context
@README.md
@docs/dependency-management.md
@services/CLAUDE.md
@DEPLOYMENT.md

# Documentation Guidelines

After writing new code, check if README.md needs updating:
1. New features or tools added
2. Architecture changes (new services, ports, dependencies)
3. API endpoint changes
4. Configuration or environment variable changes
5. Project structure changes

# Build Guidelines

When upgrading package to resolve conflict and dependecies alwasy go up in version.

When building docker images use parallelism
Use these vars to speed up buildkit
# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export BUILDKIT_STEP_LOG_MAX_SIZE=50000000
export BUILDKIT_STEP_LOG_MAX_SPEED=100000000



