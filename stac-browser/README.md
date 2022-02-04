## A simple STAC browser deployment

```bash
git clone git@github.com:radiantearth/stac-browser.git
cd stac-browser
npm install
```

Run it locally:
```
npm run start -- --CATALOG_URL="https://xxx.execute-api.us-east-1.amazonaws.com/"
```

Run it with S3 Static Website Hosting:

```
npm run build -- --CATALOG_URL="https://xxx.execute-api.us-east-1.amazonaws.com/"
aws s3 cp --recursive dist/ s3://delta-dev-stac-browser
```