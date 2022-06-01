# Use STAC-FastApi with PgSTAC for metadata

## Status

Proposed

## Context

We will implement a Spatio Temporal Asset Catalog (STAC) metadata store and API to support the evolution of a dashboard used for displaying and interacting with geospatial datasets an models.

## Decision

Two Python tools will be adopted for managing metadata for the dashboard: STAC-FastAPI built with a PGStac backend. Both decisions are in this record.

### [STAC-FastApi](https://github.com/stac-utils/stac-fastapi)

Client enforces industry standard stac-api specification, provides basic support and guidance for adding extensions to the core specification, and defines types (but does not yet implement pydantic). 

- FastAPI provides browser based interactive API documentation by default. 
- The API can be implemented with a SqlAlchemy backend or PGStac, we will implement the latter. 

### [PGStac](https://github.com/stac-utils/pgstac)

PostgreSQL schema and functions supporting stac-api.

- Using a PostgreSQL database will make a wide variety of spatial and temporal inquiries possible.
- Schema enforcement ensures the integrity of the metadata and ensures consistent API behavior for users.

### Complimentary tooling and examples

- [TiTiler-PgSTAC](https://github.com/stac-utils/titiler-pgstac) supports using stac-api queries as titiler sources.
- [rio-stac](http://devseed.com/rio-stac/) and [stac-fastapi-rio-stac](https://github.com/developmentseed/stac-fastapi-rio-stac) for generating and publishing STAC records for raster data.
- [eoAPI](https://github.com/developmentseed/eoAPI) PgSTAC + TiTiler-pgSTAC example with AWS CDK deployment.

### Also considered

- [sat-api-pg](https://github.com/developmentseed/sat-api-pg) uses an older version of the stac specification 0.8 and is not immediately compatibale with version 1.x of the standard.
- [pygeoapi](https://docs.pygeoapi.io/en/stable/) provides an Open Geospatial Consortium compliant metadata server and API that also adopts the STAC specification.

## Consequences

There will be some startup cost to standing up and learning to use a new database and API, but using an actively maintained ecosystem of tooling for stac-fastapi and pgstac will accelerate the initial deployment and operation a STAC compliant API and PostGreSQL metadata store. Dashboard evolution work can quickly jump to developing new functionality such as scientific model metadata and aggregating dataset statistics over custom temporal ranges.

Dashboard API and metadata storage evolution developments on stac-spec, stac-fastapi, and pgstac are likely to be widely applicable and could be contributed back to the STAC community.
