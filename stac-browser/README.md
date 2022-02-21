## A simple STAC browser deployment

```bash
git clone git@github.com:radiantearth/stac-browser.git
cd stac-browser
npm install
```

Run it locally:
```
export STAC_API_ENDPOINT=https://xxx.execute-api.us-east-1.amazonaws.com/
npm run start -- --CATALOG_URL=${STAC_API_ENDPOINT}
```

Run it with S3 Static Website Hosting:

```
npm run build -- --CATALOG_URL=${STAC_API_ENDPOINT}
# Currently deployed to s3://delta-dev-stac-browser
BROWSER_CODE_BUCKET=s3://delta-dev-stac-browser
aws s3 cp --recursive dist/ $BROWSER_CODE_BUCKET
```

## TODO:

Add CDK Code to automatically deploy. A challenge to doing so is the API handles pagination differently form how the browser code requests. The browser is simply using `?page=2` and our stac-api pages need a next token of the form `token=next:<next-item-id>`.
