#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maps for the MunichRe hail-risk portfolio project.

The script plots hail occurrence, population exposure and a relative hail-risk proxy
for Germany. The risk proxy is only a screening metric, not an estimate of damage.
"""

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LogNorm
from matplotlib.ticker import FuncFormatter
from netCDF4 import Dataset

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

from shapely.geometry import Point
from shapely.prepared import prep


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
SAVE_DIR = BASE_DIR / "plots"

DATA_FILE = DATA_DIR / "hail_risk_proxy_0.1deg_2005-2023.nc"

FIG_DPI = 350
MAP_EXTENT = [5.2, 15.3, 47.1, 55.1]
SHOW_GRIDLINES = False

SAVE_DIR.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


risk_note = (
    "Relative risk proxy only. No insured values, claims data or vulnerability "
    "functions are included."
)


population_formatter = FuncFormatter(
    lambda x, pos: f"{x / 1000:.0f}k" if x >= 1000 else f"{x:.0f}"
)
risk_formatter = FuncFormatter(lambda x, pos: f"{x:.0f}")


def centres_to_edges(x):
    x = np.asarray(x)
    dx = np.diff(x)

    edges = np.zeros(len(x) + 1)
    edges[1:-1] = x[:-1] + dx / 2
    edges[0] = x[0] - dx[0] / 2
    edges[-1] = x[-1] + dx[-1] / 2

    return edges


def get_germany_geometry():
    shp = shpreader.natural_earth(
        resolution="10m",
        category="cultural",
        name="admin_0_countries",
    )

    for record in shpreader.Reader(shp).records():
        attrs = record.attributes
        names = [attrs.get("ADMIN"), attrs.get("NAME_LONG"), attrs.get("NAME")]

        if "Germany" in names:
            return record.geometry

    raise RuntimeError("Germany geometry not found.")


def get_state_lines():
    try:
        shp = shpreader.natural_earth(
            resolution="10m",
            category="cultural",
            name="admin_1_states_provinces_lines",
        )

        geoms = []
        for record in shpreader.Reader(shp).records():
            attrs = record.attributes
            country_info = [
                attrs.get("adm0_a3"),
                attrs.get("ADM0_A3"),
                attrs.get("admin"),
                attrs.get("ADMIN"),
            ]

            if "DEU" in country_info or "Germany" in country_info:
                if record.geometry is not None:
                    geoms.append(record.geometry)

        return geoms

    except Exception:
        return []


def make_germany_mask(lon, lat, germany_geom):
    germany = prep(germany_geom)
    mask = np.zeros((len(lat), len(lon)), dtype=bool)

    for i, la in enumerate(lat):
        for j, lo in enumerate(lon):
            point = Point(float(lo), float(la))
            mask[i, j] = germany.contains(point) or germany_geom.touches(point)

    return mask


def mask_for_plotting(data, germany_mask, positive_only=True):
    arr = np.asarray(data, dtype=float)
    arr = np.where(np.isfinite(arr), arr, np.nan)

    # Keep only Germany, and for the plotted fields hide empty grid cells.
    mask = ~germany_mask
    if positive_only:
        mask = mask | (arr <= 0)

    return np.ma.masked_where(mask, arr)


def percentile_limit(data, q, positive_only=False):
    vals = data.compressed()
    vals = vals[np.isfinite(vals)]

    if positive_only:
        vals = vals[vals > 0]

    if len(vals) == 0:
        return 1.0

    return np.nanpercentile(vals, q)


def setup_map(ax, germany_geom, state_geoms):
    ax.set_extent(MAP_EXTENT, crs=ccrs.PlateCarree())

    ax.add_feature(cfeature.OCEAN, facecolor="#ffffff", zorder=0)
    ax.add_feature(cfeature.LAND, facecolor="#f6f6f4", edgecolor="none", zorder=0)
    ax.add_feature(cfeature.BORDERS, linewidth=0.35, edgecolor="#b8b8b8", zorder=4)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.35, edgecolor="#b8b8b8", zorder=4)

    ax.add_geometries(
        [germany_geom],
        crs=ccrs.PlateCarree(),
        facecolor="none",
        edgecolor="#303030",
        linewidth=0.9,
        zorder=6,
    )

    if state_geoms:
        ax.add_geometries(
            state_geoms,
            crs=ccrs.PlateCarree(),
            facecolor="none",
            edgecolor="#707070",
            linewidth=0.35,
            alpha=0.7,
            zorder=5,
        )

    if not SHOW_GRIDLINES:
        ax.set_xticks([])
        ax.set_yticks([])
        return

    gl = ax.gridlines(
        draw_labels=True,
        x_inline=False,
        y_inline=False,
        linewidth=0.25,
        alpha=0.35,
        color="#808080",
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlocator = mticker.FixedLocator(np.arange(6, 16, 2))
    gl.ylocator = mticker.FixedLocator(np.arange(48, 56, 2))
    gl.xlabel_style = {"size": 9, "color": "#404040"}
    gl.ylabel_style = {"size": 9, "color": "#404040"}


def add_footer(fig):
    fig.text(
        0.01,
        0.01,
        risk_note,
        ha="left",
        va="bottom",
        fontsize=8.5,
        color="#555555",
    )


def save_figure(fig, name):
    png_path = SAVE_DIR / f"{name}.png"
    pdf_path = SAVE_DIR / f"{name}.pdf"

    fig.savefig(png_path, dpi=FIG_DPI, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")

    print(f"Saved: {png_path}")
    print(f"Saved: {pdf_path}")


def add_colorbar(mesh, ax, label, formatter=None, shrink=0.78):
    cbar = plt.colorbar(
        mesh,
        ax=ax,
        orientation="horizontal",
        pad=0.035,
        shrink=shrink,
        extend="max",
    )

    cbar.set_label(label, fontsize=10.5, labelpad=6)
    cbar.ax.tick_params(labelsize=9)

    if formatter is not None:
        cbar.ax.xaxis.set_major_formatter(formatter)

    return cbar


def make_single_map(
    lon_edges,
    lat_edges,
    data,
    title,
    subtitle,
    cbar_label,
    cmap,
    out_name,
    germany_geom,
    state_geoms,
    norm=None,
    vmin=None,
    vmax=None,
    formatter=None,
):
    fig = plt.figure(figsize=(8.2, 6.0))
    ax = plt.axes(projection=ccrs.PlateCarree())

    setup_map(ax, germany_geom, state_geoms)

    mesh = ax.pcolormesh(
        lon_edges,
        lat_edges,
        data,
        cmap=cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        shading="auto",
        transform=ccrs.PlateCarree(),
        zorder=3,
    )

    ax.set_title(title, fontsize=15, fontweight="bold", pad=12)
    ax.text(
        0.01,
        0.98,
        subtitle,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        color="#404040",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.78, pad=3),
        zorder=10,
    )

    add_colorbar(mesh, ax, cbar_label, formatter=formatter)
    add_footer(fig)

    fig.tight_layout(rect=[0, 0.035, 1, 1])
    save_figure(fig, out_name)
    plt.show()
    plt.close(fig)


def load_data():
    with Dataset(DATA_FILE) as nc:
        lon = np.asarray(nc.variables["lon"][:])
        lat = np.asarray(nc.variables["lat"][:])
        hail_count = np.asarray(nc.variables["hail_count"][:], dtype=float)
        population = np.asarray(nc.variables["population"][:], dtype=float)
        risk_proxy = np.asarray(nc.variables["risk_proxy"][:], dtype=float)

    return lon, lat, hail_count, population, risk_proxy


def main():
    lon, lat, hail_count, population, risk_proxy = load_data()
    lon_edges = centres_to_edges(lon)
    lat_edges = centres_to_edges(lat)

    germany_geom = get_germany_geometry()
    state_geoms = get_state_lines()
    germany_mask = make_germany_mask(lon, lat, germany_geom)

    hail_plot = mask_for_plotting(hail_count, germany_mask)
    population_plot = mask_for_plotting(population, germany_mask)
    risk_plot = mask_for_plotting(risk_proxy, germany_mask)

    hail_vmax = percentile_limit(hail_plot, 98)
    pop_vmin = percentile_limit(population_plot, 2, positive_only=True)
    pop_vmax = percentile_limit(population_plot, 98)
    risk_vmax = percentile_limit(risk_plot, 98)

    make_single_map(
        lon_edges=lon_edges,
        lat_edges=lat_edges,
        data=hail_plot,
        title="Observed hail hazard",
        subtitle="Hail occurrence count on a 0.1° grid, 2005–2023",
        cbar_label="Hail count",
        cmap="Blues",
        out_name="01_hail_hazard_report_style",
        germany_geom=germany_geom,
        state_geoms=state_geoms,
        vmin=0,
        vmax=hail_vmax,
    )

    make_single_map(
        lon_edges=lon_edges,
        lat_edges=lat_edges,
        data=population_plot,
        title="Population exposure",
        subtitle="GHSL GHS-POP 2020, 1 km, aggregated to the 0.1° hail grid",
        cbar_label="Population per 0.1° grid cell",
        cmap="cividis",
        out_name="02_population_exposure_report_style",
        germany_geom=germany_geom,
        state_geoms=state_geoms,
        norm=LogNorm(vmin=pop_vmin, vmax=pop_vmax),
        formatter=population_formatter,
    )

    make_single_map(
        lon_edges=lon_edges,
        lat_edges=lat_edges,
        data=risk_plot,
        title="Relative hail risk proxy",
        subtitle="Normalized hail occurrence × normalized population exposure",
        cbar_label="Relative risk proxy",
        cmap="YlOrRd",
        out_name="03_relative_hail_risk_proxy_report_style",
        germany_geom=germany_geom,
        state_geoms=state_geoms,
        vmin=0,
        vmax=risk_vmax,
        formatter=risk_formatter,
    )

    panel_items = [
        {
            "data": hail_plot,
            "title": "a) Hail hazard",
            "cmap": "Blues",
            "norm": None,
            "vmin": 0,
            "vmax": hail_vmax,
            "label": "Hail count",
            "formatter": None,
        },
        {
            "data": population_plot,
            "title": "b) Population exposure",
            "cmap": "cividis",
            "norm": LogNorm(vmin=pop_vmin, vmax=pop_vmax),
            "vmin": None,
            "vmax": None,
            "label": "Population",
            "formatter": population_formatter,
        },
        {
            "data": risk_plot,
            "title": "c) Relative risk proxy",
            "cmap": "YlOrRd",
            "norm": None,
            "vmin": 0,
            "vmax": risk_vmax,
            "label": "Risk proxy",
            "formatter": risk_formatter,
        },
    ]

    fig, axes = plt.subplots(
        1,
        3,
        figsize=(15.5, 5.7),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )

    for ax, item in zip(axes, panel_items):
        setup_map(ax, germany_geom, state_geoms)

        mesh = ax.pcolormesh(
            lon_edges,
            lat_edges,
            item["data"],
            cmap=item["cmap"],
            norm=item["norm"],
            vmin=item["vmin"],
            vmax=item["vmax"],
            shading="auto",
            transform=ccrs.PlateCarree(),
            zorder=3,
        )

        ax.set_title(item["title"], fontsize=13.5, fontweight="bold", pad=8)

        cbar = add_colorbar(
            mesh,
            ax,
            item["label"],
            formatter=item["formatter"],
            shrink=0.86,
        )
        cbar.set_label(item["label"], fontsize=9.5)
        cbar.ax.tick_params(labelsize=8.5)

    fig.suptitle(
        "Germany hail hazard, population exposure and relative risk proxy",
        fontsize=16,
        fontweight="bold",
        y=0.97,
    )
    fig.text(
        0.5,
        0.925,
        "A transparent geospatial risk-screening workflow for natural hazard and catastrophe-risk applications",
        ha="center",
        va="top",
        fontsize=10.5,
        color="#444444",
    )

    add_footer(fig)
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    save_figure(fig, "00_hail_risk_project_three_panel_report_style")

    plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
