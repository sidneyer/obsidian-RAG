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

# Check Python version
print_status "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$python_version < 3.8" | bc -l) )); then
    print_error "Python 3.8 or higher is required. Found version $python_version"
    exit 1
fi

# Check Node.js version
print_status "Checking Node.js version..."
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi

node_version=$(node -v | cut -d'v' -f2)
if (( $(echo "$node_version < 16.0" | bc -l) )); then
    print_error "Node.js 16 or higher is required. Found version $node_version"
    exit 1
fi

# Create Python virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r server/requirements.txt

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
cd plugin
npm install
npm run build
cd ..

# Download LLM model
print_status "Setting up LLM model..."
mkdir -p server/models
if [ ! -f server/models/llama-2-7b-chat.Q4_K_M.gguf ]; then
    print_warning "Please download a GGUF model (e.g. llama-2-7b-chat.Q4_K_M.gguf)"
    print_warning "and place it in the server/models directory."
fi

# Create server configuration
print_status "Setting up server configuration..."
if [ ! -f server/config/config.json ]; then
    cp server/config/config.example.json server/config/config.json
    print_status "Created default server configuration"
fi

# Set up Obsidian plugin
print_status "Setting up Obsidian plugin..."
plugin_dir="$HOME/.obsidian/plugins/obsidian-rag"
if [ ! -d "$plugin_dir" ]; then
    mkdir -p "$plugin_dir"
fi

cp -r plugin/dist/* "$plugin_dir/"
print_status "Installed plugin to $plugin_dir"

# Print success message
echo
echo -e "${GREEN}Installation complete!${NC}"
echo
echo "Next steps:"
echo "1. Start the server:"
echo "   cd server"
echo "   source ../.venv/bin/activate"
echo "   python run.py"
echo
echo "2. Enable the plugin in Obsidian:"
echo "   - Open Obsidian Settings"
echo "   - Go to Community Plugins"
echo "   - Enable 'Obsidian RAG'"
echo
echo "3. Configure the plugin:"
echo "   - Set the server URL (default: http://localhost:8000)"
echo "   - Configure other settings as needed"
echo
echo "For more information, see the README.md file." 