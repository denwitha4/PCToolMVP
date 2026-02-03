"""
Bundle allocation presets for PC component bundles.
"""

BUNDLE_PRESETS = {
    "full_build": {
        "name": "Full Build",
        "description": "Complete PC with all standard components",
        "auto_populate": True,
        "components": [
            {"category": "GPU", "weight": 30.0, "quantity": 1},
            {"category": "CPU", "weight": 20.0, "quantity": 1},
            {"category": "RAM", "weight": 20.0, "quantity": 1},
            {"category": "Storage", "weight": 15.0, "quantity": 1},
            {"category": "Motherboard", "weight": 5.0, "quantity": 1},
            {"category": "PSU", "weight": 5.0, "quantity": 1},
            {"category": "Case", "weight": 2.5, "quantity": 1},
            {"category": "Cooling", "weight": 2.5, "quantity": 1},
        ]
    },
    "bulk": {
        "name": "Bulk",
        "description": "Multiple quantities of same component type",
        "auto_populate": False,
        "components": []
    },
    "custom": {
        "name": "Custom",
        "description": "Build your own component mix",
        "auto_populate": False,
        "components": []
    }
}
