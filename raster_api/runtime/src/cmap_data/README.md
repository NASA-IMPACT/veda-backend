# Additional colormap for VEDA

## EPA colormap

ref: <https://github.com/NASA-IMPACT/veda-config-ghg/issues/203>

```python
from matplotlib import colors
import numpy as np

my_cmap = colors.LinearSegmentedColormap.from_list(name='my_cmap',colors=['#6F4C9B', '#6059A9', '#5568B8', '#4E79C5', '#4D8AC6',
'#4E96BC', '#549EB3', '#59A5A9', '#60AB9E', '#69B190',
'#77B77D', '#8CBC68', '#A6BE54', '#BEBC48', '#D1B541',
'#DDAA3C', '#E49C39', '#E78C35', '#E67932', '#E4632D',
'#DF4828', '#DA2222', '#B8221E', '#95211B', '#721E17',
'#521A13'], N=3000)
my_cmap._init()

slopen = 200
alphas_slope = np.abs(np.linspace(0, 1.0, slopen))
alphas_stable = np.ones(3003-slopen)
alphas = np.concatenate((alphas_slope, alphas_stable))
my_cmap._lut[:,-1] = alphas
my_cmap.set_under('white', alpha=0)

x = np.linspace(0, 1, 256)
cmap_vals = my_cmap(x)[:, :]
cmap_uint8 = (cmap_vals * 255).astype('uint8')
np.save("epa-ghgi-ch4.npy", cmap_uint8)
```

## NLCD colormap

refs:

- <https://www.mrlc.gov/data/legends/national-land-cover-database-class-legend-and-description>
- <https://github.com/NASA-IMPACT/veda-backend/issues/429>

```python
import rasterio
from rio_tiler.colormap import parse_color
import numpy as np

# The COGs in the nlcd-annual-conus collection store an internal colormap
nlcd_filename = "/vsis3/veda-data-store/nlcd-annual-conus/nlcd_2001_cog_v2.tif"

# These categories are only used to set transparency and document categories defined in colormap
# https://www.mrlc.gov/data/legends/national-land-cover-database-class-legend-and-description
nlcd_categories = {
    "11": "Open Water",
    "12": "Perennial Ice/Snow",
    "21": "Developed, Open Space",
    "22": "Developed, Low Intensity",
    "23": "Developed, Medium Intensity",
    "24": "Developed, High Intensity",
    "31": "Barren Land (Rock/Sand/Clay)",
    "41": "Deciduous Forest",
    "42": "Evergreen Forest",
    "43": "Mixed Forest",
    "51": "Dwarf Scrub",
    "52": "Shrub/Scrub",
    "71": "Grassland/Herbaceous",
    "72": "Sedge/Herbaceous",
    "73": "Lichens",
    "74": "Moss",
    "81": "Pasture/Hay",
    "82": "Cultivated Crops",
    "90": "Woody Wetlands",
    "95": "Emergent Herbaceous Wetlands"
}

with rasterio.open(nlcd_filename) as r:
    internal_colormap = r.colormap(1)

cmap = np.zeros((256, 4), dtype=np.uint8)
cmap[:] = np.array([0, 0, 0, 255])
for c, v in internal_colormap.items():
    if str(c) in nlcd_categories.keys():
        cmap[c] = np.array(parse_color(v))

np.save("nlcd.npy", cmap)
```

## Soil texture colormap

```python
from rio_tiler.colormap import parse_color
import numpy as np

# These categories are based on a USGS soil texture chart, not an official set of color mappings for soil texture categories
texture_categories = {
    "1": "#F89E61",
    "2": "#BA8560",
    "3": "#D8D2B4",
    "4": "#AE734C",
    "5": "#9E8478",
    "6": "#C6A365",
    "7": "#B4A67D",
    "8": "#E1D4C4",
    "9": "#BEB56D",
    "10": "#777C7A",
    "11": "#A89B6F",
    "12": "#E9E2AF"
}

cmap = np.zeros((256, 4), dtype=np.uint8)
cmap[:] = np.array([0, 0, 0, 255])
for k in texture_categories.keys():
    cmap[int(k)] = np.array(parse_color(texture_categories[k]))

np.save("soil_texture.npy", cmap)
```

## Tornadoes colormap

