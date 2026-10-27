"""
PAPER FIGURE 4: share of population and area within a given distance of a market.
  panel a: detected periodic markets            fig04a_population_coverage.png
  panel b: OpenStreetMap marketplaces           fig04b_osm_coverage.png
  both, as the paper sets them side by side     fig04_population_coverage.png
(in output_paper/paper_exhibits; drawn by exhibits/plots.py)

Extracted from MAI_AFG/Code/AFG20250825.ipynb (cells 9-11 and 13), the detection
team's notebook, with the database credentials removed. The logic is unchanged.

NOT RUN in this repository's checks: it needs access that only the detection
team has.
  * Google Earth Engine read access to projects/planetupload (the ring tables)
    and projects/mali-candidate-locs (the city mask). Set EE_PROJECT to an Earth
    Engine project registered to an account with that access.
  * For `build_rings()` only: the MAI MySQL database holding the detected market
    locations. Set MAI_DB_URL to its SQLAlchemy URL
    (mysql+mysqlconnector://user:password@host:3306/mai-database).
    Once the ring tables exist, `plot()` does not need the database.

Population is the JRC GHSL 2023A population grid for 2020 (the paper's source
note says WorldPop 2020). "Major cities" are removed with the detection team's
city mask.

Panel b reads the detection team's OpenStreetMap ring tables (OSM_RING_ASSET and its
"without cities" twin), built the same way around OSM marketplaces that do not
coincide with a periodic market. They reproduce the bars of the panel b image in
the manuscript; the code that built them is not in this repository. (The earlier
"_osm" tables, without the 2, give higher shares and are not the paper's.)

    python figure4_population_coverage.py          # plot from the existing ring tables
    python figure4_population_coverage.py --build  # rebuild the ring tables first
"""
import os
import sys

import ee
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "NTL_processing"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "exhibits"))
import plots as P  # noqa: E402  (draws the figure in the house style of exhibits/style.py)
import style as S  # noqa: E402

COUNTRY = "Afghanistan"
RING_ASSET = f"projects/planetupload/assets/cleanedLocs/{COUNTRY}_ringsghsl"
RING_ASSET_NOCITIES = RING_ASSET + "_withoutcities"
CITY_MASK = "projects/mali-candidate-locs/assets/afghanistan-candidate-locs/cityMask"
OSM_RING_ASSET = "projects/planetupload/assets/cleanedLocs/Afghanistanadm1_ringsghsl_osm2"
OSM_RING_ASSET_NOCITIES = "projects/planetupload/assets/cleanedLocs/Afghanistanadm1_ringsghsl_withoutcities_osm2"

# National totals, from the original notebook.
TOTAL_POPULATION = 30830426
TOTAL_POPULATION_NOCITIES = 21660128
TOTAL_AREA_KM2 = 652867

POPULATION_LIMITS = [0, 500, 1000, 5000, 100000]

ee.Initialize(project=os.environ.get("EE_PROJECT", "p155mali1"))


def _population_images():
    boundaries_shp = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017").filter(
        ee.Filter.eq("country_na", COUNTRY))
    worldpop = ee.Image(ee.ImageCollection("JRC/GHSL/P2023A/GHS_POP")
                        .filterDate("2020-01-01", "2021-01-01").first()).clip(boundaries_shp)
    worldpop = worldpop.set("system:footprint", boundaries_shp.geometry())
    citymask = ee.FeatureCollection(CITY_MASK).union().first().geometry()
    worldpop_without_cities = worldpop.clip(boundaries_shp.geometry().difference(citymask))
    return boundaries_shp, worldpop, worldpop_without_cities


