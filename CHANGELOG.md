# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Progressive Coverage Enforcement**: Automated CI/CD workflow requiring 1% coverage increase per PR from dev→main (90% cap)
  - New GitHub Actions workflow: `.github/workflows/coverage-enforcement.yml`
  - Comprehensive coverage policy documentation: `docs/COVERAGE_POLICY.md`
  - Detailed PR comments with coverage comparison, actionable guidance, and progress tracking
  - Automatic pass when 90% coverage cap is reached

## [0.2.0] - 2025-06-21

### Added
- **Multi-Tenancy Architecture**: Complete transformation to support multiple WhatsApp instances
  - SQLite database with InstanceConfig model for tenant management
  - Dynamic webhook routing: `/webhook/evolution/{instance_name}`
  - CRUD API endpoints for instance management (`/api/instances/`)
  - Typer-based CLI tools for instance administration
  - Full backward compatibility with existing single-tenant deployments

- **Comprehensive Makefile System**: Production-ready automation
  - Essential commands: `make dev`, `make install`, `make test`
  - Service management: `make install-service`, `make start-service`, `make stop-service`
  - Code quality: `make lint`, `make format`, `make typecheck`
  - Database tools: `make db-init`, `make cli-instances`, `make cli-create`
  - Publishing: `make build`, `make publish`, `make release`

- **Database Layer**: 
  - SQLAlchemy 2.0+ with async support
  - Instance configuration management
  - Automatic default instance creation from environment variables
  - Migration-ready database structure

- **CLI Management Tools**:
  - `omnihub-instance list` - List all configured instances
  - `omnihub-instance create` - Interactive instance creation
  - `omnihub-instance update` - Modify existing instances
  - `omnihub-instance delete` - Remove instances with confirmation
  - `omnihub-instance set-default` - Change default instance

### Changed
- **Webhook Processing**: Enhanced to support both multi-tenant and legacy endpoints
- **Configuration**: Per-instance configuration override capability
- **Service Injection**: Dynamic configuration injection based on instance
- **Error Handling**: Improved error responses and logging

### Fixed
- Audio transcription service configuration and error handling
- WhatsApp client presence update reliability
- Various unused variable assignments and import optimizations

### Configuration
- **New Environment Variables**:
  - Database configuration for multi-tenancy
  - Instance-specific overrides
- **New CLI Commands**:
  - `omnihub-instance` - Instance management interface
- **New API Endpoints**:
  - `GET /api/instances/` - List instances
  - `POST /api/instances/` - Create instance
  - `GET /api/instances/{name}` - Get instance details
  - `PUT /api/instances/{name}` - Update instance
  - `DELETE /api/instances/{name}` - Delete instance
  - `POST /api/instances/{name}/set-default` - Set as default

### Security
- Input validation with Pydantic models
- Proper error handling without information disclosure
- Environment-based secret management
- SQL injection protection via SQLAlchemy ORM

### Testing
- 100+ comprehensive test cases
- Database operations and models testing
- Multi-tenant webhook routing tests
- CRUD API endpoint validation
- CLI command interface testing
- Backward compatibility test suites

### Documentation
- Complete deployment guides and configuration examples
- Multi-tenancy architecture documentation
- API documentation with OpenAPI/Swagger
- CLI help system and usage examples
- Production deployment strategies

## [0.1.0] - Previous Release
- Initial single-tenant WhatsApp integration
- Basic webhook processing
- Audio transcription capabilities
- Evolution API integration