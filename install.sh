#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print messages
print_message() {
    echo -e "${GREEN}==>${NC} $1"
}

print_error() {
    echo -e "${RED}Error:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}Warning:${NC} $1"
}

# Check system requirements
check_requirements() {
    print_message "Checking system requirements..."
    
    # Check Python version
    if ! command -v python3 >/dev/null 2>&1; then
        print_error "Python 3 is required but not installed."
        exit 1
    fi
    
    # Check Node.js version
    if ! command -v node >/dev/null 2>&1; then
        print_error "Node.js is required but not installed."
        exit 1
    fi
    
    # Check if running on macOS
    if [[ "$(uname)" != "Darwin" ]]; then
        print_warning "This script is optimized for macOS. Some features may not work on other platforms."
    fi
}

# Setup Python environment
setup_python() {
    print_message "Setting up Python environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install Python dependencies
    pip install -r server/requirements.txt
}

# Setup Node.js environment and build plugin
setup_node() {
    print_message "Setting up Node.js environment..."
    
    # Install Node.js dependencies
    cd plugin
    npm install
    
    # Build plugin
    npm run build
    cd ..
}

# Function to find Obsidian vaults in iCloud
find_obsidian_vaults() {
    local icloud_obsidian_path="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"
    if [ ! -d "$icloud_obsidian_path" ]; then
        print_error "iCloud Obsidian directory not found at: $icloud_obsidian_path"
        return 1
    fi
    
    # List all directories (vaults) in the iCloud Obsidian folder
    local vaults=()
    while IFS= read -r vault; do
        if [ -d "$vault/.obsidian" ]; then
            vaults+=("$(basename "$vault")")
        fi
    done < <(find "$icloud_obsidian_path" -maxdepth 1 -type d ! -name ".*")
    
    if [ ${#vaults[@]} -eq 0 ]; then
        print_error "No Obsidian vaults found in iCloud"
        return 1
    fi
    
    echo "${vaults[@]}"
}

# Install plugin to Obsidian vault
install_plugin() {
    print_message "Installing plugin to Obsidian..."
    
    # Find available vaults
    local vaults=($(find_obsidian_vaults))
    if [ $? -ne 0 ]; then
        print_error "Failed to find Obsidian vaults"
        return 1
    fi
    
    # Print available vaults
    echo "Available vaults:"
    for i in "${!vaults[@]}"; do
        echo "$((i+1)). ${vaults[$i]}"
    done
    
    # Ask user to select vault
    read -p "Select vault number (1-${#vaults[@]}): " vault_num
    if ! [[ "$vault_num" =~ ^[0-9]+$ ]] || [ "$vault_num" -lt 1 ] || [ "$vault_num" -gt "${#vaults[@]}" ]; then
        print_error "Invalid selection"
        return 1
    fi
    
    local selected_vault="${vaults[$((vault_num-1))]}"
    local plugin_dir="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/$selected_vault/.obsidian/plugins/obsidian-rag"
    
    # Create plugin directory
    mkdir -p "$plugin_dir"
    
    # Copy plugin files
    cp -r plugin/dist/* "$plugin_dir/"
    
    print_message "Plugin installed successfully to vault: $selected_vault"
    print_message "Please restart Obsidian and enable the plugin in Settings -> Community Plugins"
}

# Setup server configuration
setup_server() {
    print_message "Setting up server configuration..."
    
    # Copy example config if config doesn't exist
    if [ ! -f "server/config/config.json" ]; then
        cp server/config/config.example.json server/config/config.json
    fi
    
    # Create necessary directories
    mkdir -p server/models server/data embeddings_cache
}

# Main installation process
main() {
    print_message "Starting installation..."
    
    check_requirements
    setup_python
    setup_node
    setup_server
    install_plugin
    
    print_message "Installation completed successfully!"
    print_message "Next steps:"
    echo "1. Download a GGUF model and place it in server/models/"
    echo "2. Start the server: cd server && python run.py"
    echo "3. Enable the plugin in Obsidian's Community Plugins settings"
}

# Run main installation
main 