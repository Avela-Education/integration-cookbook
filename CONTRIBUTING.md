# Contributing to Integration Cookbook

Thank you for contributing to the Avela Integration Cookbook. This page covers the standards for examples and documentation.

## 🎯 Ways to Contribute

- **🐛 Report bugs** - Found a problem with an example? Tell us
- **💡 Request examples** - Need an integration pattern? Suggest it
- **📝 Improve documentation** - Better explanations help everyone
- **🔧 Submit new examples** - Share your integration solutions
- **✅ Review pull requests** - Help maintain quality

## 📋 Before You Start

1. **Check existing examples** - Make sure your contribution doesn't duplicate existing work
2. **Read the guidelines** - Follow our standards below
3. **Test your code** - Ensure examples work as documented
4. **Consider security** - Never include credentials or sensitive data

## 🎨 Example Standards

### Directory Structure

Each example should follow this structure:

```
api/{resource}-{action}-{language}/
├── README.md                  # Example documentation
├── example_script.py          # Main code file
├── requirements.txt           # Dependencies (Python)
├── package.json               # Dependencies (Node.js)
└── config.example.json        # Optional, non-secret settings only
```

### Credentials

New recipes must get credentials from the shared client rather than reading a config file themselves:

```python
from avela_client import create_client

client = create_client()
```

`create_client()` checks environment variables, then the OS keychain. To pass credentials in code, construct `AvelaClient(client_id=..., client_secret=...)` directly. Call it and your recipe works with every storage option a user might have picked, and it supports profiles.

If your recipe takes command line arguments, add a `--profile` option and pass the value straight through, so someone with several Avela clients can pick one per run.

Print `client.credential_source` in your startup banner, the way the existing recipes do. It names the source without revealing anything, so it is safe to put in your README's expected output.


```
AVELA_CLIENT_ID=your_client_id
AVELA_CLIENT_SECRET=your_client_secret
AVELA_ENVIRONMENT=prod
```

Ship a `config.example.json` only if your recipe has non-secret settings worth templating, such as an output directory or a list of form template keys. It must never contain `client_id` or `client_secret`. Credentials come from `create_client()`, so do not write new code that opens `config.json` directly. Full credential documentation: [`shared/python/README.md`](shared/python/README.md).

### Code Style

#### Python