```python
from rio_tiler.colormap import parse_color
import numpy as np

# Colormap for Enhanced Fujita (EF) scale ratings
tornado_ef_scale = {
    "0": "#add8e6", #EF0
    "1": "#90ee90", #EF1
    "2": "#ffe71f", #EF2
    "3": "#ffa500", #EF3
    "4": "#ff0000", #EF4
    "5": "#ff00ff", #EF5
    "6": "#b3bcc9", #EFU
}

cmap = np.zeros((256, 4), dtype=np.uint8)
cmap[:] = np.array([0, 0, 0, 255])
for k in tornado_ef_scale.keys():
    cmap[int(k)] = np.array(parse_color(tornado_ef_scale[k]))

np.save("tornado_ef_scale.npy", cmap)
```

## Surface Temperature Colormap

```python
from matplotlib import colors
import numpy as np

stops = [
    "#3CCBCE",
    "#C5F8FF",
    "#FEC5FF",
    "#E079FB",
    "#094FC9",
    "#009FFF",
    "#44E2FF",
    "#147F4F",
    "#79B32C",
    "#FDFE00",
    "#FF8700",
    "#FF0F00",
    "#9D0F2B",
    "#4D0000",
    "#BA2E6D",
]

st_cmap = colors.LinearSegmentedColormap.from_list(name='st_cmap',colors=stops, N=256)
x = np.arange(0, 256, 1, dtype=int)
st_cmap_vals = (st_cmap(x)[:, :] * 255).astype('uint8')

np.save("surface_temperature.npy", st_cmap_vals)
```

## OPERA Vegetation Disturbance Status Colormap

```python
from rio_tiler.colormap import parse_color
import numpy as np

opera_veg_dist_status_categories = {
    "0": "#121212",  # No disturbance
    "1": "#005555",  # First detection, <50% vegetation loss
    "2": "#897f4e",  # Provisional disturbance, <50%
    "3": "#dee043",  # Confirmed disturbance, <50%
    "4": "#008888",  # First detection, >=50% vegetation loss
    "5": "#e48727",  # Provisional disturbance, >=50%
    "6": "#e01b07",  # Confirmed disturbance, >=50%
    "7": "#777777",  # Confirmed disturbance, <50%, finished
    "8": "#dddddd",  # Confirmed disturbance, >=50%, finished
}

cmap = np.zeros((256, 4), dtype=np.uint8)

for value, color in opera_veg_dist_status_categories.items():
    cmap[int(value)] = np.array(parse_color(color), dtype=np.uint8)

cmap[255] = np.array([0, 0, 0, 0], dtype=np.uint8)

np.save("opera_veg_dist_status.npy", cmap)
```

## Sentinel OptiSAR Burn Severity Colormap

```python
from rio_tiler.colormap import parse_color
import numpy as np


optisar_fire_severity_categories = {
    "3": "#4CE600",  # Unburnt
    "4": "#FFFF00",  # Low Severity
    "5": "#E64C00",  # Medium Severity
    "6": "#E60000",  # High Severity
    "7": "#000000",  # Extreme Severity
}

# Create the 256-entry RGBA lookup table expected by VEDA.
# Undefined values remain transparent.
cmap = np.zeros((256, 4), dtype=np.uint8)

for value, color in optisar_fire_severity_categories.items():
    cmap[int(value)] = np.array(parse_color(color), dtype=np.uint8)

# Common nodata/background value
cmap[255] = np.array([0, 0, 0, 0], dtype=np.uint8)

np.save("optisar_fire_severity.npy", cmap)
```

## Sentinel-1 HydroSAR Water Extent Colormap

```python
from rio_tiler.colormap import parse_color
import numpy as np


# Sentinel-1 HydroSAR surface-water extent classification
s1_hydrosar_water_extent_categories = {
    "1": "#005CE6",  # Known Water
    "2": "#FF0000",  # Flooded Developed
    "3": "#4CE600",  # Flooded Vegetation
    "4": "#E69800",  # Flooded Cropland/Grassland
}

# Create the 256-entry RGBA lookup table expected by VEDA.
# Undefined values remain transparent.
cmap = np.zeros((256, 4), dtype=np.uint8)

for value, color in s1_hydrosar_water_extent_categories.items():
    cmap[int(value)] = np.array(parse_color(color), dtype=np.uint8)

# Explicit background/nodata values
cmap[0] = np.array([0, 0, 0, 0], dtype=np.uint8)
cmap[255] = np.array([0, 0, 0, 0], dtype=np.uint8)

np.save("s1_hydrosar_water_extent.npy", cmap)
```

