"""Custom Alternate Asset Reader."""

import attr
from rio_tiler.errors import InvalidAssetName, MissingAssets
from rio_tiler.types import AssetInfo

from titiler.pgstac.reader import PgSTACReader


@attr.s
class PgSTACReaderAlt(PgSTACReader):
    """Custom STAC Reader for the alternate asset format used widely by NASA.

    Only accept `pystac.Item` as input (while rio_tiler.io.STACReader accepts url or pystac.Item)

    """

    def _get_asset_info(self, asset: str) -> AssetInfo:
        """Validate asset names and return asset's url.
        Args:
            asset (str): STAC asset name.
        Returns:
            str: STAC asset href.
        """
        if asset not in self.assets:
            raise InvalidAssetName(f"{asset} is not valid")

        asset_info = self.input.assets[asset]
        extras = asset_info.extra_fields

        if ("alternate" not in extras) or ("s3" not in extras["alternate"]):
            raise MissingAssets("No alternate asset found")

        info = AssetInfo(url=extras["alternate"]["s3"]["href"], metadata=extras)

        info["env"] = {}

        if "file:header_size" in asset_info.extra_fields:
            h = asset_info.extra_fields["file:header_size"]
            info["env"].update({"GDAL_INGESTED_BYTES_AT_OPEN": h})

        if requester_pays := extras["alternate"]["s3"].get("storage:requester_pays"):
            if requester_pays:
                info["env"].update({"AWS_REQUEST_PAYER": "requester"})

        if bands := extras.get("raster:bands"):
            stats = [
                (b["statistics"]["minimum"], b["statistics"]["maximum"])
                for b in bands
                if {"minimum", "maximum"}.issubset(b.get("statistics", {}))
            ]
            if len(stats) == len(bands):
                info["dataset_statistics"] = stats

        return info
