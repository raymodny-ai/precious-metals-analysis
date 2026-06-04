# Contributing to Precious Metals Analysis System

Thank you for your interest in contributing! 🙏

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Install dev dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov black flake8
   ```

## Code Style

- Use **Black** for formatting: `black src/`
- Use **Flake8** for linting: `flake8 src/`
- Follow PEP 8 guidelines
- Add type hints to all functions

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Add tests for new functionality
4. Run tests: `pytest`
5. Update documentation if needed
6. Submit a pull request

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src

# Specific module
pytest tests/test_integration.py -v
```

## Commit Messages

Use conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Adding tests

## Questions?

Open an issue for discussion.