### GAIA Building Exposure Colormap

ref: <https://dev.disasters.openveda.cloud/api/stac/collections/gaia-total-composite>

The `gaia-total-composite` render config uses an interval colormap over raw
built-up-area values (m² per pixel). A `.npy` colormap is a 256-entry lookup
table applied after the data is rescaled to 0-255, so this file is built for
`rescale=0,637500` (2500 m² per index), which places every class boundary on an
exact index. Requests must pass `rescale=0,637500` with
`colormap_name=gaia-exposure`; values >= 637500 m² clip to the top class.

```python
import numpy as np

# GAIA gridded building exposure: modeled built-up area in square metres per pixel.
# Class breakpoints and colors are taken verbatim from the `renders` block of the
# gaia-total-composite STAC collection.
#
# A .npy colormap is a 256-entry lookup table applied *after* the data has been
# rescaled to 0-255, so this LUT is built for `rescale=0,637500`
# (2500 m^2 per LUT index). That bin width puts every class boundary on an exact
# index. Values >= 637500 clip to index 255 and take the top class color.
# Requests must pass `rescale=0,637500` together with `colormap_name=gaia-exposure`.
BIN = 2500

gaia_exposure_classes = [
    ((0, 25000), (63, 42, 107, 255)),
    ((25000, 50000), (62, 134, 158, 255)),
    ((50000, 75000), (115, 192, 195, 255)),
    ((75000, 100000), (195, 224, 156, 255)),
    ((100000, 150000), (247, 233, 156, 255)),
    ((150000, 300000), (243, 197, 86, 255)),
    ((300000, 450000), (231, 142, 65, 255)),
    ((450000, 10000000), (207, 73, 49, 255)),
]

cmap = np.zeros((256, 4), dtype=np.uint8)
for (start, end), color in gaia_exposure_classes:
    cmap[start // BIN : min(end // BIN, 256)] = color

np.save("gaia-exposure.npy", cmap)
```

### OPERA Generic Disturbance Status Colormap

ref: <https://dev.disasters.openveda.cloud/api/stac/collections/opera-distalert-gen-dist-status-daily>

```python
from rio_tiler.colormap import parse_color
import numpy as np

# OPERA DIST-ALERT GEN-DIST-STATUS layer (Sentinel-1 and HLS products): generic
# (all land cover) disturbance detection status and confidence. Classes 7 and 8
# (finished) occur in the HLS product only. Colors match the `renders` block of
# the opera-distalert-gen-dist-status-daily STAC collection.
opera_gen_dist_status_categories = {
    "0": "#ffffff",  # No disturbance
    "1": "#ffffb2",  # First detection, low confidence
    "2": "#fecc5c",  # Provisional disturbance, low confidence
    "3": "#fd8d3c",  # Confirmed disturbance, low confidence
    "4": "#fc4e2a",  # First detection, high confidence
    "5": "#e31a1c",  # Provisional disturbance, high confidence
    "6": "#b10026",  # Confirmed disturbance, high confidence
    "7": "#777777",  # Confirmed disturbance, low confidence, finished (HLS)
    "8": "#dddddd",  # Confirmed disturbance, high confidence, finished (HLS)
}

cmap = np.zeros((256, 4), dtype=np.uint8)

for value, color in opera_gen_dist_status_categories.items():
    cmap[int(value)] = np.array(parse_color(color), dtype=np.uint8)

cmap[255] = np.array([0, 0, 0, 0], dtype=np.uint8)

np.save("opera_gen_dist_status.npy", cmap)
```

## TEMPO NO2 Rainbow 4 Colormap

ref: https://worldview.earthdata.nasa.gov/

This colormap approximates the Rainbow 4 palette in NASA Worldview, based on the TEMPO NO2 provider screenshot. The default display maximum should be 20 × 10^15 molecules/cm² instead of 30 × 10^15 molecules/cm². The display range must be configured separately from the colormap.

```python
import numpy as np
from matplotlib import colors

# Approximate Worldview Rainbow 4 color stops
tempo_no2_stops = [
    (0.00, "#3582C6"),
    (0.10, "#93D0AC"),
    (0.19, "#EFF4A9"),
    (0.29, "#FEE7A0"),
    (0.38, "#FEA258"),
    (0.48, "#E85B63"),
    (0.58, "#B43678"),
    (0.67, "#731F7F"),
    (0.77, "#3E1169"),
    (0.86, "#180C39"),
    (0.96, "#090513"),
    (1.00, "#5A585E"),
]

cmap = colors.LinearSegmentedColormap.from_list(
    "tempo_no2",
    tempo_no2_stops,
    N=256,
)

cmap_vals = (cmap(np.arange(256)) * 255).astype("uint8")

np.save("tempo_no2.npy", cmap_vals)
```

