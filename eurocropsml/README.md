# EuroCropsML

Machine learning benchmark for crop classification using Sentinel-2 time series.

**Source:** [Zenodo Record 15095445](https://zenodo.org/records/15095445)

## Dataset

- **706,683 parcels** across Latvia, Estonia, and Portugal
- **176 crop classes** (HCAT taxonomy)
- **Sentinel-2 time series**: 10 spectral bands at 10m resolution
- **Format**: NumPy compressed archives (.npz) with train/test splits per country

## Quick Start

```bash
# List available files
python3 eurocropsml/download.py --list

# Download Latvia subset
python3 eurocropsml/download.py --download --country latvia

# Explore class distribution
python3 eurocropsml/explore.py --country latvia

# Plot sample time series
python3 eurocropsml/explore.py --country latvia --plot
```

## Requirements

```
numpy
matplotlib  # for plotting only
```
