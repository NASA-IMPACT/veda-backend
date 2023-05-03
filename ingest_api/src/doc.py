DESCRIPTION = """
# Overview
The VEDA STAC Ingestor is a service that allows users and other services to add new
 records to the STAC database in order to manage geo spatial data.
It performs validation on the records, called STAC items, to ensure that they meet the
 STAC specification, all assets are accessible, and their collection exists. The
  service also performs other operations on the records.

# Usage

## Auth
The auth API allows users to retrieve an access token and get information about the
 current user.
To get an access token, the user must provide their username and password in the
 request body to the POST `/token` API.
The current user's information can be retrieved using the GET `/auth/me` API.

Before using the API, user must ask a VEDA team member to create credentials (username
 and password) for VEDA auth.
The user name and password is used to get the access token from Auth API call in order
 to authorize the execution of API.

## Ingestions

The ingestion API allows users to create, cancel, update, and retrieve information
 about STAC item ingests.

The `/ingestions/` endpoint includes a GET endpoint to list ingests based on their
 status.
The endpoint takes a single query parameter, `status`, which should be selected from a
 predefined set of allowed values in the form of a dropdown list.

The allowed values for the `status` parameter are:

* "started": Ingests that have started processing
* "queued": Ingests that are waiting to be processed
* "failed": Ingests that have failed during processing
* "succeeded": Ingests that have been successfully processed
* "cancelled": Ingests that were cancelled before completing

To create an ingestion, the user must provide the following information in the request
 body to the POST `/ingestions` API:
The API allows creating a new ingestion, which includes validating and processing a
 STAC item, and adding it to the STAC database.
The request body should be in JSON format and should contain the fields that specifies
 a STAC item. `https://stacspec.org/en/tutorials/intro-to-stac/#STAC-Item`

The `/ingestions/{ingestion_id}` GET endpoint allows retrieving information about a
 specific ingestion, including its current status and other metadata.

To cancel an ingestion, the user must provide the ingestion id to the DELETE
 `/ingestions/{ingestion_id}` API.

To update an ingestion, the user must provide the ingestion id and the new information
 to the PUT `/ingestions/{ingestion_id}` API.

## Collections
The collection API is used to create a new STAC collection dataset.
The input to the collection API is a STAC collection which follows the STAC
 collection specification.
     `https://github.com/radiantearth/stac-spec/blob/v1.0.0/collection-spec/collection-spec.md`

Following is a sample input for collection API:
```
{
  "id": "collection-id",
  "title": "Collection Title",
  "description": "A detailed description of the collection",
  "license": "LICENSE",
  "extent": {
    "spatial": [
      WEST, SOUTH,
      EAST, NORTH
    ],
    "temporal": [
      "START_DATE",
      "END_DATE"
    ]
  },
  "providers": [
    {
      "name": "Provider Name",
      "roles": ["role1", "role2"],
      "url": "http://example.com"
    }
  ],
  "stac_version": "STAC_VERSION",
  "links": [
    {
      "rel": "self",
      "href": "http://example.com/stac/collection-id"
    },
    {
      "rel": "items",
      "href": "http://example.com/stac/collection-id/items"
    }
  ]
}
```

To delete a collection, the user must provide the collection id to the `collections/
collection_id` API.


## Workflow Executions
The workflow execution API is used to start a new workflow execution. The workflow
 execution API accepts discovery from s3 or cmr.
To run a workflow execution, the user must provide the following information:

**For s3 discovery:**
We use inputs for the workflow from the veda-data-pipelines repository.
 `https://github.com/NASA-IMPACT/veda-data-pipelines/tree/main/data/step_function_inputs`.

Following is a sample input for s3 discovery:
```
{
    "collection": "EPA-annual-emissions_1A_Combustion_Mobile",
    "prefix": "EIS/cog/EPA-inventory-2012/annual/",
    "bucket": "veda-data-store-staging",
    "filename_regex": "^(.*)Combustion_Mobile.tif$",
    "discovery": "s3",
    "upload": False,
    "start_datetime": "2012-01-01T00:00:00Z",
    "end_datetime": "2012-12-31T23:59:59Z",
    "cogify": False,
}
```

We can use `workflow_executions/workflow_execution_id` to get the status of the
 workflow execution.
"""
