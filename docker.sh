#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to print status messages
print_status() {
    echo -e "${GREEN}==>${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Function to show help
show_help() {
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  start       Start the server container"
    echo "  stop        Stop the server container"
    echo "  restart     Restart the server container"
    echo "  logs        Show container logs"
    echo "  build       Rebuild the container"
    echo "  clean       Remove all containers and volumes"
    echo "  status      Show container status"
    echo "  shell       Open a shell in the container"
    echo "  help        Show this help message"
}

# Check command argument
if [ -z "$1" ]; then
    show_help
    exit 1
fi

# Handle commands
case "$1" in
    start)
        print_status "Starting server container..."
        docker-compose up -d
        ;;
        
    stop)
        print_status "Stopping server container..."
        docker-compose down
        ;;
        
    restart)
        print_status "Restarting server container..."
        docker-compose restart
        ;;
        
    logs)
        print_status "Showing container logs..."
        docker-compose logs -f
        ;;
        
    build)
        print_status "Rebuilding container..."
        docker-compose build --no-cache
        ;;
        
    clean)
        print_status "Removing containers and volumes..."
        docker-compose down -v
        ;;
        
    status)
        print_status "Container status:"
        docker-compose ps
        ;;
        
    shell)
        print_status "Opening shell in container..."
        docker-compose exec server /bin/bash
        ;;
        
    help)
        show_help
        ;;
        
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 