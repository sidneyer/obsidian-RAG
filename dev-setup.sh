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
pip install -r server/requirements-dev.txt

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
cd plugin
npm install

# Set up Git hooks
print_status "Setting up Git hooks..."
if [ -d .git ]; then
    # Pre-commit hook for Python
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
set -e

# Format Python code
echo "Formatting Python code..."
source .venv/bin/activate
cd server
black .
isort .
flake8 .
mypy .

# Format TypeScript code
echo "Formatting TypeScript code..."
cd ../plugin
npm run lint
EOF
    chmod +x .git/hooks/pre-commit
    print_status "Created pre-commit hook"
fi

# Create test vault
print_status "Creating test vault..."
mkdir -p testvaults/dev_vault
mkdir -p testvaults/dev_vault/.obsidian/plugins

# Link plugin for development
print_status "Linking plugin for development..."
ln -sf "$PWD/plugin" testvaults/dev_vault/.obsidian/plugins/obsidian-rag

# Set up server configuration
print_status "Setting up server configuration..."
if [ ! -f server/config/config.json ]; then
    cp server/config/config.example.json server/config/config.json
    print_status "Created default server configuration"
fi

# Print success message
echo
echo -e "${GREEN}Development setup complete!${NC}"
echo
echo "Next steps:"
echo "1. Start the development servers:"
echo "   Terminal 1 (Server):"
echo "   cd server"
echo "   source ../.venv/bin/activate"
echo "   python run.py --debug"
echo
echo "   Terminal 2 (Plugin):"
echo "   cd plugin"
echo "   npm run dev"
echo
echo "2. Open the test vault in Obsidian:"
echo "   testvaults/dev_vault"
echo
echo "3. Enable the plugin in Obsidian:"
echo "   - Open Obsidian Settings"
echo "   - Go to Community Plugins"
echo "   - Enable 'Obsidian RAG'"
echo
echo "For more information, see CONTRIBUTING.md" 