#!/bin/bash

# K12 Research Agent: Glass Box Launch script
# This script builds and starts the containerized stack.

# Terminal colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${CYAN}🚀 Initializing K12 Research Agent: Glass Box Edition...${NC}"

# Check for Docker
if ! [ -x "$(command -v docker-compose)" ]; then
  echo 'Error: docker-compose is not installed.' >&2
  exit 1
fi

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${CYAN}⚠️  Warning: .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${GREEN}Please update the .env file with your API keys before proceeding.${NC}"
    exit 1
fi

echo -e "${CYAN}📦 Building containers...${NC}"
docker-compose build

echo -e "${CYAN}🛰️  Launching the Glass Box stack...${NC}"
docker-compose up -d

echo -e "\n${GREEN}✅ Launch Complete!${NC}"
echo -e "--------------------------------------------------"
echo -e "Frontend UI:  http://localhost:5173"
echo -e "Backend API:   http://localhost:8000"
echo -e "--------------------------------------------------"
echo -e "${CYAN}Use 'docker-compose logs -f' to view real-time research activity.${NC}"
echo -e "${CYAN}Use 'docker-compose down' to stop the system.${NC}"
