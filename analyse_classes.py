#!/usr/bin/env python3
"""
analyse_classes.py — Extract and reconcile crop/land-cover class names across all map datasets.

Outputs:
  crop_classification_hierarchy.json — Hierarchical classification with cross-dataset mapping.

Usage:
  python3 analyse_classes.py
"""

import json, os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# UNIFIED HIERARCHICAL CLASSIFICATION
# =============================================================================
# 4-level hierarchy:
#   L0: Land surface type (Cropland, Forest, Grassland, Water, Urban, ...)
#   L1: Crop category (Cereals, Oilseeds, Legumes, Root Crops, ...)
#   L2: Crop type (Wheat, Barley, Maize, ...)
#   L3: Variant (Winter Wheat, Spring Wheat, Durum Wheat, ...)
#
# Additional attributes:
#   duration: "annual" | "perennial" | "biennial" — crop lifecycle duration
#
# Each level has a canonical English name and a suggested color.

HIERARCHY = {
    "L0": {
        "Cropland":          {"color": "#f5c71a", "description": "Actively cultivated agricultural land"},
        "Grassland":         {"color": "#7cfc00", "description": "Permanent and temporary grass, pastures, meadows"},
        "Forest":            {"color": "#006400", "description": "Tree-covered land (native and plantation)"},
        "Shrubland":         {"color": "#9acd32", "description": "Shrubs, bushes, heathland"},
        "Water":             {"color": "#4682b4", "description": "Rivers, lakes, reservoirs, sea"},
        "Urban":             {"color": "#fa0000", "description": "Built-up areas, infrastructure"},
        "Bare":              {"color": "#b4b4b4", "description": "Bare soil, rock, sand, barren land"},
        "Wetland":           {"color": "#0096a0", "description": "Marshes, bogs, peatland"},
        "Snow/Ice":          {"color": "#f0f0f0", "description": "Permanent snow and glaciers"},
        "Fallow":            {"color": "#d2b48c", "description": "Arable land temporarily not in production"},
        "Unknown":           {"color": "#808080", "description": "Unclassified or unknown land cover"},
    },
    "L1": {
        "Cereals":           {"color": "#d4a017", "parent": "Cropland", "duration": "annual"},
        "Oilseeds":          {"color": "#ffa500", "parent": "Cropland", "duration": "annual"},
        "Legumes":           {"color": "#228b22", "parent": "Cropland", "duration": "annual",
                              "note": "Some legumes (clover, lucerne) are perennial but grown as annual crops"},
        "Root Crops":        {"color": "#cd853f", "parent": "Cropland", "duration": "annual",
                              "note": "Biennial plants (beet, carrot) grown as annuals"},
        "Vegetables":        {"color": "#ff6347", "parent": "Cropland", "duration": "annual"},
        "Fruits/Orchards":   {"color": "#9370db", "parent": "Cropland", "duration": "perennial"},
        "Vineyards":         {"color": "#722f72", "parent": "Cropland", "duration": "perennial"},
        "Industrial Crops":  {"color": "#9acd32", "parent": "Cropland", "duration": "annual"},
        "Fodder Crops":      {"color": "#90ee90", "parent": "Cropland", "duration": "mixed",
                              "note": "Includes both annual fodder (ryegrass) and perennial (grass leys)"},
        "Flowers":           {"color": "#ff69b4", "parent": "Cropland", "duration": "annual"},
        "Mixed/Other Crops": {"color": "#a9a9a9", "parent": "Cropland", "duration": "mixed"},
        "Nursery":           {"color": "#228b22", "parent": "Cropland", "duration": "perennial"},
    },
    "L2": {
        # Cereals — all annual
        "Wheat":       {"color": "#d4a017", "parent": "Cereals", "duration": "annual"},
        "Barley":      {"color": "#ccaa00", "parent": "Cereals", "duration": "annual"},
        "Maize":       {"color": "#f5c71a", "parent": "Cereals", "duration": "annual"},
        "Rye":         {"color": "#b89830", "parent": "Cereals", "duration": "annual"},
        "Oats":        {"color": "#c8a848", "parent": "Cereals", "duration": "annual"},
        "Triticale":   {"color": "#a89030", "parent": "Cereals", "duration": "annual"},
        "Rice":        {"color": "#00bfff", "parent": "Cereals", "duration": "annual"},
        "Sorghum":     {"color": "#b8860b", "parent": "Cereals", "duration": "annual"},
        "Millet":      {"color": "#f4a460", "parent": "Cereals", "duration": "annual"},
        "Spelt":       {"color": "#c0a030", "parent": "Cereals", "duration": "annual"},
        # Oilseeds — all annual
        "Rapeseed":    {"color": "#ffa500", "parent": "Oilseeds", "duration": "annual"},
        "Sunflower":   {"color": "#ffc107", "parent": "Oilseeds", "duration": "annual"},
        "Soy":         {"color": "#cdaa20", "parent": "Oilseeds", "duration": "annual"},
        "Flax/Linseed":{"color": "#e8d44d", "parent": "Oilseeds", "duration": "annual"},
        "Mustard":     {"color": "#eee8aa", "parent": "Oilseeds", "duration": "annual"},
        "Hemp":        {"color": "#9acd32", "parent": "Industrial Crops", "duration": "annual"},
        # Legumes — mostly annual, some perennial
        "Beans":       {"color": "#228b22", "parent": "Legumes", "duration": "annual"},
        "Peas":        {"color": "#00ff7f", "parent": "Legumes", "duration": "annual"},
        "Lentils":     {"color": "#3cb371", "parent": "Legumes", "duration": "annual"},
        "Chickpea":    {"color": "#556b2f", "parent": "Legumes", "duration": "annual"},
        "Lupin":       {"color": "#00fa9a", "parent": "Legumes", "duration": "annual"},
        "Clover":      {"color": "#00cd66", "parent": "Legumes", "duration": "perennial",
                        "note": "Short-lived perennial (2-3 years), often grown as annual ley"},
        "Lucerne":     {"color": "#2e8b57", "parent": "Legumes", "duration": "perennial",
                        "note": "Perennial (3-5+ years), major forage legume"},
        # Root crops — annual/biennial grown as annual
        "Potato":      {"color": "#cd853f", "parent": "Root Crops", "duration": "annual"},
        "Sugar Beet":  {"color": "#deb887", "parent": "Root Crops", "duration": "annual",
                        "note": "Biennial plant grown as annual for sugar"},
        "Carrot":      {"color": "#ff8c00", "parent": "Root Crops", "duration": "annual",
                        "note": "Biennial plant grown as annual for root harvest"},
        "Turnip":      {"color": "#dda0dd", "parent": "Root Crops", "duration": "annual"},
        # Vegetables — annual
        "Onion":       {"color": "#daa520", "parent": "Vegetables", "duration": "annual"},
        "Tomato":      {"color": "#ff4500", "parent": "Vegetables", "duration": "annual"},
        "Lettuce":     {"color": "#90ee90", "parent": "Vegetables", "duration": "annual"},
        "Cabbage":     {"color": "#66cdaa", "parent": "Vegetables", "duration": "annual",
                        "note": "Biennial plant grown as annual"},
        "Spinach":     {"color": "#2e8b57", "parent": "Vegetables", "duration": "annual"},
        # Fruits — all perennial
        "Apple":       {"color": "#ff6b6b", "parent": "Fruits/Orchards", "duration": "perennial"},
        "Pear":        {"color": "#c5e17a", "parent": "Fruits/Orchards", "duration": "perennial"},
        "Cherry":      {"color": "#dc143c", "parent": "Fruits/Orchards", "duration": "perennial"},
        "Berry":       {"color": "#9400d3", "parent": "Fruits/Orchards", "duration": "perennial"},
        "Strawberry":  {"color": "#ff4040", "parent": "Fruits/Orchards", "duration": "perennial",
                        "note": "Short-lived perennial (2-3 years), often replanted annually"},
    },
}

# =============================================================================
# DATASET CLASS DEFINITIONS
# =============================================================================
# Each dataset: { code: { name, color, L0, L1, L2, L3 (optional) } }

DATASETS = {}

