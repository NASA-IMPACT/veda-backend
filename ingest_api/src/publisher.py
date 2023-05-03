import os
from typing import Union

import fsspec
import xarray as xr
import xstac
from pypgstac.db import PgstacDB
from src.schemas import (
    COGDataset,
    DashboardCollection,
    DataType,
    SpatioTemporalExtent,
    ZarrDataset,
)
from src.utils import (
    IngestionType,
    convert_decimals_to_float,
    get_db_credentials,
    load_into_pgstac,
)
from src.validators import get_s3_credentials
from src.vedaloader import VEDALoader


class Publisher:
    common_fields = [
        "title",
        "description",
        "license",
        "links",
        "time_density",
        "is_periodic",
    ]
    common = {
        "links": [],
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [[None, None]]},
        },
        "type": "Collection",
        "stac_version": "1.0.0",
    }

    def __init__(self) -> None:
        self.func_map = {
            DataType.zarr: self.create_zarr_collection,
            DataType.cog: self.create_cog_collection,
        }

    def get_template(self, dataset: Union[ZarrDataset, COGDataset]) -> dict:
        dataset_dict = dataset.dict()
        collection_dict = {
            "id": dataset_dict["collection"],
            **Publisher.common,
            **{
                key: dataset_dict[key]
                for key in Publisher.common_fields
                if key in dataset_dict.keys()
            },
        }
        return collection_dict

    def _create_zarr_template(self, dataset: ZarrDataset, store_path: str) -> dict:
        template = self.get_template(dataset)
        template["assets"] = {
            "zarr": {
                "href": store_path,
                "title": "Zarr Array Store",
                "description": "Zarr array store with one or several arrays (variables)",
                "roles": ["data", "zarr"],
                "type": "application/vnd+zarr",
                "xarray:open_kwargs": {
                    "engine": "zarr",
                    "chunks": {},
                    **dataset.xarray_kwargs,
                },
            }
        }
        return template

    def create_zarr_collection(self, dataset: ZarrDataset) -> dict:
        """
        Creates a zarr stac collection based off of the user input
        """
        s3_creds = get_s3_credentials()
        discovery = dataset.discovery_items[0]
        store_path = f"s3://{discovery.bucket}/{discovery.prefix}{discovery.zarr_store}"
        template = self._create_zarr_template(dataset, store_path)
        store = fsspec.get_mapper(store_path, client_kwargs=s3_creds)
        ds = xr.open_zarr(
            store, consolidated=bool(dataset.xarray_kwargs.get("consolidated"))
        )

        collection = xstac.xarray_to_stac(
            ds,
            template,
            temporal_dimension=dataset.temporal_dimension or "time",
            x_dimension=dataset.x_dimension or "lon",
            y_dimension=dataset.y_dimension or "lat",
            reference_system=dataset.reference_system or 4326,
        )
        return collection.to_dict()

    def create_cog_collection(self, dataset: COGDataset) -> dict:
        collection_stac = self.get_template(dataset)
        collection_stac["extent"] = SpatioTemporalExtent.parse_obj(
            {
                "spatial": {
                    "bbox": [
                        list(dataset.spatial_extent.dict(exclude_unset=True).values())
                    ]
                },
                "temporal": {
                    "interval": [
                        # most of our data uses the Z suffix for UTC - isoformat() doesn't
                        [
                            x.isoformat().replace("+00:00", "Z")
                            for x in list(
                                dataset.temporal_extent.dict(
                                    exclude_unset=True
                                ).values()
                            )
                        ]
                    ]
                },
            }
        )
        collection_stac["item_assets"] = {
            "cog_default": {
                "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                "roles": ["data", "layer"],
                "title": "Default COG Layer",
                "description": "Cloud optimized default layer to display on map",
            }
        }
        return collection_stac

    def generate_stac(
        self, dataset: Union[COGDataset, ZarrDataset], data_type: str
    ) -> dict:
        create_function = self.func_map.get(data_type, self.create_cog_collection)
        return create_function(dataset)

    def ingest(self, collection: DashboardCollection):
        """
        Takes a collection model,
        does necessary preprocessing,
        and loads into the PgSTAC collection table
        """
        creds = get_db_credentials(os.environ["DB_SECRET_ARN"])
        collection = [convert_decimals_to_float(collection.dict(by_alias=True))]
        with PgstacDB(dsn=creds.dsn_string, debug=True) as db:
            load_into_pgstac(
                db=db, ingestions=collection, table=IngestionType.collections
            )

    def delete(self, collection_id: str):
        """
        Deletes the collection from the database
        """
        creds = get_db_credentials(os.environ["DB_SECRET_ARN"])
        with PgstacDB(dsn=creds.dsn_string, debug=True) as db:
            loader = VEDALoader(db=db)
            loader.delete_collection(collection_id)
