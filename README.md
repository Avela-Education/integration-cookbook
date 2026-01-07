# Integration Cookbook 🚀

> Production-ready integration patterns for the Avela Education Platform

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![API Version](https://img.shields.io/badge/API-v2-green.svg)](https://docs.avela.org)

## 🎯 Quick Start

Get started with these production-ready recipes:

### 🔌 Fetch All Applicants (Python)
Retrieve and export applicant data with automatic pagination

```bash
# Clone the repository
git clone https://github.com/Avela-Education/integration-cookbook.git
cd integration-cookbook/api/applicants-fetch-all-python

# Set up and run
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp config.example.json config.json
# Edit config.json with your credentials
python avela_api_client.py
```

### 📊 Update Forms from CSV (Python)
Bulk update form answers by reading from a CSV file

```bash
cd api/forms-update-csv-python

# Set up and run
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
# Edit config.json with your credentials
python form_update_client.py
```

## 📚 Integration Methods

| Method | Use When | Best For | Example |
|--------|----------|----------|---------|
| **REST API** | Real-time data access | Custom apps, dashboards | [Fetch applicants](api/applicants-fetch-all-python/) |
| **CSV Import/Export** | Bulk operations | Data migration, reports | [Update forms](api/forms-update-csv-python/) |
| **Webhooks** | Event-driven | Real-time notifications | Coming soon |
| **Third-party Tools** | No-code integration | Zapier, Make.com | Coming soon |

## 🗂️ Browse by Category

### API Integration
Programmatic access to Avela data and functionality. Browse all recipes in the [api/](api/) folder.

**Available Recipes:**
- [**Fetch All Applicants (Python)**](api/applicants-fetch-all-python/) - Retrieve and export applicant data with automatic pagination
- [**Update Forms from CSV (Python)**](api/forms-update-csv-python/) - Bulk update form answers by reading from a CSV file
- [**Download Form Files (Python)**](api/forms-download-files-python/) - Batch download file attachments from forms

## 🛠️ Prerequisites

Before you begin, ensure you have:

1. **Avela API Credentials**
   - Client ID and Client Secret
   - [Request access](https://avela.org/api-access) from your Avela administrator

2. **Development Environment**
   - Python 3.10+ or Node.js 16+ (depending on examples)
   - Git for cloning the repository
   - Text editor or IDE

3. **Basic Knowledge**
   - REST APIs and HTTP
   - JSON data format
   - OAuth2 authentication (helpful but not required)

## 🔑 Authentication

All API examples use OAuth2 client credentials flow:
- Client ID and Client Secret provided by Avela
- Tokens valid for 24 hours
- Include in Authorization header: `Bearer {token}`

See the [Security Guide](SECURITY.md) for best practices.

## 📖 Documentation & Resources

- [**API Reference**](https://docs.avela.org/api/v2) - Complete API documentation
- [**Authentication Guide**](https://docs.avela.org/authentication) - OAuth2 setup
- [**Webhook Events**](https://docs.avela.org/webhooks) - Available events
- [**Rate Limits**](https://docs.avela.org/rate-limits) - API usage limits
- [**Support Portal**](https://support.avela.org) - Get help

## 🤝 Contributing

We welcome contributions from the community! Whether you want to:

- 🐛 Report a bug
- 💡 Request a new example
- 📝 Improve documentation
- 🔧 Submit a new integration pattern

Please see our [Contributing Guide](CONTRIBUTING.md) for:
- Code style guidelines
- Example standards and templates
- Pull request process
- Testing requirements

## 💬 Support & Community

- **📧 Email:** [api-support@avela.org](mailto:api-support@avela.org)
- **🐛 Bug Reports:** [GitHub Issues](https://github.com/Avela-Education/integration-cookbook/issues)
- **💬 Discussions:** [GitHub Discussions](https://github.com/Avela-Education/integration-cookbook/discussions)
- **📚 Documentation:** [docs.avela.org](https://docs.avela.org)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap

See our [Roadmap](ROADMAP.md) for planned examples and future features.

Want to request a new example? [Create an issue](https://github.com/Avela-Education/integration-cookbook/issues/new?template=example_request.md)!
