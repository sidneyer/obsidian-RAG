# Contributing to Obsidian RAG

Thank you for your interest in contributing to Obsidian RAG! This document provides guidelines and instructions for contributing to the project.

## Project Status

The project is currently in active development with several key components needing attention:

### Server Component
- [ ] Complete LLM manager implementation
- [ ] Add support for more file formats
- [ ] Improve vault indexing system
- [ ] Add caching system for LLM responses
- [ ] Implement proper error handling

### Plugin Component
- [ ] Complete file modification handling
- [ ] Add more UI components
- [ ] Improve error handling
- [ ] Add progress indicators
- [ ] Implement settings validation

## Development Setup

### Prerequisites

1. Development tools:
   - Python 3.8+
   - Node.js 16+
   - Git
   - VSCode (recommended)
   - Obsidian for testing

2. Python packages:
   ```bash
   pip install -r server/requirements.txt
   pip install -r server/requirements-dev.txt  # Development dependencies
   ```

3. Node packages:
   ```bash
   cd plugin
   npm install
   ```

### Development Environment

1. Create a test vault:
   ```bash
   cd testvaults
   mkdir dev_vault
   ```

2. Link plugin for development:
   ```bash
   cd /path/to/obsidian/vault/.obsidian/plugins
   ln -s /path/to/repo/plugin obsidian-rag
   ```

3. Start development servers:
   ```bash
   # Terminal 1 - Server
   cd server
   python run.py --debug

   # Terminal 2 - Plugin
   cd plugin
   npm run dev
   ```

## Development Workflow

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Make your changes:
   - Follow the code style
   - Add tests
   - Update documentation

4. Run tests:
   ```bash
   # Server tests
   cd server
   pytest
   
   # Plugin tests
   cd plugin
   npm test
   ```

5. Format code:
   ```bash
   # Server
   cd server
   black .
   isort .
   
   # Plugin
   cd plugin
   npm run lint
   ```

6. Submit a pull request

## Code Style

### Python (Server)
- Follow PEP 8
- Use type hints
- Document functions and classes
- Maximum line length: 88 characters (Black default)

### TypeScript (Plugin)
- Follow the Obsidian plugin style guide
- Use TypeScript features appropriately
- Document public APIs
- Maximum line length: 100 characters

## Testing

### Server Tests
- Write unit tests for new features
- Use pytest fixtures
- Mock external services
- Test edge cases

### Plugin Tests
- Write unit tests for utilities
- Test UI components
- Mock Obsidian API calls
- Test error handling

## Documentation

- Update README.md for user-facing changes
- Update CONTRIBUTING.md for development changes
- Document new features in docs/
- Include code examples where appropriate

## Pull Request Process

1. Update documentation
2. Add/update tests
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Request review

## Getting Help

- Open an issue for bugs
- Use discussions for questions
- Join our community chat

## Code of Conduct

Please follow our code of conduct:

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain professionalism

## License

By contributing, you agree that your contributions will be licensed under the MIT License. 