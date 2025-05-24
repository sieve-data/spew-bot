# Contributing to Spew

Thank you for your interest in contributing to Spew! We welcome contributions from everyone, whether you're fixing a bug, adding a feature, improving documentation, or suggesting new ideas.

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** with Anaconda/Miniconda
- **Node.js 18+** and **Yarn**
- **Git**
- **Sieve Account** (for AI functions)

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/yourusername/spew-bot.git
   cd spew-bot
   ```

2. **Quick setup using Makefile**

   ```bash
   make setup-all
   ```

3. **Activate the conda environment**

   ```bash
   conda activate spew-env
   ```

4. **Configure environment variables**

   - Copy the environment template and fill in your API keys
   - See the [Backend Setup](README.md#backend-setup-server) section for required variables

5. **Deploy Sieve functions** (if working on AI features)

   ```bash
   make sieve-login
   make deploy-sieve
   ```

6. **Start development servers**
   ```bash
   make dev
   ```

## 📁 Project Structure

```
spew-bot/
├── client/              # Next.js frontend
├── server/              # Flask backend
│   ├── sieve_functions/ # AI processing functions
│   ├── twitter_bot/     # Twitter bot implementation
│   ├── routes/          # API routes
│   └── data/            # Data files and database
├── Makefile            # Development automation
└── README.md           # Project documentation
```

## 🛠️ Development Workflow

### Making Changes

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**

   - Follow the code style guidelines below
   - Add tests if applicable
   - Update documentation as needed

3. **Test your changes**

   ```bash
   # Test the bot
   make check-bot

   # Test the API
   make dev-server

   # Test the frontend
   make dev-client
   ```

4. **Commit your changes**

   ```bash
   git add .
   git commit -m "feat: add new celebrity persona support"
   ```

5. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

We follow conventional commits for consistent commit messages:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:

```
feat: add David Attenborough persona
fix: resolve Twitter API rate limiting
docs: update setup instructions
refactor: optimize video processing pipeline
```

## 📝 Code Style Guidelines

### Python (Backend)

- Follow **PEP 8** style guidelines
- Use **type hints** where applicable
- Use **docstrings** for functions and classes
- Keep functions focused and small
- Use meaningful variable names

```python
def generate_script(query: str, persona_name: str, style_prompt: str) -> str:
    """
    Generate educational script for a specific persona.

    Args:
        query: The educational topic to explain
        persona_name: Name of the celebrity persona
        style_prompt: Style guidelines for the persona

    Returns:
        Generated script text
    """
    # Implementation here
```

### TypeScript/React (Frontend)

- Use **TypeScript** for type safety
- Follow **React best practices**
- Use **functional components** with hooks
- Use **Tailwind CSS** for styling
- Keep components small and focused

```typescript
interface PersonaCardProps {
  persona: Persona;
  onSelect: (persona: Persona) => void;
}

export const PersonaCard: React.FC<PersonaCardProps> = ({
  persona,
  onSelect,
}) => {
  // Component implementation
};
```

### Sieve Functions

- Keep functions stateless and focused
- Use proper error handling
- Document environment variables clearly
- Include type hints and docstrings

## 🧪 Testing

### Running Tests

```bash
# Backend tests
cd server && python -m pytest

# Frontend tests
cd client && yarn test

# Bot status check
make check-bot
```

### Writing Tests

- Write unit tests for new functions
- Include integration tests for API endpoints
- Test error handling and edge cases
- Mock external API calls in tests

## 📋 Pull Request Guidelines

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No merge conflicts with main branch

### PR Description Template

```markdown
## Description

Brief description of the changes made.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing

- [ ] Tests pass
- [ ] Manual testing completed
- [ ] New tests added (if applicable)

## Screenshots (if applicable)

Add screenshots for UI changes.

## Additional Notes

Any additional context or considerations.
```

## 🐛 Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected vs actual behavior**
4. **Environment details** (OS, Python version, etc.)
5. **Error messages or logs**
6. **Screenshots** if applicable

### Feature Requests

For feature requests, please include:

1. **Problem description** - What problem does this solve?
2. **Proposed solution** - How should it work?
3. **Alternatives considered** - What other approaches did you think about?
4. **Additional context** - Any mockups, examples, or references

## 🤝 Community Guidelines

- **Be respectful** and inclusive
- **Help others** learn and grow
- **Provide constructive feedback**
- **Ask questions** if something is unclear
- **Share knowledge** and best practices

## 🔐 Security

If you discover a security vulnerability, please:

1. **Do not** open a public issue
2. **Email** the maintainers directly
3. **Provide** detailed information about the vulnerability
4. **Allow** reasonable time for a fix before disclosure

## 📚 Additional Resources

- [Sieve Documentation](https://docs.sieve.cloud)
- [Next.js Documentation](https://nextjs.org/docs)
- [Flask Documentation](https://flask.palletsprojects.com)
- [Twitter API Documentation](https://developer.twitter.com/en/docs)

## 📞 Getting Help

- **GitHub Issues** - For bugs and feature requests
- **GitHub Discussions** - For questions and general discussion
- **Documentation** - Check the README for setup instructions

---

Thank you for contributing to Spew! 🎭✨
