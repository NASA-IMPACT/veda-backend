"""A utility script to create ndjson STAC Collection and Item records from a given STAC catalog, not intended for large catalogs"""
import os
import argparse
from datetime import datetime
import json
import shutil
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from pystac_client import Client

parser = argparse.ArgumentParser()
parser.add_argument(
    "-s",
    "--stac_api",
    dest="stac_api",
    type=str,
    required=True,
    help="Url of STAC catalog",
)
parser.add_argument(
    "-c",
    "--collection_id",
    dest="collection_id",
    type=str,
    required=False,
    default=None,
    help="Optional identifier for collection to back up. If not supplied all collections will be included",
)
parser.add_argument(
    "-b",
    "--bucket",
    dest="bucket",
    type=str,
    required=False,
    default=None,
    help="Optional S3 destination bucket to store ndjson backup. If not provided, local files will be created.",
)
parser.add_argument(
    "-n",
    "--profile_name",
    dest="profile_name",
    type=str,
    required=False,
    default=None,
    help="Optional AWS profile name for boto3 session configuration",
)
parser.add_argument(
    "-p",
    "--prefix",
    dest="prefix",
    type=str,
    required=False,
    default=None,
    help="Optional S3 destination key prefix or local path prefix to store ndjson backup. If not provided, the datetime of the run will be used.",
)
parser.add_argument(
    "-d",
    "--delete ",
    dest="delete_local",
    required=False,
    default=False,
    action="store_true",
    help="Optional flag to delete local files at the end of processing, defaults False",
)
args = parser.parse_args()


def strip_dynamic_links(links: List[dict]) -> List[Optional[dict]]:
    """Strips dynamic catalog-specific links"""
    return [link for link in links if link["rel"] not in ["collection", "items", "parent", "root", "self"]]

# Setup destination 
date_prefix = datetime.utcnow().isoformat(timespec="hours")
prefix = date_prefix if not args.prefix else os.path.join(args.prefix, date_prefix)
collections_path = os.path.join(prefix,"collections-nd.json")
os.makedirs(prefix, exist_ok=True)


# Boto3 client if bucket provided
if args.bucket:
    bucket = args.bucket
    session = boto3.Session(profile_name=args.profile_name)
    s3_client = session.client('s3')

# Get STAC catalog
stac_client = Client.open(args.stac_api)

# List collection record(s)
if args.collection_id:
    collections = [stac_client.get_collection(args.collection_id)]
else:
    collections = stac_client.get_all_collections()

# Iterate over collections and produce ndjson
with open(collections_path, "w") as f_collections:
    for collection in collections:
        collection_dict = collection.to_dict(include_self_link=False)
        collection_dict["links"] = strip_dynamic_links(collection_dict["links"]) # TODO confirm that pypgstac will ignore self, parent, child links on load or strip these

        f_collections.write(f"{json.dumps(collection_dict)}\n")
        print(f"Collection {collection.id} written to {collections_path}")

        items_path = os.path.join(prefix, f"items-{collection.id}-nd.json")
        items_search = stac_client.search(collections=[collection.id])
        with open(items_path, "w") as f_items:
            items_dict = items_search.get_all_items_as_dict()
            for item in items_search.get_items():
                item_dict = item.to_dict(include_self_link=False)
                item_dict["links"] = strip_dynamic_links(item_dict["links"])
                f_items.write(f"{json.dumps(item_dict)}\n")

        # Upload items object if bucket config provided
        if args.bucket:
            print(f"Uploading {items_path=} to {bucket=}")
            try:
                response = s3_client.upload_file(items_path, bucket, items_path)
            except ClientError as e:
                raise e
        
    # Upload collections object if bucket config provided
    if args.bucket:
        print(f"Uploading {collections_path=} to {bucket=}")
        try:
            response = s3_client.upload_file(collections_path, bucket, collections_path)
        except ClientError as e:
            raise e
    
    if args.delete_local:
        print(f"Processing complete, removing {prefix=}")
        shutil.rmtree(prefix)

    print("fin.")

