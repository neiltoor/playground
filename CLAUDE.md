When upgrading package to resolve conflict and dependecies alwasy go up in version. 

when building docker images use parallelism
Use these vars to speed up buildkit
# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export BUILDKIT_STEP_LOG_MAX_SIZE=50000000
export BUILDKIT_STEP_LOG_MAX_SPEED=100000000



