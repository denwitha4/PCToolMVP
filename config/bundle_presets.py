"""
Bundle allocation presets for PC component bundles.

Each preset defines default weight percentages for component categories.
Weights are used to allocate bundle costs proportionally across components.
"""

BUNDLE_PRESETS = {
    "gaming_pc": {
        "name": "Gaming PC Bundle",
        "description": "High-performance gaming PC with GPU focus",
        "weights": {
            "GPU": 45.0,
            "CPU": 20.0,
            "Motherboard": 10.0,
            "RAM": 8.0,
            "Storage": 7.0,
            "PSU": 5.0,
            "Case": 3.0,
            "Cooling": 2.0,
        }
    },
    "office_pc": {
        "name": "Office PC Bundle",
        "description": "Productivity-focused PC for office work",
        "weights": {
            "CPU": 30.0,
            "Motherboard": 15.0,
            "RAM": 15.0,
            "Storage": 20.0,
            "PSU": 10.0,
            "Case": 10.0,
        }
    },
    "gpu_heavy": {
        "name": "GPU-Heavy Bundle",
        "description": "Mining or rendering rig with dominant GPU allocation",
        "weights": {
            "GPU": 70.0,
            "CPU": 10.0,
            "Motherboard": 7.0,
            "RAM": 5.0,
            "PSU": 5.0,
            "Case": 3.0,
        }
    },
    "storage_heavy": {
        "name": "Storage-Heavy Bundle",
        "description": "NAS or storage server with high storage allocation",
        "weights": {
            "Storage": 50.0,
            "CPU": 20.0,
            "Motherboard": 12.0,
            "RAM": 10.0,
            "Case": 8.0,
        }
    }
}
