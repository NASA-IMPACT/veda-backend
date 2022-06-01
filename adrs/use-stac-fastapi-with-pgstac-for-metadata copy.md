# Use STAC-Fastapi with PgSTAC for metadata

## Status

Proposed

## Context
We will implement a Spatio Temporal Asset Catalog (STAC) specification metadata store and API to support the evolution of a dashboard used for displaying and interacting with geospatial datasets an models.

## Decision

### [STAC-FastApi](https://github.com/stac-utils/stac-fastapi) 
Client enforces industry standard stac-api specification, provides basic support and guidance for adding extensions to the core specification, and defines types (but does not yet implement pydantic). The API can be implemented with a SqlAlchemy backend or PGStac, we will implement the latter. FastAPI provides browser based interactive API documentation by default.

### [PGStac](https://github.com/stac-utils/pgstac)
PostgreSQL schema and functions supporting stac-api.

### Pros
- Community defined standards and best practices provide a strong starting point for defining the dashboard metadata backend--revealing both common usage patterns and pitfals.
- Python 
- PostgreSQL datastorage will make a wide variety of spatial and temporal inquiries possible.

- stac-spec [collection](https://github.com/radiantearth/stac-spec/tree/master/collection-spec), [collection fields](https://github.com/radiantearth/stac-spec/blob/master/collection-spec/collection-spec.md#collection-fields)
- stac-spec [item](https://github.com/radiantearth/stac-spec/tree/master/item-spec), [item fields](https://github.com/radiantearth/stac-spec/blob/master/item-spec/item-spec.md#item-fields)
- stac-spec [extensions](https://stac-extensions.github.io/)


STAC release 1.x compliant 
- API
- PostgreSQL schema
- PostgreSQL client
- Relevant extensions already implemented in stac-fastapi+pgstac
  - raster metadata
  - proj metadata
  - filter api spec
  - ?versioning indicators
  - ?tiling


### Complimentary tooling and examples
- [TiTiler-PgSTAC](https://github.com/stac-utils/titiler-pgstac) supports using stac-api queries as titiler sources.
- [rio-stac](http://devseed.com/rio-stac/) and [stac-fastapi-rio-stac](https://github.com/developmentseed/stac-fastapi-rio-stac) for generating and publishing STAC records for raster data.
- [eoAPI](https://github.com/developmentseed/eoAPI) PgSTAC + TiTiler-pgSTAC example with AWS CDK deployment.


### Also considered
- [sat-api-pg](https://github.com/developmentseed/sat-api-pg) uses an older version of the stac specification 0.8 and is not immediately compatibale with version 1.x of the standard.
- [pygeoapi](https://docs.pygeoapi.io/en/stable/) provides an Open Geospatial Consortium compliant metadata server and API that also adopts the STAC specification. 
  
## Consequences
There will be some startup cost to standing up and learning to use a new database and API, but using an actively maintained ecosystem of tooling for stac-fastapi and pgstac will accelerate the initial deployment and operation a STAC compliant API and PostGreSQL metadata store. Dashboard evolution work can quickly jump to developing new functionality such as scientific model metadata and aggregating dataset statistics over custom temporal ranges.

Some dashboard use cases will require new development and there will be some adjustment needed to transition from static/periodically updted S3 collection metadata JSON files to STAC spec API geojson responses.

Dashboard API and metadata storage evolution developments on stac-spec, stac-fastapi, and pgstac are likely to be widely applicable and could be contributed back to the STAC community.

