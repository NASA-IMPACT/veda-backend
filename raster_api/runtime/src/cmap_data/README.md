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
np.save("epa.npy", cmap_uint8)
```