def _market_centroids():
    """Detected market locations, from the MAI database (same query as the notebook)."""
    from sqlalchemy import create_engine
    engine = create_engine(os.environ["MAI_DB_URL"])
    query = f"""
       SELECT marketLat, marketLon FROM `mai-database`.`location_file` lf
        WHERE to_delete IS NULL
        AND 00DownStatus IN ("complete","updating")
        AND country="{COUNTRY}"
        AND (false_positive IN (-1,0) OR false_positive IS NULL)
        AND EXISTS(
            SELECT 1 FROM process_runs pr2
            WHERE pr2.Location=lf.Location
            AND Setup="MpM6"
            AND Status="complete"
        )
        AND NOT EXISTS(
            SELECT 1 FROM process_runs pr
            WHERE pr.Location=lf.Location
            AND Setup="MpM6"
            AND runAnyway="no"
        )
        """
    df = pd.read_sql(query, engine)
    df = df[df["marketLat"].notnull()]
    df["geometry"] = [Point(xy) for xy in zip(df.marketLon, df.marketLat)]
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    print("# markets:", len(gdf))
    return gdf


def build_rings():
    """Union of 1, 2, 5, 10 and 20 km buffers around every market, with the
    population inside each, exported to the two ring assets (cell 10)."""
    import geemap
    boundaries_shp, worldpop, worldpop_without_cities = _population_images()
    geo = boundaries_shp.first().geometry(5)
    markets_fc = geemap.geopandas_to_ee(_market_centroids())
    rings = ee.FeatureCollection(ee.List([1000, 2000, 5000, 10000, 20000]).map(
        lambda r: markets_fc
        .map(lambda m: ee.Feature(m.buffer(r).simplify(ee.Number(r).divide(2))
                                  .intersection(geo, ee.Number(r).divide(2))))
        .union(ee.Number(r).divide(2)).first().set("radius", r))).map(
        lambda f: ee.Feature(f).set("area_km2", ee.Feature(f).area().divide(1e6)))

    for image, asset in [(worldpop, RING_ASSET), (worldpop_without_cities, RING_ASSET_NOCITIES)]:
        fc = image.reduceRegions(collection=rings, reducer=ee.Reducer.sum(),
                                 scale=worldpop.projection().nominalScale(), tileScale=16,
                                 ).select(["sum", "area_km2", "radius"],
                                          ["population", "area_km2", "radius"])
        ee.batch.Export.table.toAsset(collection=fc, description="export_grid_w_pop",
                                      assetId=asset).start()
    print("export tasks started; run again without --build once they finish")


def _ring_table(asset):
    feats = ee.FeatureCollection(asset).getInfo()["features"]
    return pd.DataFrame([f["properties"] for f in feats])


def coverage_table(asset=RING_ASSET, asset_nocities=RING_ASSET_NOCITIES):
    """Cell 11: population and area shares by distance band (the data of Figure 4a;
    with the OSM assets, of Figure 4b). Same national totals for both."""
    df_b = _ring_table(asset)
    df_b_nocities = _ring_table(asset_nocities)
    df_b = df_b.merge(df_b_nocities[["radius", "population"]], on="radius",
                      suffixes=("", "_nocities"))

    df_bb = df_b.sort_values(by="radius")
    df_bb["radius_km"] = df_bb["radius"] / 1000
    df_bb["population_share"] = 100 * df_bb["population"] / TOTAL_POPULATION
    df_bb["population_share_nocities"] = 100 * df_bb["population_nocities"] / TOTAL_POPULATION_NOCITIES
    df_bb["area_share"] = 100 * df_bb["area_km2"] / TOTAL_AREA_KM2
    df_bb = df_bb[df_bb["radius"] < 50000]
    df_bb = df_bb[["radius_km", "population_share", "area_share", "population_share_nocities"]]
    print(df_bb.to_string(index=False))
    return df_bb


def plot():
    """Save the figure data and draw it with exhibits/plots.py."""
    a = coverage_table()
    b = coverage_table(OSM_RING_ASSET, OSM_RING_ASSET_NOCITIES)
    S.save_data(a, "fig04a_population_coverage")
    S.save_data(b, "fig04b_osm_coverage")
    S.save(P.fig04a_population_coverage(a), "fig04a_population_coverage")
    S.save(P.fig04b_osm_coverage(b), "fig04b_osm_coverage")
    S.save(P.fig04_population_coverage({"a": a, "b": b}), "fig04_population_coverage")


if __name__ == "__main__":
    if "--build" in sys.argv:
        build_rings()
    else:
        plot()
