#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add population exposure to the existing 0.1° hail grid.
"""

from pathlib import Path
import numpy as np
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
from shapely.geometry import box
from netCDF4 import Dataset


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
EXPOSURE_DIR = DATA_DIR / "exposure"

hail_file = DATA_DIR / "hail_occurrence_0.1deg_2005-2023.nc"
population_file = EXPOSURE_DIR / "GHS_POP_E2020_GLOBE_R2023A_54009_1000_V1_0.tif"
out_file = DATA_DIR / "hail_occurrence_plus_population_0.1deg_2005-2023.nc"

DATA_DIR.mkdir(exist_ok=True)


def load_hail_grid(path):
    with Dataset(path) as nc:
        hail_count = nc.variables["hail_count"][:]
        lon = nc.variables["lon"][:]
        lat = nc.variables["lat"][:]

    return (
        np.asarray(hail_count, dtype=float),
        np.asarray(lon, dtype=float),
        np.asarray(lat, dtype=float),
    )


def make_grid_polygons(lon, lat, hail_count):
    dlon = abs(np.mean(np.diff(lon)))
    dlat = abs(np.mean(np.diff(lat)))

    half_lon = dlon / 2
    half_lat = dlat / 2

    rows = []

    for i, la in enumerate(lat):
        for j, lo in enumerate(lon):
            rows.append(
                {
                    "lon": lo,
                    "lat": la,
                    "hail_count": hail_count[i, j],
                    "geometry": box(
                        lo - half_lon,
                        la - half_lat,
                        lo + half_lon,
                        la + half_lat,
                    ),
                }
            )

    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def add_population_to_grid(grid, population_path):
    with rasterio.open(population_path) as src:
        raster_crs = src.crs
        nodata = src.nodata

    grid_on_raster = grid.to_crs(raster_crs)

    stats = zonal_stats(
        vectors=grid_on_raster.geometry,
        raster=population_path,
        stats=["sum"],
        nodata=nodata,
        all_touched=True,
    )

    # Empty cells can return None, so turn them into zero population.
    population = np.array([item["sum"] if item["sum"] is not None else 0 for item in stats])
    grid["population"] = population

    return grid


def save_to_netcdf(path, lon, lat, hail_count, population_2d):
    with Dataset(path, "w", format="NETCDF4") as nc:
        nc.createDimension("lat", len(lat))
        nc.createDimension("lon", len(lon))

        lat_var = nc.createVariable("lat", "f4", ("lat",))
        lon_var = nc.createVariable("lon", "f4", ("lon",))
        hail_var = nc.createVariable("hail_count", "f4", ("lat", "lon"))
        pop_var = nc.createVariable("population", "f4", ("lat", "lon"))

        lat_var[:] = lat
        lon_var[:] = lon
        hail_var[:, :] = hail_count
        pop_var[:, :] = population_2d

        lat_var.units = "degrees_north"
        lon_var.units = "degrees_east"

        hail_var.long_name = "Observed hail occurrence count"
        hail_var.period = "2005-04-01 to 2023-09-30"

        pop_var.long_name = "Population exposure aggregated to hail grid"
        pop_var.units = "people per 0.1 degree grid cell"


def main():
    hail_count, lon, lat = load_hail_grid(hail_file)

    grid = make_grid_polygons(lon, lat, hail_count)
    grid = add_population_to_grid(grid, population_file)

    population_2d = grid["population"].values.reshape(len(lat), len(lon))

    save_to_netcdf(out_file, lon, lat, hail_count, population_2d)

    print(f"Saved: {out_file}")


if __name__ == "__main__":
    main()