## NAQFC Ozone (8-Hour) Colormap

ref: https://github.com/Air-Quality-Portal/aq-arch/issues/192

This colormap approximates the ozone color ramp used in the NOAA Air Quality Forecast Guidance Viewer. Colors were sampled from the provider's screenshot showing ozone concentrations from 0 to 200 ppb (0–0.200 ppm).

```python
import numpy as np
from matplotlib import colors

# Ozone concentration in ppb and corresponding screenshot colors
o3_stops = [
    (0, "#AFFEB0"),
    (10, "#7EFE7E"),
    (20, "#4BFF4C"),
    (30, "#08F001"),
    (40, "#03C300"),
    (50, "#008700"),
    (60, "#E1E103"),
    (70, "#FEBC2E"),
    (80, "#E17411"),
    (90, "#FE7879"),
    (100, "#BE0001"),
    (110, "#F0B4E7"),
    (120, "#DC8CD3"),
    (130, "#C864BF"),
    (140, "#B43DAB"),
    (150, "#A02497"),
    (160, "#8B1D83"),
    (170, "#781470"),
    (180, "#640D5B"),
    (190, "#500347"),
    (200, "#3C003C"),
]

# Normalize ozone concentrations to 0-1
normalized_stops = [
    (value / 200.0, color)
    for value, color in o3_stops
]

cmap = colors.LinearSegmentedColormap.from_list(
    "naqfc_o3",
    normalized_stops,
    N=256,
)

cmap_vals = (cmap(np.arange(256)) * 255).astype("uint8")

np.save("naqfc_o3.npy", cmap_vals)
```

## NAQFC PM2.5 (24-Hour) Colormap

ref: https://github.com/Air-Quality-Portal/aq-arch/issues/192

This colormap uses the same color progression as the NAQFC ozone viewer, redistributed across the EPA 24-hour PM2.5 AQI concentration breakpoints. The range is 0–225.4 µg/m³. Unlike the ozone ramp, these colors are derived from the ozone screenshot rather than an official PM2.5 color table.

```python
import numpy as np
from matplotlib import colors

# Reference ozone color ramp from the supplied screenshot
o3_stops = [
    (0, "#AFFEB0"),
    (10, "#7EFE7E"),
    (20, "#4BFF4C"),
    (30, "#08F001"),
    (40, "#03C300"),
    (50, "#008700"),
    (60, "#E1E103"),
    (70, "#FEBC2E"),
    (80, "#E17411"),
    (90, "#FE7879"),
    (100, "#BE0001"),
    (110, "#F0B4E7"),
    (120, "#DC8CD3"),
    (130, "#C864BF"),
    (140, "#B43DAB"),
    (150, "#A02497"),
    (160, "#8B1D83"),
    (170, "#781470"),
    (180, "#640D5B"),
    (190, "#500347"),
    (200, "#3C003C"),
]

normalized_stops = [
    (value / 200.0, color)
    for value, color in o3_stops
]

o3_cmap = colors.LinearSegmentedColormap.from_list(
    "naqfc_o3",
    normalized_stops,
    N=256,
)

# EPA 24-hour PM2.5 AQI category upper bounds (µg/m³)
pm25_breakpoints = np.array([
    0.0, 9.0, 35.4, 55.4, 125.4, 225.4
])

# Corresponding ozone positions used for the color progression
o3_breakpoints = np.array([
    0.0, 54.0, 70.0, 85.0, 105.0, 200.0
])

# Generate a 256-entry lookup table over 0-225.4 µg/m³
pm25_values = np.linspace(0, 225.4, 256)

# Map each PM2.5 concentration to its equivalent position
# within the ozone-derived color progression.
mapped_o3 = np.interp(
    pm25_values,
    pm25_breakpoints,
    o3_breakpoints,
)

# Convert mapped ozone positions to normalized palette coordinates
cmap_vals = (
    o3_cmap(mapped_o3 / 200.0) * 255
).astype("uint8")

np.save("naqfc_pm25.npy", cmap_vals)
```
 