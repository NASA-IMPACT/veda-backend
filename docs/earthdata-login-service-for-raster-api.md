# Earthdata login and credential rotation service for raster API

Access to [cloud optimized HLS Operation TOA](https://cmr.earthdata.nasa.gov/search/concepts/C2021957657-LPCLOUD.html) data hosted in the [LPCLOUD](https://search.earthdata.nasa.gov/search?q=C2021957657-LPCLOUD) requires an access token granted by an earthdata user login. In order to stream these cloud optimized assets in the delta-backend raster API, the sidcar [edl-credential-rotation](https://github.com/NASA-IMPACT/edl-credential-rotation#edl-credential-rotation) lambda service can be deployed to obtain and renew access tokens on behalf of the delta-backend raster API.

git: [edl-credential-rotation](https://github.com/NASA-IMPACT/edl-credential-rotation#edl-credential-rotation)

## Adding login credential rotation to a delta-backend stack

> Note: both the delta backend stack and the edl credential rotation stack must be deployed in the **`us-west-2`** region. This is the region where the S3 COG HLS assets are hosted and tokens granted in a different region will be rejected.

1. Deploy delta backend stack in `us-west-2` and note the ARN of the raster-api lambda after it is created.
2. Clone the [edl-crendential-rotation](https://github.com/NASA-IMPACT/edl-credential-rotation) repo.
3. Configure [environment settings](https://github.com/NASA-IMPACT/edl-credential-rotation#environment-settings) with a valid [earthdata login](https://urs.earthdata.nasa.gov/) USERNAME and PASSWORD and the raster-api ARN.
4. [Deploy the edl-credential-rotation service](https://github.com/NASA-IMPACT/edl-credential-rotation#cdk-commands) in `us-west-2`.
