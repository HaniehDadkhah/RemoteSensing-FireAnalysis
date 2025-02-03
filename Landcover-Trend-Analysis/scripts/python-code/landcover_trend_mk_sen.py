"# Python Script for Landcover Trend Analysis" 
import os
import geopandas as gpd
import rasterio
from rasterio.mask import mask
import numpy as np
import pandas as pd
import pymannkendall as mk
import matplotlib.pyplot as plt
from scipy.stats import linregress
from matplotlib.lines import Line2D

# =========================== PATHS AND DIRECTORIES ===========================
# Paths to input data
tiff_dir = r""path", "to", "MODIS-LULC""
shapefile_path = r"path", "to", "Campania_Provinces.shp"

# Paths to output data
output_excel = os.path.join(tiff_dir, "landcover_pixel_area_summary.xlsx")
trend_output_excel = os.path.join(tiff_dir, "landcover_trend_analysis.xlsx")
selected_plot_dir = os.path.join(tiff_dir, "Selected_Class_Plots")
os.makedirs(selected_plot_dir, exist_ok=True)

# =========================== LAND COVER CLASSES ==============================
land_cover_classes = {
    0: "Water Bodies",
    1: "Grasslands",
    2: "Shrublands",
    3: "Broadleaf Croplands",
    4: "Grassy Woodlands",
    5: "Evergreen Broadleaf Forests",
    6: "Deciduous Broadleaf Forests",
    7: "Evergreen Needleleaf Forests",
    8: "Deciduous Needleleaf Forests",
    9: "Non-Vegetated Lands",
    10: "Urban and Built-up Lands"
}

# Define color mapping for selected land cover classes
color_mapping = {
    "Grasslands": "yellow",
    "Grassy Woodlands": "orange",
    "Deciduous Broadleaf Forests": "green"
}

# =========================== CUSTOM SLOPE LABEL POSITIONS ====================
custom_label_positions = {
    "Avellino": {
        "Grasslands": [-5.5, 120],
        "Grassy Woodlands": [-5, -160],
        "Deciduous Broadleaf Forests": [-5, 80],
    },
    "Benevento": {
        "Grasslands": [-5.5, 100],
        "Grassy Woodlands": [-5.5, -160],
        "Deciduous Broadleaf Forests": [-5, 60],
    },
    "Napoli": {
        "Grasslands": [-5, -30],
        "Grassy Woodlands": [-5, 15],
        "Deciduous Broadleaf Forests": [-5, 20],
    },
    "Salerno": {
        "Grasslands": [-6, 160],
        "Grassy Woodlands": [-6, 180],
        "Deciduous Broadleaf Forests": [-6, 190],
    },
    "Caserta": {
        "Grasslands": [-6, 80],
        "Grassy Woodlands": [-5, 90],
        "Deciduous Broadleaf Forests": [-5, 60],
    },
}

# =========================== STEP 1: AREA EXTRACTION =========================
def extract_landcover_area():
    print("Extracting land cover area...")
    shapefile = gpd.read_file(shapefile_path)
    with rasterio.open(os.path.join(tiff_dir, "LC_Type3_500m_2001.tif")) as src:
        raster_crs = src.crs
    shapefile = shapefile.to_crs(raster_crs)

    results = []
    for _, row in shapefile.iterrows():
        region_name = row["NAME_2"]
        geometry = [row["geometry"]]
        print(f"Processing region: {region_name}")

        for year in range(2001, 2021):
            raster_file = os.path.join(tiff_dir, f"LC_Type3_500m_{year}.tif")
            if not os.path.exists(raster_file):
                print(f"Raster file not found for year {year}. Skipping...")
                continue

            try:
                with rasterio.open(raster_file) as src:
                    masked, _ = mask(src, geometry, crop=True)
                    data = masked[0]

                unique, counts = np.unique(data[data != 255], return_counts=True)  # Exclude no-data (255)
                pixel_counts = dict(zip(unique, counts))

                row_data = {"Region": region_name, "Year": year}
                for land_cover, class_name in land_cover_classes.items():
                    pixel_count = pixel_counts.get(land_cover, 0)
                    area_sqkm = pixel_count * 0.25  # Convert pixels to sq. km
                    row_data[f"{class_name} Pixels"] = pixel_count
                    row_data[f"{class_name} Area (sq. km)"] = round(area_sqkm, 4)
                results.append(row_data)
            except Exception as e:
                print(f"Error processing file {raster_file}: {e}")

    results_df = pd.DataFrame(results)
    results_df.to_excel(output_excel, index=False)
    print(f"Area data saved to {output_excel}")
    return results_df

