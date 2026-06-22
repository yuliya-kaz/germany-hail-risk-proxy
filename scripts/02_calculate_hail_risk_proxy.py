#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calculate a relative hail risk proxy from hail occurrence and population exposure.
"""

from pathlib import Path
import numpy as np
from netCDF4 import Dataset

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

in_file = DATA_DIR / "hail_occurrence_plus_population_0.1deg_2005-2023.nc"
out_file = DATA_DIR / "hail_risk_proxy_0.1deg_2005-2023.nc"


def robust_normalize(data, upper_percentile=98):
    data = np.asarray(data, dtype=float)
    data = np.where(np.isfinite(data), data, np.nan)

    vmax = np.nanpercentile(data, upper_percentile)

    if not np.isfinite(vmax) or vmax <= 0:
        return np.zeros_like(data)

    return np.clip(data / vmax, 0, 1)


def load_data(path):
    with Dataset(path) as nc:
        lon = nc.variables["lon"][:]
        lat = nc.variables["lat"][:]
        hail_count = nc.variables["hail_count"][:]
        population = nc.variables["population"][:]

    return (
        np.asarray(lon),
        np.asarray(lat),
        np.asarray(hail_count, dtype=float),
        np.asarray(population, dtype=float),
    )


def clean_values(data):
    data = np.where(np.isfinite(data), data, 0)
    data = np.where(data < 0, 0, data)
    return data


def save_to_netcdf(path, lon, lat, hail_count, population, hazard_norm, exposure_norm, risk_proxy):
    with Dataset(path, "w", format="NETCDF4") as nc:
        nc.createDimension("lat", len(lat))
        nc.createDimension("lon", len(lon))

        lat_var = nc.createVariable("lat", "f4", ("lat",))
        lon_var = nc.createVariable("lon", "f4", ("lon",))

        hail_var = nc.createVariable("hail_count", "f4", ("lat", "lon"))
        pop_var = nc.createVariable("population", "f4", ("lat", "lon"))
        hazard_var = nc.createVariable("hazard_norm", "f4", ("lat", "lon"))
        exposure_var = nc.createVariable("exposure_norm", "f4", ("lat", "lon"))
        risk_var = nc.createVariable("risk_proxy", "f4", ("lat", "lon"))

        lat_var[:] = lat
        lon_var[:] = lon
        hail_var[:, :] = hail_count
        pop_var[:, :] = population
        hazard_var[:, :] = hazard_norm
        exposure_var[:, :] = exposure_norm
        risk_var[:, :] = risk_proxy

        lat_var.units = "degrees_north"
        lon_var.units = "degrees_east"

        hail_var.long_name = "Observed hail occurrence count"
        hail_var.period = "2005-04-01 to 2023-09-30"

        pop_var.long_name = "Population exposure aggregated to 0.1 degree hail grid"
        pop_var.units = "people per 0.1 degree grid cell"
        pop_var.source = "GHSL GHS-POP 2020, 1 km"

        hazard_var.long_name = "Normalized hail hazard"
        hazard_var.description = "hail_count normalized by the 98th percentile and clipped to 0-1"

        exposure_var.long_name = "Normalized population exposure"
        exposure_var.description = "log10(population + 1) normalized by the 98th percentile and clipped to 0-1"

        risk_var.long_name = "Relative hail risk proxy"
        risk_var.units = "relative index, 0-100"
        risk_var.description = (
            "risk_proxy = hazard_norm * exposure_norm * 100. "
            "This is a relative risk proxy, not an insured-loss estimate."
        )


def main():
    lon, lat, hail_count, population = load_data(in_file)

    hail_count = clean_values(hail_count)
    population = clean_values(population)

    hazard_norm = robust_normalize(hail_count, upper_percentile=98)

    population_log = np.log10(population + 1)
    exposure_norm = robust_normalize(population_log, upper_percentile=98)

    risk_proxy = hazard_norm * exposure_norm * 100
    risk_proxy = np.where(hail_count > 0, risk_proxy, 0)

    save_to_netcdf(
        out_file,
        lon,
        lat,
        hail_count,
        population,
        hazard_norm,
        exposure_norm,
        risk_proxy,
    )

    print(f"Saved: {out_file}")
    print("hail_count min/max:", np.nanmin(hail_count), np.nanmax(hail_count))
    print("population min/max:", np.nanmin(population), np.nanmax(population))
    print("hazard_norm min/max:", np.nanmin(hazard_norm), np.nanmax(hazard_norm))
    print("exposure_norm min/max:", np.nanmin(exposure_norm), np.nanmax(exposure_norm))
    print("risk_proxy min/max:", np.nanmin(risk_proxy), np.nanmax(risk_proxy))


if __name__ == "__main__":
    main()