We use [ruff](https://docs.astral.sh/ruff/) to lint and format. Your code must pass both checks before you open a PR:

```bash
# Install uv (if not already installed)
# See: https://docs.astral.sh/uv/getting-started/installation/

# Install dev dependencies
uv sync --group dev

# Run linter
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

**Style requirements:**
- Line length: 90 characters maximum
- Single quotes for strings
- Use meaningful variable names
- Add type hints where appropriate
- Use docstrings for functions and classes

#### JavaScript/Node.js
- Follow [JavaScript Standard Style](https://standardjs.com/)
- Use ES6+ features
- Use async/await for asynchronous operations
- Add JSDoc comments for functions

#### General
- **Comments**: Explain *why*, not *what*
- **Error handling**: Show good patterns without overdoing it
- **Minimal dependencies**: Use standard libraries where possible
- **Educational**: Code should teach, not just work

### README Template

Each example needs a full README:

```markdown
# [Example Name]

## Overview
Brief description of what this example demonstrates (2-3 sentences).

## Prerequisites
- Avela API credentials
- Python 3.10+ / Node.js 16+ / etc.
- Any other specific requirements

## Installation
```bash
pip install -r requirements.txt
# or
npm install
```

## Configuration
```bash
# Store credentials in the OS keychain (it asks for the values)
python ../../shared/python/setup_credentials.py
```
On a server or in CI there is no keychain, so set `AVELA_CLIENT_ID`,
`AVELA_CLIENT_SECRET`, and `AVELA_ENVIRONMENT` in your environment instead. See

## Usage
```bash
python example.py
```

## What This Example Does
1. Step-by-step explanation
2. Of what the code does
3. And why it matters

## Key Concepts
- **Concept 1**: Explanation
- **Concept 2**: Explanation

## Expected Output
```
Show what success looks like
```

## Common Issues
- **Problem**: Solution
- **Problem**: Solution

## Related Examples
- [Related Example 1](../path/to/example/)
- [Related Example 2](../path/to/example/)

## API Reference
- [Relevant API Docs](https://prod.api-docs.avela.dev/v2/index.html)
```

### Security Requirements

**Never include in examples:**
- ❌ Actual API credentials
- ❌ Real email addresses or phone numbers
- ❌ Production database connection strings
- ❌ Private keys or certificates
- ❌ Internal URLs or endpoints

**Always include:**
- ✅ Credentials from `create_client()`, never a direct config file read
- ✅ Clear documentation on where to get credentials
- ✅ Input validation examples
- ✅ Proper error handling

### Testing Requirements

Before submitting, check that your example:

- [ ] **Runs successfully** on a clean system
- [ ] **Dependencies install** without errors
- [ ] **Credentials work** from environment variables and from the keychain
- [ ] **Configuration is clear** - documented in README
- [ ] **Includes sample output** - shows what to expect
- [ ] **Handles errors gracefully** - doesn't crash on common issues
- [ ] **Works with latest API** - test against current API version

## 📝 Pull Request Process

### 1. Fork and Create Branch

```bash
git clone https://github.com/YourUsername/integration-cookbook.git
cd integration-cookbook
git checkout -b feature/your-example-name
```

### 2. Make Your Changes

- Follow the example standards above
- Add a full README
- Test thoroughly
- Update the main README if you add a new category

### 3. Commit Guidelines

Use clear, descriptive commit messages:

```bash
git commit -m "Add Python example for bulk applicant import"
git commit -m "Fix authentication error in webhook handler"
git commit -m "Update REST API documentation"
```

**Commit message format:**
- Start with verb (Add, Fix, Update, Remove)
- Be specific about what changed
- Reference issues if applicable: `Fix #123: ...`

### 4. Submit Pull Request

1. Push your branch to your fork
2. Open a pull request against `main`
3. Fill out the PR template completely
4. Link related issues
5. Wait for review

### Pull Request Checklist

- [ ] Example follows directory structure
- [ ] README is complete and clear
- [ ] Code passes linting (`uv run ruff check .` and `uv run ruff format --check .`)
- [ ] Credentials come from `create_client()`
- [ ] No credentials or sensitive data
- [ ] Dependencies are documented
- [ ] Example has been tested
- [ ] Related documentation updated
- [ ] PR description explains the changes

**Note:** CI runs ruff on your PR. Make sure linting passes before you ask for review.

## 🐛 Reporting Issues

### Bug Reports

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md):

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, language version, etc.)
- Code snippets or error messages

### Example Requests

Use the [example request template](.github/ISSUE_TEMPLATE/example_request.md):

- Describe the integration pattern needed
- Explain the use case
- Provide context on why it's useful
- Suggest which category it fits

### Feature Requests

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md):

- Describe the enhancement
- Explain the benefit
- Provide examples if possible

## 🔍 Code Review Process

Every submission is reviewed. Reviewers check:

1. **Functionality** - Does the example work?
2. **Code quality** - Is it well-written and documented?
3. **Security** - Are there any security issues?
4. **Documentation** - Is the README clear and complete?
5. **Standards** - Does it follow our guidelines?

### Review Timeline

- Initial response: Within 3 business days
- Full review: Within 1 week
- Merging: After approval from 1+ maintainers

## 📚 Additional Resources

- [Avela API Documentation](https://prod.api-docs.avela.dev/v2/index.html)
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [JavaScript Style Guide](https://standardjs.com/)
- [How to Write a Good README](https://www.makeareadme.com/)

## 💬 Questions?

- Email: [help@avela.org](mailto:help@avela.org)
- Check existing [issues](https://github.com/Avela-Education/integration-cookbook/issues)

## 📜 Code of Conduct

This project has a [Code of Conduct](CODE_OF_CONDUCT.md). By taking part, you agree to follow it.

---

Thank you for contributing to the Avela Integration Cookbook! 🙏