# ---- 1. CROME (England) ----
DATASETS["crome"] = {
    "meta": {
        "label": "England CROME", "country": "England",
        "source": "Rural Payments Agency / Defra",
        "resolution": "~5m (vector parcels)", "type": "vector",
        "years": [2020, 2021, 2022, 2023, 2024],
        "url": "https://environment.data.gov.uk/"
    },
    "classes": {
        # Cereals
        "AC66": {"name": "Winter Wheat",      "color": "#d4a017", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat",    "L3": "Winter Wheat"},
        "AC32": {"name": "Spring Wheat",      "color": "#f0d000", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat",    "L3": "Spring Wheat"},
        "AC63": {"name": "Winter Barley",     "color": "#ccaa00", "L0": "Cropland", "L1": "Cereals", "L2": "Barley",   "L3": "Winter Barley"},
        "AC01": {"name": "Spring Barley",     "color": "#e6b800", "L0": "Cropland", "L1": "Cereals", "L2": "Barley",   "L3": "Spring Barley"},
        "AC19": {"name": "Spring Oats",       "color": "#e8c840", "L0": "Cropland", "L1": "Cereals", "L2": "Oats",     "L3": "Spring Oats"},
        "AC65": {"name": "Winter Oats",       "color": "#c9a830", "L0": "Cropland", "L1": "Cereals", "L2": "Oats",     "L3": "Winter Oats"},
        "AC24": {"name": "Spring Rye",        "color": "#d4aa50", "L0": "Cropland", "L1": "Cereals", "L2": "Rye",      "L3": "Spring Rye"},
        "AC68": {"name": "Winter Rye",        "color": "#b89830", "L0": "Cropland", "L1": "Cereals", "L2": "Rye",      "L3": "Winter Rye"},
        "AC30": {"name": "Spring Triticale",  "color": "#c8a848", "L0": "Cropland", "L1": "Cereals", "L2": "Triticale","L3": "Spring Triticale"},
        "AC69": {"name": "Winter Triticale",  "color": "#a89030", "L0": "Cropland", "L1": "Cereals", "L2": "Triticale","L3": "Winter Triticale"},
        "AC17": {"name": "Maize",             "color": "#f5c71a", "L0": "Cropland", "L1": "Cereals", "L2": "Maize"},
        "AC18": {"name": "Millet",            "color": "#f4a460", "L0": "Cropland", "L1": "Cereals", "L2": "Millet"},
        "AC92": {"name": "Sorghum",           "color": "#b8860b", "L0": "Cropland", "L1": "Cereals", "L2": "Sorghum"},
        "AC05": {"name": "Buckwheat",         "color": "#bc8f8f", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat",    "L3": "Buckwheat"},
        "AC100":{"name": "Italian Ryegrass",  "color": "#98fb98", "L0": "Cropland", "L1": "Fodder Crops", "L2": "Wheat"},
        # Oilseeds
        "AC36": {"name": "Spring Oilseed",    "color": "#ffe135", "L0": "Cropland", "L1": "Oilseeds", "L2": "Rapeseed", "L3": "Spring Rapeseed"},
        "AC67": {"name": "Winter Oilseed",    "color": "#ffd700", "L0": "Cropland", "L1": "Oilseeds", "L2": "Rapeseed", "L3": "Winter Rapeseed"},
        "AC16": {"name": "Spring Linseed",    "color": "#e8d44d", "L0": "Cropland", "L1": "Oilseeds", "L2": "Flax/Linseed", "L3": "Spring Linseed"},
        "AC64": {"name": "Winter Linseed",    "color": "#d4c030", "L0": "Cropland", "L1": "Oilseeds", "L2": "Flax/Linseed", "L3": "Winter Linseed"},
        "AC88": {"name": "Sunflower",         "color": "#ffa500", "L0": "Cropland", "L1": "Oilseeds", "L2": "Sunflower"},
        "AC37": {"name": "Brown Mustard",     "color": "#f0e68c", "L0": "Cropland", "L1": "Oilseeds", "L2": "Mustard"},
        "AC38": {"name": "Mustard",           "color": "#eee8aa", "L0": "Cropland", "L1": "Oilseeds", "L2": "Mustard"},
        "AC04": {"name": "Borage",            "color": "#d2691e", "L0": "Cropland", "L1": "Oilseeds"},
        # Root/tuber
        "AC44": {"name": "Potato",            "color": "#cd853f", "L0": "Cropland", "L1": "Root Crops", "L2": "Potato"},
        "AC03": {"name": "Beet",              "color": "#e07020", "L0": "Cropland", "L1": "Root Crops", "L2": "Sugar Beet"},
        "AC07": {"name": "Carrot",            "color": "#ff8c00", "L0": "Cropland", "L1": "Root Crops", "L2": "Carrot"},
        "AC23": {"name": "Parsnips",          "color": "#ffdab9", "L0": "Cropland", "L1": "Root Crops"},
        "AC35": {"name": "Turnip",            "color": "#dda0dd", "L0": "Cropland", "L1": "Root Crops", "L2": "Turnip"},
        "AC41": {"name": "Radish",            "color": "#ff7f7f", "L0": "Cropland", "L1": "Root Crops"},
        # Vegetables
        "AC20": {"name": "Onions",            "color": "#daa520", "L0": "Cropland", "L1": "Vegetables", "L2": "Onion"},
        "AC45": {"name": "Tomato",            "color": "#ff4500", "L0": "Cropland", "L1": "Vegetables", "L2": "Tomato"},
        "AC15": {"name": "Lettuce",           "color": "#90ee90", "L0": "Cropland", "L1": "Vegetables", "L2": "Lettuce"},
        "AC34": {"name": "Spring Cabbage",    "color": "#66cdaa", "L0": "Cropland", "L1": "Vegetables", "L2": "Cabbage"},
        "AC70": {"name": "Winter Cabbage",    "color": "#5f9ea0", "L0": "Cropland", "L1": "Vegetables", "L2": "Cabbage"},
        "AC26": {"name": "Spinach",           "color": "#2e8b57", "L0": "Cropland", "L1": "Vegetables", "L2": "Spinach"},
        "AC22": {"name": "Parsley",           "color": "#3cb371", "L0": "Cropland", "L1": "Vegetables"},
        "AC09": {"name": "Chicory",           "color": "#8fbc8f", "L0": "Cropland", "L1": "Vegetables"},
        "AC50": {"name": "Squash",            "color": "#ff8c69", "L0": "Cropland", "L1": "Vegetables"},
        "AC52": {"name": "Siam Pumpkin",      "color": "#ffa07a", "L0": "Cropland", "L1": "Vegetables"},
        # Industrial / misc crops
        "AC14": {"name": "Hemp",              "color": "#9acd32", "L0": "Cropland", "L1": "Industrial Crops", "L2": "Hemp"},
        "AC06": {"name": "Canary Seed",       "color": "#deb887", "L0": "Cropland", "L1": "Cereals"},
        "AC71": {"name": "Coriander",         "color": "#7fff00", "L0": "Cropland", "L1": "Industrial Crops"},
        "AC72": {"name": "Corn Gromwell",     "color": "#6b8e23", "L0": "Cropland", "L1": "Industrial Crops"},
        "AC74": {"name": "Phacelia",          "color": "#8a2be2", "L0": "Cropland", "L1": "Industrial Crops"},
        "AC81": {"name": "Poppy",             "color": "#ff1493", "L0": "Cropland", "L1": "Industrial Crops"},
        # Flowers
        "AC10": {"name": "Daffodil",          "color": "#ffff00", "L0": "Cropland", "L1": "Flowers"},
        "AC90": {"name": "Gladioli",          "color": "#ff69b4", "L0": "Cropland", "L1": "Flowers"},
        "AC94": {"name": "Sweet William",     "color": "#c71585", "L0": "Cropland", "L1": "Flowers"},
        # Legumes
        "LG01": {"name": "Chickpea",          "color": "#556b2f", "L0": "Cropland", "L1": "Legumes", "L2": "Chickpea"},
        "LG02": {"name": "Fenugreek",         "color": "#6b8e23", "L0": "Cropland", "L1": "Legumes"},
        "LG03": {"name": "Spring Field Beans","color": "#228b22", "L0": "Cropland", "L1": "Legumes", "L2": "Beans", "L3": "Spring Field Beans"},
        "LG20": {"name": "Winter Field Beans","color": "#006400", "L0": "Cropland", "L1": "Legumes", "L2": "Beans", "L3": "Winter Field Beans"},
        "LG04": {"name": "Green Beans",       "color": "#32cd32", "L0": "Cropland", "L1": "Legumes", "L2": "Beans"},
        "LG06": {"name": "Lupins",            "color": "#00fa9a", "L0": "Cropland", "L1": "Legumes", "L2": "Lupin"},
        "LG07": {"name": "Spring Peas",       "color": "#00ff7f", "L0": "Cropland", "L1": "Legumes", "L2": "Peas", "L3": "Spring Peas"},
        "LG21": {"name": "Winter Peas",       "color": "#008b45", "L0": "Cropland", "L1": "Legumes", "L2": "Peas", "L3": "Winter Peas"},
        "LG08": {"name": "Soya",              "color": "#3cb371", "L0": "Cropland", "L1": "Legumes", "L2": "Beans"},
        "LG09": {"name": "Cowpea",            "color": "#20b2aa", "L0": "Cropland", "L1": "Legumes", "L2": "Beans"},
        "LG11": {"name": "Lucerne",           "color": "#2e8b57", "L0": "Cropland", "L1": "Legumes", "L2": "Lucerne"},
        "LG13": {"name": "Sainfoin",          "color": "#66cdaa", "L0": "Cropland", "L1": "Legumes"},
        "LG14": {"name": "Clover",            "color": "#00cd66", "L0": "Cropland", "L1": "Legumes", "L2": "Clover"},
        "LG15": {"name": "Mixed Leguminous 1","color": "#4f7942", "L0": "Cropland", "L1": "Legumes"},
        "LG16": {"name": "Mixed Leguminous 2","color": "#3a6b35", "L0": "Cropland", "L1": "Legumes"},
        # Fruit, etc
        "AC27": {"name": "Strawberry",        "color": "#ff6347", "L0": "Cropland", "L1": "Fruits/Orchards", "L2": "Strawberry"},
        "TC01": {"name": "Perennial Crops/Trees","color":"#006400","L0": "Cropland", "L1": "Fruits/Orchards"},
        "NU01": {"name": "Nursery Crops",     "color": "#228b22", "L0": "Cropland", "L1": "Nursery"},
        # Grassland
        "PG01": {"name": "Grass",             "color": "#7cfc00", "L0": "Grassland"},
        "HE02": {"name": "Heathland/Bracken", "color": "#9370db", "L0": "Shrubland"},
        "HEAT": {"name": "Heather",           "color": "#8b668b", "L0": "Shrubland"},
        # Other
        "FA01": {"name": "Fallow Land",       "color": "#f5deb3", "L0": "Fallow"},
        "CA02": {"name": "Cover Crop",        "color": "#bdb76b", "L0": "Cropland", "L1": "Fodder Crops"},
        "SR01": {"name": "Short Rotation Coppice","color":"#8b4513","L0": "Forest"},
        "WO12": {"name": "Trees/Scrubs/Hedgerows","color":"#2f4f4f","L0": "Forest"},
        "NA01": {"name": "Non-vegetated Land","color": "#a9a9a9", "L0": "Bare"},
        "WA00": {"name": "Water",             "color": "#4682b4", "L0": "Water"},
        # Mixed
        "AC58": {"name": "Mixed Crop 1",      "color": "#d2b48c", "L0": "Cropland", "L1": "Mixed/Other Crops"},
        "AC59": {"name": "Mixed Crop 2",      "color": "#c4a882", "L0": "Cropland", "L1": "Mixed/Other Crops"},
        "AC60": {"name": "Mixed Crop 3",      "color": "#b69a76", "L0": "Cropland", "L1": "Mixed/Other Crops"},
        "AC61": {"name": "Mixed Crop 4",      "color": "#a88c6a", "L0": "Cropland", "L1": "Mixed/Other Crops"},
        "AC62": {"name": "Mixed Crop 5",      "color": "#9a7e5e", "L0": "Cropland", "L1": "Mixed/Other Crops"},
        "AC00": {"name": "Unknown/Mixed Veg", "color": "#808080", "L0": "Unknown"},
    }
}

# ---- 2. JRC EU Crop Map ----
DATASETS["jrc-eucropmap"] = {
    "meta": {
        "label": "JRC EU Crop Map", "country": "EU-27 + UK (2018)",
        "source": "European Commission Joint Research Centre",
        "resolution": "10m (Sentinel-2)", "type": "raster",
        "years": [2018, 2022],
        "url": "https://jeodpp.jrc.ec.europa.eu/"
    },
    "classes": {
        "1":  {"name": "Common wheat",      "color": "#a57000", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat", "L3": "Common Wheat"},
        "2":  {"name": "Durum wheat",        "color": "#6e4b00", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat", "L3": "Durum Wheat"},
        "3":  {"name": "Barley",             "color": "#ff00ff", "L0": "Cropland", "L1": "Cereals", "L2": "Barley"},
        "4":  {"name": "Rye",                "color": "#800080", "L0": "Cropland", "L1": "Cereals", "L2": "Rye"},
        "5":  {"name": "Oats",               "color": "#ff80ff", "L0": "Cropland", "L1": "Cereals", "L2": "Oats"},
        "6":  {"name": "Maize",              "color": "#ffff00", "L0": "Cropland", "L1": "Cereals", "L2": "Maize"},
        "7":  {"name": "Rice",               "color": "#00bfff", "L0": "Cropland", "L1": "Cereals", "L2": "Rice"},
        "8":  {"name": "Triticale",          "color": "#d0d0d0", "L0": "Cropland", "L1": "Cereals", "L2": "Triticale"},
        "9":  {"name": "Other cereals",      "color": "#c8a080", "L0": "Cropland", "L1": "Cereals"},
        "10": {"name": "Potatoes",           "color": "#c87000", "L0": "Cropland", "L1": "Root Crops", "L2": "Potato"},
        "11": {"name": "Sugar beet",         "color": "#ff00ff", "L0": "Cropland", "L1": "Root Crops", "L2": "Sugar Beet"},
        "12": {"name": "Other root crops",   "color": "#00a000", "L0": "Cropland", "L1": "Root Crops"},
        "13": {"name": "Other non-perm. industrial crops","color":"#008000","L0":"Cropland","L1":"Industrial Crops"},
        "14": {"name": "Sunflower",          "color": "#ffff80", "L0": "Cropland", "L1": "Oilseeds", "L2": "Sunflower"},
        "15": {"name": "Rape and turnip rape","color":"#c8ff00", "L0": "Cropland", "L1": "Oilseeds", "L2": "Rapeseed"},
        "16": {"name": "Soya",               "color": "#006000", "L0": "Cropland", "L1": "Legumes", "L2": "Beans"},
        "17": {"name": "Dry pulses",         "color": "#ff8000", "L0": "Cropland", "L1": "Legumes"},
        "18": {"name": "Fodder crops",       "color": "#ffc0ff", "L0": "Cropland", "L1": "Fodder Crops"},
        "19": {"name": "Bare arable land",   "color": "#606040", "L0": "Fallow"},
        "20": {"name": "Woodland and Shrubland (incl. permanent crops)","color":"#40c080","L0":"Forest"},
        "21": {"name": "Grasslands",         "color": "#c0ffc0", "L0": "Grassland"},
    }
}

# ---- 3. Germany (DLR CropTypes) ----
DATASETS["germany"] = {
    "meta": {
        "label": "Germany DLR CropTypes", "country": "Germany",
        "source": "DLR (German Aerospace Center)",
        "resolution": "10m (Sentinel-1)", "type": "raster",
        "years": [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
        "url": "https://geoservice.dlr.de/"
    },
    "classes": {
        "1":  {"name": "Winter wheat",       "color": "#0000ff", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat", "L3": "Winter Wheat"},
        "2":  {"name": "Winter barley",      "color": "#00a0ff", "L0": "Cropland", "L1": "Cereals", "L2": "Barley", "L3": "Winter Barley"},
        "3":  {"name": "Winter rye",         "color": "#ff00ff", "L0": "Cropland", "L1": "Cereals", "L2": "Rye", "L3": "Winter Rye"},
        "4":  {"name": "Winter cereals",     "color": "#a000ff", "L0": "Cropland", "L1": "Cereals"},
        "5":  {"name": "Spring wheat",       "color": "#0080ff", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat", "L3": "Spring Wheat"},
        "6":  {"name": "Spring barley",      "color": "#00c0ff", "L0": "Cropland", "L1": "Cereals", "L2": "Barley", "L3": "Spring Barley"},
        "7":  {"name": "Spring oats",        "color": "#00e0ff", "L0": "Cropland", "L1": "Cereals", "L2": "Oats", "L3": "Spring Oats"},
        "8":  {"name": "Maize",              "color": "#ffff00", "L0": "Cropland", "L1": "Cereals", "L2": "Maize"},
        "9":  {"name": "Beans-lupins-peas",  "color": "#ff8000", "L0": "Cropland", "L1": "Legumes"},
        "10": {"name": "Potatoes",           "color": "#804000", "L0": "Cropland", "L1": "Root Crops", "L2": "Potato"},
        "11": {"name": "Sugar beet",         "color": "#ff0080", "L0": "Cropland", "L1": "Root Crops", "L2": "Sugar Beet"},
        "12": {"name": "Rapeseed",           "color": "#c0ff00", "L0": "Cropland", "L1": "Oilseeds", "L2": "Rapeseed"},
        "13": {"name": "Clover",             "color": "#00c000", "L0": "Cropland", "L1": "Legumes", "L2": "Clover"},
        "14": {"name": "Arable grass",       "color": "#80ff00", "L0": "Grassland"},
        "15": {"name": "Permanent grass",    "color": "#00ff00", "L0": "Grassland"},
        "16": {"name": "Vineyards",          "color": "#800080", "L0": "Cropland", "L1": "Vineyards"},
        "17": {"name": "Fruit trees",        "color": "#ff0000", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "18": {"name": "Hops",               "color": "#008080", "L0": "Cropland", "L1": "Industrial Crops"},
        "19": {"name": "Other agricultural use","color":"#808080","L0": "Cropland", "L1": "Mixed/Other Crops"},
    }
}

# ---- 4. USDA Cropland Data Layer ----
DATASETS["usda-cdl"] = {
    "meta": {
        "label": "USDA Cropland Data Layer", "country": "USA",
        "source": "USDA NASS",
        "resolution": "30m (Landsat + Sentinel)", "type": "raster",
        "years": [2020, 2021, 2022, 2023],
        "url": "https://nassgeodata.gmu.edu/CropScape/"
    },
    "classes": {
        "1":   {"name": "Corn",              "color": "#ffd300", "L0": "Cropland", "L1": "Cereals", "L2": "Maize"},
        "2":   {"name": "Cotton",            "color": "#ff2626", "L0": "Cropland", "L1": "Industrial Crops"},
        "3":   {"name": "Rice",              "color": "#00a8e5", "L0": "Cropland", "L1": "Cereals", "L2": "Rice"},
        "4":   {"name": "Sorghum",           "color": "#ff9e0a", "L0": "Cropland", "L1": "Cereals", "L2": "Sorghum"},
        "5":   {"name": "Soybeans",          "color": "#267000", "L0": "Cropland", "L1": "Legumes", "L2": "Beans"},
        "6":   {"name": "Sunflower",         "color": "#ffff00", "L0": "Cropland", "L1": "Oilseeds", "L2": "Sunflower"},
        "10":  {"name": "Peanuts",           "color": "#70a800", "L0": "Cropland", "L1": "Legumes"},
        "11":  {"name": "Tobacco",           "color": "#00af49", "L0": "Cropland", "L1": "Industrial Crops"},
        "12":  {"name": "Sweet Corn",        "color": "#dda50a", "L0": "Cropland", "L1": "Cereals", "L2": "Maize"},
        "13":  {"name": "Pop or Orn Corn",   "color": "#dda50a", "L0": "Cropland", "L1": "Cereals", "L2": "Maize"},
        "21":  {"name": "Barley",            "color": "#e2007c", "L0": "Cropland", "L1": "Cereals", "L2": "Barley"},
        "22":  {"name": "Durum Wheat",       "color": "#896054", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat", "L3": "Durum Wheat"},
        "23":  {"name": "Spring Wheat",      "color": "#d8b56b", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat", "L3": "Spring Wheat"},
        "24":  {"name": "Winter Wheat",      "color": "#a57000", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat", "L3": "Winter Wheat"},
        "25":  {"name": "Other Small Grains","color": "#d69ebc", "L0": "Cropland", "L1": "Cereals"},
        "26":  {"name": "Dbl Crop WinWht/Soybeans","color":"#707000","L0":"Cropland","L1":"Cereals","L2":"Wheat"},
        "27":  {"name": "Rye",               "color": "#ac007c", "L0": "Cropland", "L1": "Cereals", "L2": "Rye"},
        "28":  {"name": "Oats",              "color": "#a05989", "L0": "Cropland", "L1": "Cereals", "L2": "Oats"},
        "29":  {"name": "Millet",            "color": "#d6a0d6", "L0": "Cropland", "L1": "Cereals", "L2": "Millet"},
        "30":  {"name": "Speltz",            "color": "#d1ff00", "L0": "Cropland", "L1": "Cereals", "L2": "Spelt"},
        "31":  {"name": "Canola",            "color": "#e5007c", "L0": "Cropland", "L1": "Oilseeds", "L2": "Rapeseed"},
        "32":  {"name": "Flaxseed",          "color": "#b29b70", "L0": "Cropland", "L1": "Oilseeds", "L2": "Flax/Linseed"},
        "33":  {"name": "Safflower",         "color": "#f5ba9f", "L0": "Cropland", "L1": "Oilseeds"},
        "34":  {"name": "Rape Seed",         "color": "#d6d600", "L0": "Cropland", "L1": "Oilseeds", "L2": "Rapeseed"},
        "35":  {"name": "Mustard",           "color": "#d1ff00", "L0": "Cropland", "L1": "Oilseeds", "L2": "Mustard"},
        "36":  {"name": "Alfalfa",           "color": "#ff9e0a", "L0": "Cropland", "L1": "Legumes", "L2": "Lucerne"},
        "37":  {"name": "Other Hay/Non Alfalfa","color":"#a5f28c","L0":"Grassland"},
        "42":  {"name": "Dry Beans",         "color": "#a800e5", "L0": "Cropland", "L1": "Legumes", "L2": "Beans"},
        "43":  {"name": "Potatoes",          "color": "#a50000", "L0": "Cropland", "L1": "Root Crops", "L2": "Potato"},
        "44":  {"name": "Other Crops",       "color": "#702600", "L0": "Cropland", "L1": "Mixed/Other Crops"},
        "45":  {"name": "Sugarcane",         "color": "#00af49", "L0": "Cropland", "L1": "Industrial Crops"},
        "46":  {"name": "Sweet Potatoes",    "color": "#af7000", "L0": "Cropland", "L1": "Root Crops", "L2": "Potato"},
        "47":  {"name": "Misc Vegs & Fruits","color":"#b5704c","L0":"Cropland","L1":"Vegetables"},
        "48":  {"name": "Watermelons",       "color": "#ff2626", "L0": "Cropland", "L1": "Vegetables"},
        "49":  {"name": "Onions",            "color": "#ff9e0a", "L0": "Cropland", "L1": "Vegetables", "L2": "Onion"},
        "50":  {"name": "Cucumbers",         "color": "#267000", "L0": "Cropland", "L1": "Vegetables"},
        "51":  {"name": "Chick Peas",        "color": "#f5ba9f", "L0": "Cropland", "L1": "Legumes", "L2": "Chickpea"},
        "52":  {"name": "Lentils",           "color": "#b29b70", "L0": "Cropland", "L1": "Legumes", "L2": "Lentils"},
        "53":  {"name": "Peas",              "color": "#00af49", "L0": "Cropland", "L1": "Legumes", "L2": "Peas"},
        "54":  {"name": "Tomatoes",          "color": "#ff2626", "L0": "Cropland", "L1": "Vegetables", "L2": "Tomato"},
        "55":  {"name": "Cranberries",       "color": "#e80000", "L0": "Cropland", "L1": "Fruits/Orchards", "L2": "Berry"},
        "56":  {"name": "Hops",              "color": "#b2dda5", "L0": "Cropland", "L1": "Industrial Crops"},
        "57":  {"name": "Herbs",             "color": "#00af49", "L0": "Cropland", "L1": "Industrial Crops"},
        "58":  {"name": "Clover/Wildflowers","color":"#7cd3ff","L0":"Grassland"},
        "59":  {"name": "Sod/Grass Seed",    "color": "#e8bfff", "L0": "Grassland"},
        "60":  {"name": "Switchgrass",       "color": "#afffdd", "L0": "Grassland"},
        "61":  {"name": "Fallow/Idle Cropland","color":"#bfbf77","L0":"Fallow"},
        "63":  {"name": "Forest",            "color": "#93cc93", "L0": "Forest"},
        "64":  {"name": "Shrubland",         "color": "#c6d69e", "L0": "Shrubland"},
        "65":  {"name": "Barren",            "color": "#ccbfa3", "L0": "Bare"},
        "66":  {"name": "Cherries",          "color": "#ff00ff", "L0": "Cropland", "L1": "Fruits/Orchards", "L2": "Cherry"},
        "67":  {"name": "Peaches",           "color": "#ff8eaa", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "68":  {"name": "Apples",            "color": "#ba004f", "L0": "Cropland", "L1": "Fruits/Orchards", "L2": "Apple"},
        "69":  {"name": "Grapes",            "color": "#704489", "L0": "Cropland", "L1": "Vineyards"},
        "72":  {"name": "Citrus",            "color": "#007777", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "74":  {"name": "Pecans",            "color": "#b5b55e", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "75":  {"name": "Almonds",           "color": "#ff6666", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "76":  {"name": "Walnuts",           "color": "#ff6666", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "77":  {"name": "Pears",             "color": "#ffcc66", "L0": "Cropland", "L1": "Fruits/Orchards", "L2": "Pear"},
        "81":  {"name": "Clouds/No Data",    "color": "#d7d7d7", "L0": "Unknown"},
        "82":  {"name": "Developed",         "color": "#d1d1d1", "L0": "Urban"},
        "83":  {"name": "Water",             "color": "#4970a3", "L0": "Water"},
        "87":  {"name": "Wetlands",          "color": "#7cafaf", "L0": "Wetland"},
        "88":  {"name": "Nonag/Undefined",   "color": "#e8ffbf", "L0": "Unknown"},
        "92":  {"name": "Aquaculture",       "color": "#00ffff", "L0": "Water"},
        "111": {"name": "Open Water",        "color": "#4970a3", "L0": "Water"},
        "112": {"name": "Perennial Ice/Snow","color":"#d3e2f9",  "L0": "Snow/Ice"},
        "121": {"name": "Developed/Open Space","color":"#999999","L0":"Urban"},
        "122": {"name": "Developed/Low Intensity","color":"#999999","L0":"Urban"},
        "123": {"name": "Developed/Med Intensity","color":"#999999","L0":"Urban"},
        "124": {"name": "Developed/High Intensity","color":"#999999","L0":"Urban"},
        "131": {"name": "Barren",            "color": "#ccbfa3", "L0": "Bare"},
        "141": {"name": "Deciduous Forest",  "color": "#93cc93", "L0": "Forest"},
        "142": {"name": "Evergreen Forest",  "color": "#006600", "L0": "Forest"},
        "143": {"name": "Mixed Forest",      "color": "#00cc00", "L0": "Forest"},
        "152": {"name": "Shrubland",         "color": "#c6d69e", "L0": "Shrubland"},
        "176": {"name": "Grass/Pasture",     "color": "#e8ffbf", "L0": "Grassland"},
        "190": {"name": "Woody Wetlands",    "color": "#7cafaf", "L0": "Wetland"},
        "195": {"name": "Herbaceous Wetlands","color":"#7cafaf", "L0": "Wetland"},
        "204": {"name": "Pistachios",        "color": "#b5b55e", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "205": {"name": "Triticale",         "color": "#00ff8c", "L0": "Cropland", "L1": "Cereals", "L2": "Triticale"},
        "206": {"name": "Carrots",           "color": "#d69ebc", "L0": "Cropland", "L1": "Root Crops", "L2": "Carrot"},
        "207": {"name": "Asparagus",         "color": "#00af49", "L0": "Cropland", "L1": "Vegetables"},
        "208": {"name": "Garlic",            "color": "#ffd300", "L0": "Cropland", "L1": "Vegetables"},
        "209": {"name": "Cantaloupes",       "color": "#ffd300", "L0": "Cropland", "L1": "Vegetables"},
        "210": {"name": "Prunes",            "color": "#ff6666", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "211": {"name": "Olives",            "color": "#005700", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "212": {"name": "Oranges",           "color": "#ff6800", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "214": {"name": "Broccoli",          "color": "#267000", "L0": "Cropland", "L1": "Vegetables"},
        "216": {"name": "Peppers",           "color": "#ff0000", "L0": "Cropland", "L1": "Vegetables"},
        "217": {"name": "Pomegranates",      "color": "#b5004c", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "219": {"name": "Lettuce",           "color": "#ff9e0a", "L0": "Cropland", "L1": "Vegetables", "L2": "Lettuce"},
        "221": {"name": "Strawberries",      "color": "#ff2626", "L0": "Cropland", "L1": "Fruits/Orchards", "L2": "Strawberry"},
        "222": {"name": "Squash",            "color": "#ffff7c", "L0": "Cropland", "L1": "Vegetables"},
        "224": {"name": "Vetch",             "color": "#267000", "L0": "Cropland", "L1": "Legumes"},
        "225": {"name": "Dbl Crop WinWht/Corn","color":"#c77c54","L0":"Cropland","L1":"Cereals"},
        "227": {"name": "Lettuce",           "color": "#ff9e0a", "L0": "Cropland", "L1": "Vegetables", "L2": "Lettuce"},
        "229": {"name": "Pumpkins",          "color": "#ff6800", "L0": "Cropland", "L1": "Vegetables"},
        "242": {"name": "Blueberries",       "color": "#000099", "L0": "Cropland", "L1": "Fruits/Orchards", "L2": "Berry"},
        "243": {"name": "Cabbage",           "color": "#93cc93", "L0": "Cropland", "L1": "Vegetables", "L2": "Cabbage"},
        "244": {"name": "Cauliflower",       "color": "#c6d69e", "L0": "Cropland", "L1": "Vegetables"},
        "245": {"name": "Celery",            "color": "#e8ffbf", "L0": "Cropland", "L1": "Vegetables"},
        "246": {"name": "Radishes",          "color": "#7cafaf", "L0": "Cropland", "L1": "Root Crops"},
        "247": {"name": "Turnips",           "color": "#d3e2f9", "L0": "Cropland", "L1": "Root Crops", "L2": "Turnip"},
        "248": {"name": "Eggplants",         "color": "#999999", "L0": "Cropland", "L1": "Vegetables"},
        "250": {"name": "Cranberries",       "color": "#e80000", "L0": "Cropland", "L1": "Fruits/Orchards", "L2": "Berry"},
    }
}

# ---- 5. Canada AAFC ----
DATASETS["canada"] = {
    "meta": {
        "label": "Canada AAFC Annual Crop Inventory", "country": "Canada",
        "source": "Agriculture and Agri-Food Canada",
        "resolution": "30m (Landsat/Sentinel)", "type": "raster",
        "years": [2020, 2021, 2022, 2023, 2024],
        "url": "https://open.canada.ca/"
    },
    "classes": {
        "20":  {"name": "Water",             "color": "#3333ff", "L0": "Water"},
        "30":  {"name": "Exposed Land",      "color": "#996666", "L0": "Bare"},
        "34":  {"name": "Urban",             "color": "#cc6699", "L0": "Urban"},
        "35":  {"name": "Greenhouses",       "color": "#e1e1e1", "L0": "Cropland", "L1": "Vegetables"},
        "50":  {"name": "Shrubland",         "color": "#ffff00", "L0": "Shrubland"},
        "80":  {"name": "Wetland",           "color": "#993399", "L0": "Wetland"},
        "110": {"name": "Grassland",         "color": "#cccc00", "L0": "Grassland"},
        "120": {"name": "Agriculture (undiff.)","color":"#cc6600","L0":"Cropland"},
        "122": {"name": "Pasture and Forages","color":"#ffcc33", "L0": "Grassland"},
        "130": {"name": "Too Wet to Seed",   "color": "#7899f6", "L0": "Wetland"},
        "131": {"name": "Fallow",            "color": "#ff9900", "L0": "Fallow"},
        "133": {"name": "Barley",            "color": "#dae31d", "L0": "Cropland", "L1": "Cereals", "L2": "Barley"},
        "136": {"name": "Oats",              "color": "#d1d52b", "L0": "Cropland", "L1": "Cereals", "L2": "Oats"},
        "137": {"name": "Rye",               "color": "#cacd32", "L0": "Cropland", "L1": "Cereals", "L2": "Rye"},
        "139": {"name": "Triticale",         "color": "#b9bc44", "L0": "Cropland", "L1": "Cereals", "L2": "Triticale"},
        "140": {"name": "Wheat",             "color": "#a7b34d", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat"},
        "145": {"name": "Winter Wheat",      "color": "#809769", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat", "L3": "Winter Wheat"},
        "146": {"name": "Spring Wheat",      "color": "#92a55b", "L0": "Cropland", "L1": "Cereals", "L2": "Wheat", "L3": "Spring Wheat"},
        "147": {"name": "Corn",              "color": "#ffff99", "L0": "Cropland", "L1": "Cereals", "L2": "Maize"},
        "153": {"name": "Canola/Rapeseed",   "color": "#d6ff70", "L0": "Cropland", "L1": "Oilseeds", "L2": "Rapeseed"},
        "154": {"name": "Flaxseed",          "color": "#8c8cff", "L0": "Cropland", "L1": "Oilseeds", "L2": "Flax/Linseed"},
        "155": {"name": "Mustard",           "color": "#d6cc00", "L0": "Cropland", "L1": "Oilseeds", "L2": "Mustard"},
        "157": {"name": "Sunflower",         "color": "#315491", "L0": "Cropland", "L1": "Oilseeds", "L2": "Sunflower"},
        "158": {"name": "Soybeans",          "color": "#cc9933", "L0": "Cropland", "L1": "Legumes", "L2": "Beans"},
        "162": {"name": "Peas",              "color": "#8f6c3d", "L0": "Cropland", "L1": "Legumes", "L2": "Peas"},
        "167": {"name": "Beans",             "color": "#82654a", "L0": "Cropland", "L1": "Legumes", "L2": "Beans"},
        "174": {"name": "Lentils",           "color": "#b85900", "L0": "Cropland", "L1": "Legumes", "L2": "Lentils"},
        "177": {"name": "Potatoes",          "color": "#ffcccc", "L0": "Cropland", "L1": "Root Crops", "L2": "Potato"},
        "178": {"name": "Sugarbeets",        "color": "#6f55ca", "L0": "Cropland", "L1": "Root Crops", "L2": "Sugar Beet"},
        "188": {"name": "Orchards",          "color": "#ff6666", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "190": {"name": "Vineyards",         "color": "#7442bd", "L0": "Cropland", "L1": "Vineyards"},
        "193": {"name": "Herbs",             "color": "#ccff05", "L0": "Cropland", "L1": "Industrial Crops"},
        "194": {"name": "Nursery",           "color": "#07f98c", "L0": "Cropland", "L1": "Nursery"},
        "195": {"name": "Buckwheat",         "color": "#00ffcc", "L0": "Cropland", "L1": "Cereals"},
        "197": {"name": "Hemp",              "color": "#8e7672", "L0": "Cropland", "L1": "Industrial Crops", "L2": "Hemp"},
        "200": {"name": "Forest",            "color": "#009900", "L0": "Forest"},
        "210": {"name": "Coniferous",        "color": "#006600", "L0": "Forest"},
        "220": {"name": "Broadleaf",         "color": "#00cc00", "L0": "Forest"},
        "230": {"name": "Mixedwood",         "color": "#cc9900", "L0": "Forest"},
    }
}

# ---- 6. ESA WorldCover ----
DATASETS["esa-worldcover"] = {
    "meta": {
        "label": "ESA WorldCover", "country": "Global",
        "source": "ESA / VITO",
        "resolution": "10m (Sentinel-1/2)", "type": "raster",
        "years": [2020, 2021],
        "url": "https://esa-worldcover.org/"
    },
    "classes": {
        "10":  {"name": "Tree cover",                "color": "#006400", "L0": "Forest"},
        "20":  {"name": "Shrubland",                 "color": "#ffbb22", "L0": "Shrubland"},
        "30":  {"name": "Grassland",                 "color": "#ffff4c", "L0": "Grassland"},
        "40":  {"name": "Cropland",                  "color": "#f096ff", "L0": "Cropland"},
        "50":  {"name": "Built-up",                  "color": "#fa0000", "L0": "Urban"},
        "60":  {"name": "Bare / sparse vegetation",  "color": "#b4b4b4", "L0": "Bare"},
        "70":  {"name": "Snow and ice",              "color": "#f0f0f0", "L0": "Snow/Ice"},
        "80":  {"name": "Permanent water bodies",    "color": "#0064c8", "L0": "Water"},
        "90":  {"name": "Herbaceous wetland",        "color": "#0096a0", "L0": "Wetland"},
        "95":  {"name": "Mangroves",                 "color": "#00cf75", "L0": "Forest"},
        "100": {"name": "Moss and lichen",           "color": "#fae6a0", "L0": "Bare"},
    }
}

# ---- 7. MODIS IGBP Land Cover ----
DATASETS["modis-landcover"] = {
    "meta": {
        "label": "MODIS Land Cover (IGBP)", "country": "Global",
        "source": "NASA MODIS",
        "resolution": "500m", "type": "raster",
        "years": [2020, 2021, 2022, 2023],
        "url": "https://gibs.earthdata.nasa.gov/"
    },
    "classes": {
        "1":  {"name": "Evergreen Needleleaf Forests","color":"#05450a","L0":"Forest"},
        "2":  {"name": "Evergreen Broadleaf Forests","color":"#086a10","L0":"Forest"},
        "3":  {"name": "Deciduous Needleleaf Forests","color":"#54a708","L0":"Forest"},
        "4":  {"name": "Deciduous Broadleaf Forests","color":"#78d203","L0":"Forest"},
        "5":  {"name": "Mixed Forests",      "color": "#009900", "L0": "Forest"},
        "6":  {"name": "Closed Shrublands",  "color": "#c6b044", "L0": "Shrubland"},
        "7":  {"name": "Open Shrublands",    "color": "#dcd159", "L0": "Shrubland"},
        "8":  {"name": "Woody Savannas",     "color": "#dade48", "L0": "Grassland"},
        "9":  {"name": "Savannas",           "color": "#fbff13", "L0": "Grassland"},
        "10": {"name": "Grasslands",         "color": "#b6ff05", "L0": "Grassland"},
        "11": {"name": "Permanent Wetlands", "color": "#27ff87", "L0": "Wetland"},
        "12": {"name": "Croplands",          "color": "#c24f44", "L0": "Cropland"},
        "13": {"name": "Urban and Built-up", "color": "#a5a5a5", "L0": "Urban"},
        "14": {"name": "Cropland/Natural Vegetation Mosaics","color":"#ff6d4c","L0":"Cropland"},
        "15": {"name": "Snow and Ice",       "color": "#f9ffa4", "L0": "Snow/Ice"},
        "16": {"name": "Barren",             "color": "#a5a5a5", "L0": "Bare"},
        "17": {"name": "Water Bodies",       "color": "#69fff8", "L0": "Water"},
    }
}

# ---- 8. Australia ABARES ----
DATASETS["australia"] = {
    "meta": {
        "label": "Australia Catchment Scale Land Use", "country": "Australia",
        "source": "ABARES / ABS",
        "resolution": "~50m (catchment scale)", "type": "raster",
        "years": ["current"],
        "url": "https://www.agriculture.gov.au/"
    },
    "classes": {
        "1":  {"name": "Nature conservation",    "color": "#d090d0", "L0": "Forest"},
        "2":  {"name": "Managed resource protection","color":"#8080ff","L0":"Forest"},
        "3":  {"name": "Other minimal use",      "color": "#c8c8c8", "L0": "Bare"},
        "4":  {"name": "Grazing native vegetation","color":"#ffffff","L0":"Grassland"},
        "5":  {"name": "Production native forests","color":"#008050","L0":"Forest"},
        "6":  {"name": "Plantation forests",     "color": "#80ffc0", "L0": "Forest"},
        "7":  {"name": "Grazing modified pastures","color":"#c0ff80","L0":"Grassland"},
        "8":  {"name": "Dryland cropping",       "color": "#ffff00", "L0": "Cropland"},
        "9":  {"name": "Dryland horticulture",   "color": "#ffc800", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "10": {"name": "Land in transition",     "color": "#ff9030", "L0": "Fallow"},
        "11": {"name": "Irrigated pastures",     "color": "#ff8000", "L0": "Grassland"},
        "12": {"name": "Irrigated cropping",     "color": "#ff0000", "L0": "Cropland"},
        "13": {"name": "Irrigated horticulture", "color": "#c00000", "L0": "Cropland", "L1": "Fruits/Orchards"},
        "14": {"name": "Intensive horticulture and animal production","color":"#0000ff","L0":"Cropland","L1":"Vegetables"},
        "15": {"name": "Other intensive uses",   "color": "#6060a0", "L0": "Urban"},
        "16": {"name": "Urban residential",      "color": "#ff0080", "L0": "Urban"},
        "17": {"name": "Rural residential and farm infrastructure","color":"#ffa0c0","L0":"Urban"},
        "18": {"name": "Mining and waste",       "color": "#808000", "L0": "Urban"},
        "19": {"name": "Water",                  "color": "#0000c8", "L0": "Water"},
    }
}

# ---- 9. DE Africa Crop Mask ----
DATASETS["deafrica-crop"] = {
    "meta": {
        "label": "Africa Cropland Mask", "country": "Africa",
        "source": "Digital Earth Africa",
        "resolution": "10m (Sentinel-2)", "type": "raster",
        "years": ["current"],
        "url": "https://www.digitalearthafrica.org/"
    },
    "classes": {
        "1": {"name": "Cropped land", "color": "#00ff00", "L0": "Cropland"},
        "0": {"name": "Not cropped",  "color": "#000000", "L0": "Unknown"},
    }
}

# ---- 10. GFSAD Global Croplands ----
DATASETS["gfsad-croplands"] = {
    "meta": {
        "label": "GFSAD Global Croplands", "country": "Global",
        "source": "NASA / USGS",
        "resolution": "1km", "type": "raster",
        "years": ["current"],
        "url": "https://gibs.earthdata.nasa.gov/"
    },
    "classes": {
        "1": {"name": "Irrigated cropland", "color": "#ff0000", "L0": "Cropland"},
        "2": {"name": "Rainfed cropland",   "color": "#00ff00", "L0": "Cropland"},
        "0": {"name": "Non-cropland",       "color": "#000000", "L0": "Unknown"},
    }
}

# ---- 11. WorldCereal ----
DATASETS["worldcereal"] = {
    "meta": {
        "label": "WorldCereal Temporary Crops", "country": "Global",
        "source": "ESA / VITO",
        "resolution": "10m (Sentinel)", "type": "raster",
        "years": ["current"],
        "url": "https://esa-worldcereal.org/"
    },
    "classes": {
        "0": {"name": "Not temporary crop", "color": "#000000", "L0": "Unknown"},
        "1": {"name": "Temporary crop",     "color": "#00ff00", "L0": "Cropland"},
    }
}

DATASETS["worldcereal-maize"] = {
    "meta": {
        "label": "WorldCereal Maize", "country": "Global",
        "source": "ESA / VITO",
        "resolution": "10m (Sentinel)", "type": "raster",
        "years": ["current"],
        "url": "https://esa-worldcereal.org/"
    },
    "classes": {
        "0": {"name": "Not maize", "color": "#000000", "L0": "Unknown"},
        "1": {"name": "Maize",     "color": "#f5c71a", "L0": "Cropland", "L1": "Cereals", "L2": "Maize"},
    }
}

DATASETS["worldcereal-winter"] = {
    "meta": {
        "label": "WorldCereal Winter Cereals", "country": "Global",
        "source": "ESA / VITO",
        "resolution": "10m (Sentinel)", "type": "raster",
        "years": ["current"],
        "url": "https://esa-worldcereal.org/"
    },
    "classes": {
        "0": {"name": "Not winter cereal", "color": "#000000", "L0": "Unknown"},
        "1": {"name": "Winter cereal",     "color": "#d4a017", "L0": "Cropland", "L1": "Cereals"},
    }
}

DATASETS["worldcereal-spring"] = {
    "meta": {
        "label": "WorldCereal Spring Cereals", "country": "Global",
        "source": "ESA / VITO",
        "resolution": "10m (Sentinel)", "type": "raster",
        "years": ["current"],
        "url": "https://esa-worldcereal.org/"
    },
    "classes": {
        "0": {"name": "Not spring cereal", "color": "#000000", "L0": "Unknown"},
        "1": {"name": "Spring cereal",     "color": "#e6b800", "L0": "Cropland", "L1": "Cereals"},
    }
}

# ---- 12. New Zealand LCDB ----
DATASETS["newzealand"] = {
    "meta": {
        "label": "New Zealand LCDB v6", "country": "New Zealand",
        "source": "Manaaki Whenua / Landcare Research",
        "resolution": "~15m (Landsat)", "type": "raster",
        "years": ["current"],
        "url": "https://lris.scinfo.org.nz/"
    },
    "classes": {
        "1":  {"name": "Built-up Area (Settlement)","color":"#ff0000","L0":"Urban"},
        "2":  {"name": "Urban Parkland/Open Space","color":"#cc9966","L0":"Urban"},
        "5":  {"name": "Transport Infrastructure","color":"#808080","L0":"Urban"},
        "6":  {"name": "Surface Mine or Dump","color":"#996633","L0":"Bare"},
        "10": {"name": "Sand or Gravel",     "color": "#ffcc99", "L0": "Bare"},
        "12": {"name": "Landslide",          "color": "#cc6600", "L0": "Bare"},
        "14": {"name": "Permanent Snow and Ice","color":"#ffffff","L0":"Snow/Ice"},
        "15": {"name": "Alpine Grass/Herbfield","color":"#ccff66","L0":"Grassland"},
        "16": {"name": "Gravel or Rock",     "color": "#cccccc", "L0": "Bare"},
        "20": {"name": "Lake or Pond",       "color": "#0066ff", "L0": "Water"},
        "21": {"name": "River",              "color": "#0099ff", "L0": "Water"},
        "22": {"name": "Estuarine Open Water","color":"#00ccff", "L0": "Water"},
        "30": {"name": "Short-rotation Cropland","color":"#ffff00","L0":"Cropland"},
        "33": {"name": "Orchard, Vineyard or Other Perennial Crop","color":"#ff9900","L0":"Cropland","L1":"Fruits/Orchards"},
        "40": {"name": "High Producing Exotic Grassland","color":"#66ff00","L0":"Grassland"},
        "41": {"name": "Low Producing Grassland","color":"#99ff66","L0":"Grassland"},
        "43": {"name": "Tall Tussock Grassland","color":"#ccff99","L0":"Grassland"},
        "44": {"name": "Depleted Grassland", "color": "#ffffcc", "L0": "Grassland"},
        "45": {"name": "Herbaceous Freshwater Vegetation","color":"#66cccc","L0":"Wetland"},
        "46": {"name": "Herbaceous Saline Vegetation","color":"#339999","L0":"Wetland"},
        "47": {"name": "Flaxland",           "color": "#339966", "L0": "Wetland"},
        "50": {"name": "Fernland",           "color": "#99cc00", "L0": "Shrubland"},
        "51": {"name": "Gorse and/or Broom", "color": "#cc9900", "L0": "Shrubland"},
        "52": {"name": "Manuka and/or Kanuka","color":"#669933", "L0": "Shrubland"},
        "54": {"name": "Broadleaved Indigenous Hardwoods","color":"#006600","L0":"Forest"},
        "55": {"name": "Sub Alpine Shrubland","color":"#99cc66", "L0": "Shrubland"},
        "56": {"name": "Mixed Exotic Shrubland","color":"#cccc00","L0":"Shrubland"},
        "58": {"name": "Matagouri or Grey Scrub","color":"#999966","L0":"Shrubland"},
        "64": {"name": "Forest - Harvested", "color": "#cc6699", "L0": "Forest"},
        "68": {"name": "Deciduous Hardwoods","color":"#33cc33", "L0": "Forest"},
        "69": {"name": "Indigenous Forest",  "color": "#003300", "L0": "Forest"},
        "70": {"name": "Mangrove",           "color": "#336633", "L0": "Forest"},
        "71": {"name": "Exotic Forest",      "color": "#009933", "L0": "Forest"},
    }
}

# ---- 13. Argentina GeoINTA ----
DATASETS["argentina"] = {
    "meta": {
        "label": "Argentina GeoINTA Crop Map", "country": "Argentina",
        "source": "INTA (Instituto Nacional de Tecnología Agropecuaria)",
        "resolution": "~30m", "type": "raster",
        "years": ["current"],
        "url": "https://geo-backend.inta.gob.ar/"
    },
    "classes": {
        "note": {"name": "Raster classification - classes vary by season/product", "color": "#808080", "L0": "Cropland"}
    }
}

# ---- 14. DEA Australia Land Cover ----
DATASETS["dea-landcover"] = {
    "meta": {
        "label": "Digital Earth Australia Land Cover", "country": "Australia",
        "source": "Geoscience Australia",
        "resolution": "25m (Landsat)", "type": "raster",
        "years": [2018, 2019, 2020],
        "url": "https://www.dea.ga.gov.au/"
    },
    "classes": {
        "111": {"name": "Cultivated Terrestrial Vegetation","color":"#ffff00","L0":"Cropland"},
        "112": {"name": "Natural Terrestrial Vegetation","color":"#009900","L0":"Forest"},
        "124": {"name": "Natural Aquatic Vegetation","color":"#00cccc","L0":"Wetland"},
        "215": {"name": "Artificial Surface","color":"#ff0000","L0":"Urban"},
        "216": {"name": "Natural Bare Surface","color":"#cc9966","L0":"Bare"},
        "220": {"name": "Water",              "color": "#0000ff", "L0": "Water"},
    }
}

# ---- 15. EuroCrops (from index.html) ----
DATASETS["eurocrops"] = {
    "meta": {
        "label": "EuroCrops (EU Field Boundaries)", "country": "EU",
        "source": "EuroCrops / source.coop",
        "resolution": "Vector (parcel-level)", "type": "vector",
        "years": ["2021-2022"],
        "url": "https://beta.source.coop/eurocrops/"
    },
    "classes": {
        "winter_common_soft_wheat":  {"name": "Winter Common/Soft Wheat","color":"#d4a017","L0":"Cropland","L1":"Cereals","L2":"Wheat","L3":"Winter Wheat"},
        "spring_common_soft_wheat":  {"name": "Spring Common/Soft Wheat","color":"#e6b800","L0":"Cropland","L1":"Cereals","L2":"Wheat","L3":"Spring Wheat"},
        "winter_durum_hard_wheat":   {"name": "Winter Durum/Hard Wheat","color":"#c9a830","L0":"Cropland","L1":"Cereals","L2":"Wheat","L3":"Durum Wheat"},
        "winter_barley":             {"name": "Winter Barley",     "color":"#ccaa00","L0":"Cropland","L1":"Cereals","L2":"Barley","L3":"Winter Barley"},
        "spring_barley":             {"name": "Spring Barley",     "color":"#e8c840","L0":"Cropland","L1":"Cereals","L2":"Barley","L3":"Spring Barley"},
        "winter_rye":                {"name": "Winter Rye",        "color":"#b89830","L0":"Cropland","L1":"Cereals","L2":"Rye","L3":"Winter Rye"},
        "winter_triticale":          {"name": "Winter Triticale",  "color":"#a89030","L0":"Cropland","L1":"Cereals","L2":"Triticale","L3":"Winter Triticale"},
        "winter_oats":               {"name": "Winter Oats",       "color":"#c8a848","L0":"Cropland","L1":"Cereals","L2":"Oats","L3":"Winter Oats"},
        "grain_maize_corn_popcorn":  {"name": "Grain Maize/Corn",  "color":"#f5c71a","L0":"Cropland","L1":"Cereals","L2":"Maize"},
        "green_silo_maize":          {"name": "Green/Silo Maize",  "color":"#e8b800","L0":"Cropland","L1":"Cereals","L2":"Maize"},
        "rice":                      {"name": "Rice",              "color":"#fff8dc","L0":"Cropland","L1":"Cereals","L2":"Rice"},
        "spelt":                     {"name": "Spelt",             "color":"#c0a030","L0":"Cropland","L1":"Cereals","L2":"Spelt"},
        "winter_rapeseed_rape":      {"name": "Winter Rapeseed",   "color":"#ffa500","L0":"Cropland","L1":"Oilseeds","L2":"Rapeseed","L3":"Winter Rapeseed"},
        "sunflower":                 {"name": "Sunflower",         "color":"#ffc107","L0":"Cropland","L1":"Oilseeds","L2":"Sunflower"},
        "flax_linen":                {"name": "Flax/Linen",        "color":"#e8d44d","L0":"Cropland","L1":"Oilseeds","L2":"Flax/Linseed"},
        "soy_soybeans":              {"name": "Soy/Soybeans",      "color":"#cdaa20","L0":"Cropland","L1":"Legumes","L2":"Beans"},
        "mustard":                   {"name": "Mustard",           "color":"#eee8aa","L0":"Cropland","L1":"Oilseeds","L2":"Mustard"},
        "hemp_cannabis":             {"name": "Hemp/Cannabis",     "color":"#9acd32","L0":"Cropland","L1":"Industrial Crops","L2":"Hemp"},
        "beans":                     {"name": "Beans",             "color":"#228b22","L0":"Cropland","L1":"Legumes","L2":"Beans"},
        "peas":                      {"name": "Peas",              "color":"#00ff7f","L0":"Cropland","L1":"Legumes","L2":"Peas"},
        "lentils":                   {"name": "Lentils",           "color":"#3cb371","L0":"Cropland","L1":"Legumes","L2":"Lentils"},
        "chickpeas":                 {"name": "Chickpeas",         "color":"#556b2f","L0":"Cropland","L1":"Legumes","L2":"Chickpea"},
        "sweet_lupins":              {"name": "Sweet Lupins",      "color":"#00fa9a","L0":"Cropland","L1":"Legumes","L2":"Lupin"},
        "clover":                    {"name": "Clover",            "color":"#00cd66","L0":"Cropland","L1":"Legumes","L2":"Clover"},
        "alfalfa_lucerne":           {"name": "Alfalfa/Lucerne",   "color":"#2e8b57","L0":"Cropland","L1":"Legumes","L2":"Lucerne"},
        "potatoes":                  {"name": "Potatoes",          "color":"#cd853f","L0":"Cropland","L1":"Root Crops","L2":"Potato"},
        "sugar_beet":                {"name": "Sugar Beet",        "color":"#deb887","L0":"Cropland","L1":"Root Crops","L2":"Sugar Beet"},
        "carrots_daucus":            {"name": "Carrots",           "color":"#ff8c00","L0":"Cropland","L1":"Root Crops","L2":"Carrot"},
        "fresh_vegetables":          {"name": "Fresh Vegetables",  "color":"#ff6347","L0":"Cropland","L1":"Vegetables"},
        "onions":                    {"name": "Onions",            "color":"#daa520","L0":"Cropland","L1":"Vegetables","L2":"Onion"},
        "strawberries":              {"name": "Strawberries",      "color":"#ff4040","L0":"Cropland","L1":"Fruits/Orchards","L2":"Strawberry"},
        "orchards_fruits":           {"name": "Orchards/Fruits",   "color":"#9370db","L0":"Cropland","L1":"Fruits/Orchards"},
        "vineyards_wine_vine_rebland_grapes":{"name":"Vineyards","color":"#722f72","L0":"Cropland","L1":"Vineyards"},
        "pasture_meadow_grassland_grass":{"name":"Pasture/Meadow/Grassland","color":"#7cfc00","L0":"Grassland"},
        "temporary_grass":           {"name": "Temporary Grass",   "color":"#90ee90","L0":"Grassland"},
        "tree_wood_forest":          {"name": "Tree/Wood/Forest",  "color":"#2f4f4f","L0":"Forest"},
        "shrubberries_shrubs":       {"name": "Shrubs",            "color":"#4a7c59","L0":"Shrubland"},
        "flowers_ornamental_plants": {"name": "Flowers/Ornamental","color":"#ff69b4","L0":"Cropland","L1":"Flowers"},
        "fallow_land_not_crop":      {"name": "Fallow Land",       "color":"#d2b48c","L0":"Fallow"},
        "not_known_and_other":       {"name": "Unknown/Other",     "color":"#a9a9a9","L0":"Unknown"},
    }
}


def infer_duration(cls):
    """Infer annual/perennial from hierarchy. Returns 'annual', 'perennial', 'mixed', or None."""
    if "duration" in cls:
        return cls["duration"]
    # Check L2 type first
    l2 = cls.get("L2")
    if l2 and l2 in HIERARCHY.get("L2", {}):
        h = HIERARCHY["L2"][l2]
        if "duration" in h:
            return h["duration"]
    # Check L1 category
    l1 = cls.get("L1")
    if l1 and l1 in HIERARCHY.get("L1", {}):
        h = HIERARCHY["L1"][l1]
        if "duration" in h:
            return h["duration"]
    # Non-crop L0 types
    l0 = cls.get("L0", "")
    if l0 == "Grassland":
        return "perennial"
    elif l0 == "Forest":
        return "perennial"
    elif l0 == "Shrubland":
        return "perennial"
    elif l0 in ("Water", "Urban", "Bare", "Snow/Ice", "Wetland", "Unknown"):
        return None
    elif l0 == "Fallow":
        return None
    return None


def build_output():
    """Build the comprehensive classification hierarchy JSON."""

    # Enrich classes with inferred duration
    for ds_id, ds in DATASETS.items():
        for code, cls in ds.get("classes", {}).items():
            dur = infer_duration(cls)
            if dur:
                cls["duration"] = dur

    # Cross-reference: for each L2 crop type, which datasets include it?
    l2_cross_ref = {}
    for ds_id, ds in DATASETS.items():
        if ds_id == "meta":
            continue
        for code, cls in ds.get("classes", {}).items():
            l2 = cls.get("L2")
            if l2:
                if l2 not in l2_cross_ref:
                    l2_cross_ref[l2] = {}
                if ds_id not in l2_cross_ref[l2]:
                    l2_cross_ref[l2][ds_id] = []
                l2_cross_ref[l2][ds_id].append({
                    "code": code,
                    "name": cls["name"],
                    "L3": cls.get("L3")
                })

    # Summary stats
    summary = {}
    for ds_id, ds in DATASETS.items():
        classes = ds.get("classes", {})
        meta = ds.get("meta", {})
        l0_counts = {}
        l1_counts = {}
        for cls in classes.values():
            l0 = cls.get("L0", "Unknown")
            l1 = cls.get("L1")
            l0_counts[l0] = l0_counts.get(l0, 0) + 1
            if l1:
                l1_counts[l1] = l1_counts.get(l1, 0) + 1
        summary[ds_id] = {
            "label": meta.get("label", ds_id),
            "country": meta.get("country", ""),
            "resolution": meta.get("resolution", ""),
            "type": meta.get("type", ""),
            "total_classes": len(classes),
            "L0_distribution": l0_counts,
            "L1_distribution": l1_counts,
        }

    output = {
        "_description": "Crop and land cover classification hierarchy across all map datasets. "
                        "L0=Land surface type, L1=Crop category, L2=Crop type, L3=Seasonal variant. "
                        "Generated by analyse_classes.py.",
        "_generated": "2026-03-01",
        "hierarchy": HIERARCHY,
        "datasets": {ds_id: ds for ds_id, ds in DATASETS.items()},
        "cross_reference_L2": l2_cross_ref,
        "summary": summary,
    }
    return output


def print_report(data):
    """Print a human-readable summary to stdout."""
    print("=" * 70)
    print("CROP / LAND-COVER CLASSIFICATION ANALYSIS")
    print("=" * 70)
    print()

    # Dataset overview
    print("DATASETS:")
    print("-" * 70)
    for ds_id, s in data["summary"].items():
        print(f"  {ds_id:25s} {s['label']:40s} {s['total_classes']:3d} classes  ({s['resolution']})")
    print()

    # L0 comparison
    print("L0 (LAND SURFACE TYPE) — classes per dataset:")
    print("-" * 70)
    all_l0 = sorted(set(
        l0 for s in data["summary"].values() for l0 in s["L0_distribution"]
    ))
    header = f"{'Dataset':25s}" + "".join(f"{l0:>10s}" for l0 in all_l0)
    print(header)
    for ds_id, s in data["summary"].items():
        row = f"{ds_id:25s}"
        for l0 in all_l0:
            count = s["L0_distribution"].get(l0, 0)
            row += f"{count:10d}" if count else f"{'':>10s}"
        print(row)
    print()

    # L2 cross-reference (crop types present in 3+ datasets)
    print("L2 (CROP TYPE) — cross-dataset availability:")
    print("-" * 70)
    for l2, ds_map in sorted(data["cross_reference_L2"].items(),
                              key=lambda x: -len(x[1])):
        n = len(ds_map)
        if n >= 2:
            ds_list = ", ".join(sorted(ds_map.keys()))
            print(f"  {l2:20s} ({n} datasets): {ds_list}")
    print()

    # Annual vs perennial
    print("ANNUAL vs PERENNIAL CROPS per dataset:")
    print("-" * 70)
    for ds_id, ds in data["datasets"].items():
        annual = perennial = other = 0
        for cls in ds.get("classes", {}).values():
            dur = cls.get("duration")
            if dur == "annual":
                annual += 1
            elif dur == "perennial":
                perennial += 1
            elif dur == "mixed":
                other += 1
        if annual + perennial + other > 0:
            print(f"  {ds_id:25s} annual={annual:3d}  perennial={perennial:3d}  mixed={other:3d}")
    print()

    # Unique crops per dataset
    print("DATASET-SPECIFIC CROP CLASSES (not in hierarchy):")
    print("-" * 70)
    for ds_id, ds in data["datasets"].items():
        unique = [c for c in ds.get("classes", {}).values()
                  if c.get("L0") == "Cropland" and not c.get("L2")]
        if unique:
            names = [c["name"] for c in unique[:10]]
            extra = f" (+{len(unique)-10} more)" if len(unique) > 10 else ""
            print(f"  {ds_id}: {', '.join(names)}{extra}")


def main():
    data = build_output()

    # Write JSON
    outpath = os.path.join(SCRIPT_DIR, "crop_classification_hierarchy.json")
    with open(outpath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Written: {outpath}")
    print()

    # Print report
    print_report(data)


if __name__ == "__main__":
    main()
