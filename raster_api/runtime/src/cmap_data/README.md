## Additional colormap for VEDA

##### EPA colormap

ref: https://github.com/NASA-IMPACT/veda-config-ghg/issues/203

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

##### NLCD colormap

refs: 

- https://www.mrlc.gov/data/legends/national-land-cover-database-class-legend-and-description
- https://github.com/NASA-IMPACT/veda-backend/issues/429

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

##### Soil texture colormap

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