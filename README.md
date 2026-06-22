# Germany Hail Risk Proxy

This project is a small geospatial natural hazard and catastrophe-risk 
portfolio project.

The goal is to combine observed hail occurrence over Germany with public 
population exposure data and calculate a relative hail risk proxy on a 
0.1° grid.

The project produces:

1. a hail hazard layer based on observed hail occurrence,
2. a population exposure layer,
3. a relative hail risk proxy map.

The relative risk proxy is calculated from normalized hail occurrence and 
normalized population exposure.

This is a screening-level relative risk index, not an insured-loss or 
damage estimate. No claims data, insured values, or vulnerability 
functions are included.

## Project structure

```text
scripts/
  01_add_population_to_hail_grid.py
  02_calculate_hail_risk_proxy.py
  03_plot_final_maps.py

data/
  README.md

plots/
```

## Workflow

The workflow consists of three main steps.

### 1. Add population exposure to the hail grid

```bash
python scripts/01_add_population_to_hail_grid.py
```

This script takes the hail occurrence grid and aggregates population data 
to the same 0.1° grid.

Input:

* `data/hail_occurrence_0.1deg_2005-2023.nc`
* `data/exposure/GHS_POP_E2020_GLOBE_R2023A_54009_1000_V1_0.tif`

Output:

* `data/hail_occurrence_plus_population_0.1deg_2005-2023.nc`

### 2. Calculate the relative hail risk proxy

```bash
python scripts/02_calculate_hail_risk_proxy.py
```

This script normalizes the hail occurrence and population exposure fields 
and combines them into a relative risk proxy.

The population field is log-transformed before normalization because 
population density is strongly skewed.

Output:

* `data/hail_risk_proxy_0.1deg_2005-2023.nc`

### 3. Plot the final maps

```bash
python scripts/03_plot_final_maps.py
```

This script creates final report-style maps for:

* observed hail hazard,
* population exposure,
* relative hail risk proxy.

Output figures are saved in the `plots/` folder.

## Data

Large input datasets are not included in this repository.

Expected local input files:

```text
data/
  hail_occurrence_0.1deg_2005-2023.nc
  exposure/
    GHS_POP_E2020_GLOBE_R2023A_54009_1000_V1_0.tif
```

The hail occurrence file contains observed hail counts aggregated to a 
0.1° grid over Germany for the period 2005–2023.

The population exposure input is based on GHSL GHS-POP 2020 population 
data.

## Python packages

The main Python packages used in this project are:

* numpy
* matplotlib
* netCDF4
* cartopy
* geopandas
* rasterio
* rasterstats
* shapely

Dependencies can be installed with:

```bash
pip install -r requirements.txt
```

## Notes

This project is intended as a transparent portfolio example for natural 
hazard, exposure, and catastrophe-risk analysis.

The result should be interpreted as a relative risk proxy. It highlights 
areas where observed hail occurrence and population exposure overlap, but 
it does not estimate financial losses or actual damage.

