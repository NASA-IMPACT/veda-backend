# Implement automated data ingestion

## Status

Proposed

## Context

There is currently no standard process for getting scientists' data into the dashboard. We have roughly the following use-cases: 
1. Scientists upload COGs directly to the S3 bucket (eg: CO2 and NO2 datastes)
2. Scientists email us COGs that are ready to be uploaded to the bucket (eg: agriculture cropmonitor)
3. Scientists upload GeoTiff's to S3, that need to be converted to (eg: nightlights HD)
4. Scientists upload GeoTiff's to S3, the need to be "stitched" together (eg: nightlights VIIRS)

In the first case above, with scientists uploading their COGs directly, we run into the possibility that the COGs have not been correctly generated (formatting issues, lack of `nodata` value, etc) and are not displayable in the dashboard.

The latter three cases take time for the API maintainers to address and process manually. This also allows scientists the flexibility of updating/changing their own processing pipelines, knowing that there is no automated processing that might fail since we process the data manually. 

## Decision
Implement an ingestion pipeline that does the following: 

Default case:
1. Validates that the COG is correctly formatted (eg: `rio cogeo validate`) 
2. Updates a queryable metadata store with the temporal and geographic bounds of the data, in order to make it discoverable from the interface

Custom case: 
1. Allows scientists (or developers working with scientsits) to provide their own custom pre-processing script that will be run on upload
2. Run the processing steps from above

## Consequences

- Reduce the risk of malformatted data being uploaded
- Reduce time spent processing data manually
- Reduce time spent updating and managing custom processing code for certain datasets
- Potentially creates more work for scientists who now either have to provide their own custom processing code or implement a pipeline to generate COGs before uploading them to S3. (Obviously we will be available to help scientists in either case, given our in-house COG expertise.)