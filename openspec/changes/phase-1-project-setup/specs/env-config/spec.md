## ADDED Requirements

### Requirement: Centralized Environment Config
The system SHALL support loading configurations from a `.env` file via `pydantic-settings` and validate necessary settings.

#### Scenario: Settings Loading
- **WHEN** the backend application starts and loads configuration settings
- **THEN** it validates type safety of environment variables and uses defaults if not set in `.env`
