# Obsidian RAG

Retrieval-Augmented Generation for Obsidian using local LLMs. This plugin allows you to chat with your vault using local language models and efficient document retrieval.

## Features

- Local LLM support with Apple Silicon optimization
- Efficient document processing and chunking
- Support for multiple file formats (Markdown, PDF, Word)
- Real-time search and retrieval
- Automatic server management
- Neural Engine and Metal acceleration on Apple Silicon
- Configurable settings and caching

## Requirements

- Obsidian v1.0.0 or higher
- Python 3.8 or higher
- Node.js 16 or higher
- 8GB RAM minimum (16GB recommended)
- For Apple Silicon Macs:
  - macOS 12 or higher
  - Xcode Command Line Tools

## Installation

### Quick Install (macOS)

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/obsidian-rag.git
   cd obsidian-rag
   ```

2. Run the installation script:
   ```bash
   ./install.sh
   ```

3. Download a GGUF model (e.g., llama-2-7b-chat.Q4_K_M.gguf) and place it in `server/models/`

4. Enable the plugin in Obsidian:
   - Open Settings → Community plugins
   - Enable "Obsidian RAG"
   - Configure the plugin settings

### Manual Installation

1. Install Python dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r server/requirements.txt
   ```

2. Install Node.js dependencies:
   ```bash
   cd plugin
   npm install
   npm run build
   ```

3. Copy the plugin to Obsidian:
   ```bash
   cp -r plugin/dist/* ~/.obsidian/plugins/obsidian-rag/
   ```

4. Configure the server:
   ```bash
   cp server/config/config.example.json server/config/config.json
   ```

## Usage

1. Start the server:
   ```bash
   cd server
   source ../.venv/bin/activate
   python run.py
   ```

2. In Obsidian:
   - Open the RAG panel using the ribbon icon or command palette
   - Wait for the server to initialize
   - Start chatting with your vault!

## Configuration

### Server Settings

Edit `server/config/config.json`:
- Model settings (context size, temperature, etc.)
- Neural Engine and Metal options
- Processing options (chunk size, file types)
- Security settings (API key, allowed origins)

### Plugin Settings

In Obsidian Settings → Obsidian RAG:
- Server URL (default: http://localhost:8000)
- API key (if enabled)
- UI preferences
- Search settings

## Docker Support

1. Build and start:
   ```bash
   ./docker.sh build
   ./docker.sh start
   ```

2. Monitor logs:
   ```bash
   ./docker.sh logs
   ```

## Development

1. Set up development environment:
   ```bash
   ./dev-setup.sh
   ```

2. Start development servers:
   ```bash
   # Terminal 1 (Server)
   cd server
   source ../.venv/bin/activate
   python run.py --debug

   # Terminal 2 (Plugin)
   cd plugin
   npm run dev
   ```

3. Open the test vault:
   ```bash
   open testvaults/dev_vault
   ```

## Troubleshooting

1. Server won't start:
   - Check Python version: `python3 --version`
   - Verify model file exists in `server/models/`
   - Check port 8000 is available

2. Plugin not working:
   - Verify server is running
   - Check server URL in plugin settings
   - Look for errors in Obsidian developer console

3. Poor performance:
   - Verify Metal/Neural Engine support is enabled
   - Check system resources
   - Adjust chunk size and batch settings

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

[MIT License](LICENSE) 