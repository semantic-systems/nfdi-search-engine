# NFDI Search Engine

The NFDI Search Engine is an ad hoc research gateway developed within the NFDI4DataScience context. It aggregates and searches scientific resources from multiple external data sources through a single web interface.

It provides a unified entry point to discover publications, researchers, datasets, projects, organizations, and related research resources across a broad set of integrated sources.


![NFDI Gateway – Search interface](https://github.com/semantic-systems/nfdi-search-engine/assets/58974800/5d805588-c61e-4ca1-a5d7-6f9bc540782a)

![NFDI Gateway – Search results](https://github.com/semantic-systems/nfdi-search-engine/assets/58974800/7b783634-916f-40b7-8fed-19dd19ea09c7)


## Overview

The system follows an ad hoc federated search approach. For each user query, multiple external data sources are queried in parallel. The responses are mapped to a common schema, aggregated, and presented in a unified interface.

There is no central index of external data. All results are retrieved on demand from the configured sources.

## Main capabilities

- Ad hoc federated search across multiple external research data providers
- Adapter based source integration with a shared internal data model
- Mapping of heterogeneous source responses to a common schema
- Aggregation of results into common categories such as publications and researchers
- Session based result handling for pagination and incremental loading
- Optional chatbot interaction over the current search result set
- User accounts with configurable source preferences

## Architecture in brief

- A user submits a query through the web interface
- The backend executes the query against external repositories via their APIs
- Each adapter maps its response to the shared internal schema
- A controller deduplicates and aggregates results across sources
- Results are grouped and stored in the user session
- The interface renders the results and supports loading more items per category
- If enabled, the current result set is shared with a chatbot service

The application is implemented as a Flask based web service.

## Source adapters

Source integrations are implemented as adapters.
Each adapter is a dedicated integration module that queries a specific external provider API and maps the response into the shared internal data model.

Each adapter is responsible for:

- Querying its upstream API or endpoint
- Handling authentication when required
- Mapping responses into the internal representation

The active sources are configured in `config.py`. Adding a new source typically means implementing a new adapter and registering it in the configuration.

Examples of integrated source types include scholarly repositories, research knowledge graphs, researcher identifier services, dataset repositories, and project or funding databases. The exact set of enabled sources depends on configuration and available credentials.

## Configuration

Configuration is managed through environment variables and `config.py`.

Typical configuration includes:

- A secret key for session handling
- Optional API keys for selected external providers
- Feature flags for optional components such as the chatbot

Sensitive values such as API keys should be provided through environment variables and not committed to the repository.

## Local development

### Clone the repository

Clone the repository and move into the project directory.

```bash
git clone https://github.com/semantic-systems/nfdi-search-engine.git
cd nfdi-search-engine

```

### Requirements

1. Python 3.11 or a compatible Python 3 version
2. A local virtual environment is recommended

### Environment setup

Before running the application, copy the example configuration files and adjust them as needed.

1. Copy `.env.example` to `.env`
2. Set at least the following variables:
   1. `SECRET_KEY` for session handling
   2. Optional API keys for external sources you enable
   3. Optional chatbot or analytics related settings

The file `config.py` defines the available configuration options and enabled sources.

For logging configuration, you may optionally copy `logging.conf.example` to `logging.conf` and adjust log levels or handlers.

### Install dependencies

```bash
pip install -r requirements.txt
```
### Run the application locally

```bash
python main.py
```
After starting, the web interface will be available on the configured port.

## Docker usage
A Dockerfile and Docker Compose configuration are provided for container based deployment.

### Build and run using Docker Compose
```bash
docker compose up --build
```
By default, the application is exposed on port 6000 on the host system.

## Chatbot integration
The application includes optional support for a chatbot that can assist with search result analysis based on the current result set.

When enabled:

- The result set of a search is shared with the chatbot service
- Users can ask natural language questions related to the results
- Responses are limited to the provided search context

The chatbot and language model configuration is optional and depends on deployment specific settings.

## Intended audience
This project is intended for:
- Developers who want to run or extend an ad hoc federated research search system
- Research infrastructure teams integrating multiple scholarly data sources
- Contributors working on adapters, backend logic, or the user interface

It is not intended to replace domain specific repositories or act as a long term archival system.

## License
See the LICENSE file in this repository.