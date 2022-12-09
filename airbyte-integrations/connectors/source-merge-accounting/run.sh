#!/usr/bin/env bash

IMAGE_PREFIX=${IMAGE_PREFIX:-public.ecr.aws/i1b3x1k7/}

YAMLS=( "-f" "docker-compose.yaml" "-f" "docker-compose.${ENV}.yaml" )

build() {
  docker build -t source-merge-accounting:latest .
}

push() {
	aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
	docker tag source-merge-accounting:latest ${IMAGE_PREFIX}source-merge-accounting:${TAG}
	docker push ${IMAGE_PREFIX}source-merge-accounting:${TAG}
}

case $1 in
  build)
    build
    ;;
  push)
    push
    ;;
  *)
    echo "Usage: $0 {build|push}"
    ;;
esac