# =========================== STEP 2: TREND ANALYSIS ==========================
def perform_trend_analysis(results_df):
    print("Performing trend analysis...")
    trend_results = []
    for region, group in results_df.groupby("Region"):
        print(f"Processing region: {region}")

        for lc_class in land_cover_classes.values():
            area_col = f"{lc_class} Area (sq. km)"
            trend_data = group[["Year", area_col]].dropna()

            if trend_data.empty or len(trend_data) < 2:
                continue

            mk_result = mk.original_test(trend_data[area_col])
            sen_slope = mk.sens_slope(trend_data[area_col])

            significance = "**" if mk_result.p < 0.01 else "*" if mk_result.p < 0.05 else ""
            trend_results.append({
                "Region": region,
                "Land Cover Type": lc_class,
                "Mann-Kendall Tau": round(mk_result.Tau, 4),
                "P-Value": round(mk_result.p, 4),
                "Trend": mk_result.trend,
                "Sen's Slope (sq. km/year)": round(sen_slope.slope, 4),
                "Significance": significance
            })

    trend_results_df = pd.DataFrame(trend_results)
    trend_results_df.to_excel(trend_output_excel, index=False)
    print(f"Trend analysis results saved to {trend_output_excel}")
    return trend_results_df

# =========================== STEP 3: PLOT GENERATION =========================
def generate_plots(results_df):
    print("Generating plots with slopes for selected land cover classes...")
    selected_classes = ["Grasslands", "Grassy Woodlands", "Deciduous Broadleaf Forests"]

    for region, group in results_df.groupby("Region"):
        plt.figure(figsize=(12, 8))
        plt.title(region, fontsize=30, fontname="Arial", loc="left", pad=20)

        max_area = 0

        for lc_class in selected_classes:
            area_col = f"{lc_class} Area (sq. km)"
            trend_data = group[["Year", area_col]].dropna()

            if trend_data.empty:
                continue

            mk_result = mk.original_test(trend_data[area_col])
            slope, intercept, _, _, _ = linregress(trend_data["Year"], trend_data[area_col])
            max_area = max(max_area, trend_data[area_col].max())

            # Plot scatter points
            plt.scatter(trend_data["Year"], trend_data[area_col], alpha=1, s=80,
                        label=lc_class, color=color_mapping[lc_class])

            # Plot trend line
            plt.plot(trend_data["Year"], slope * trend_data["Year"] + intercept, linestyle="--", linewidth=2,
                     label=f"{lc_class} Trend", color=color_mapping[lc_class])

            # Add slope annotation with custom positioning
            x_shift, y_shift = custom_label_positions.get(region, {}).get(lc_class, [1, 20])
            slope_label_x = trend_data["Year"].iloc[-1] + x_shift
            slope_label_y = slope * slope_label_x + intercept + y_shift
            significance = "**" if mk_result.p < 0.01 else "*" if mk_result.p < 0.05 else ""
            slope_label = f"{round(slope, 2)} km²/year {significance}"
            plt.text(
                slope_label_x,
                slope_label_y,
                slope_label,
                fontsize=26,
                fontname="Arial",
                color="black"
            )

        plt.ylim(0, max_area * 1.1)
        plt.xlabel("Time(Year)", fontsize=30, fontname="Arial", labelpad=15)
        plt.ylabel("Area Coverage (km²)", fontsize=30, fontname="Arial", labelpad=15)
        plt.xticks(ticks=np.arange(2001, 2021, 2), fontsize=28, fontname="Arial", rotation=45)
        plt.yticks(fontsize=28, fontname="Arial")
                # Customize grid lines
        plt.grid(
            which='major',  # Major grid lines
            linestyle='-',  # Solid line style
            linewidth=0.5,  # Thinner grid lines
            color='lightgray',   # Light gray color
            alpha=0.5       # Semi-transparent grid lines
        )

        plt.tight_layout()
        plt.grid(True)
        plt.tight_layout()

        output_plot = os.path.join(selected_plot_dir, f"{region}_LandCover_Trend_with_Slopes.svg")
        plt.savefig(output_plot, dpi=600, bbox_inches="tight")
        plt.close()
        print(f"Plot saved to {output_plot}")

# =========================== MAIN PROGRAM ====================================
if __name__ == "__main__":
    results_df = extract_landcover_area()
    trend_results_df = perform_trend_analysis(results_df)
    generate_plots(results_df)