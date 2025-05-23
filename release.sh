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

# Check if version is provided
if [ -z "$1" ]; then
    print_error "Please provide a version number (e.g. 1.0.0)"
    exit 1
fi

VERSION=$1

# Validate version format
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Invalid version format. Please use semantic versioning (e.g. 1.0.0)"
    exit 1
fi

# Update version in package.json
print_status "Updating version in package.json..."
cd plugin
npm version $VERSION --no-git-tag-version
cd ..

# Update version in manifest.json
print_status "Updating version in manifest.json..."
jq ".version = \"$VERSION\"" plugin/manifest.json > plugin/manifest.json.tmp
mv plugin/manifest.json.tmp plugin/manifest.json

# Clean and build plugin
print_status "Building plugin..."
cd plugin
npm run clean
npm install
npm run build
cd ..

# Create release directory
print_status "Creating release package..."
mkdir -p releases
RELEASE_DIR="releases/obsidian-rag-$VERSION"
mkdir -p "$RELEASE_DIR"

# Copy files to release directory
cp -r plugin/dist/* "$RELEASE_DIR/"
cp README.md "$RELEASE_DIR/"
cp LICENSE "$RELEASE_DIR/"

# Create release notes
print_status "Creating release notes..."
cat > "$RELEASE_DIR/release-notes.md" << EOF
# Obsidian RAG v$VERSION

## Changes in this version

[Please add release notes here]

## Installation

1. Download and extract \`obsidian-rag-$VERSION.zip\`
2. Copy the extracted folder to your vault's plugins directory:
   \`<vault>/.obsidian/plugins/\`
3. Enable the plugin in Obsidian's settings

## Server Setup

1. Follow the server setup instructions in README.md
2. Configure the plugin with your server URL

## Support

If you encounter any issues, please report them on GitHub:
https://github.com/yourusername/obsidian-rag/issues
EOF

# Create zip archive
print_status "Creating zip archive..."
cd releases
zip -r "obsidian-rag-$VERSION.zip" "obsidian-rag-$VERSION"
cd ..

# Create git tag
print_status "Creating git tag..."
git tag -a "v$VERSION" -m "Release v$VERSION"

# Print success message
echo
echo -e "${GREEN}Release v$VERSION created successfully!${NC}"
echo
echo "Next steps:"
echo "1. Review the release notes:"
echo "   $RELEASE_DIR/release-notes.md"
echo
echo "2. Push the release tag:"
echo "   git push origin v$VERSION"
echo
echo "3. Create a GitHub release:"
echo "   - Go to GitHub releases"
echo "   - Upload obsidian-rag-$VERSION.zip"
echo "   - Add the release notes"
echo
echo "4. Update the documentation if needed" 