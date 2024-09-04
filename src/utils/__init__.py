import os
import json

from typing import Dict, Any


def read_config_from_file(path2config) -> Dict[str, Any]:
    # Read the configuration file based on the extension
    if not os.path.isfile(path2config):
        raise FileNotFoundError(f"DatabaseHandler - Configuration file not found: {path2config}")

    if path2config.endswith(".json"):
        with open(path2config, "r") as file:
            configuration_as_dict = json.load(file)
    else:
        raise ValueError(f"DatabaseHandler - Unsupported file extension: {path2config}")
    return configuration_as_dict