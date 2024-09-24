import argparse
import os
from pathlib import Path

from src.utils import read_config_from_file
from src.database.handler import DatabaseHandlerFactory

ROOT_PATH = Path(__file__).parent

if __name__ == '__main__':
    arguments = argparse.ArgumentParser(description="Run raw2database project with the given configuration file.")
    arguments.add_argument(
        "--config_file",
        type=str,
        default=os.path.join(ROOT_PATH, "config", "postgres_config.json"),
        help="Path to the configuration file",
    )
    arguments.add_argument(
        "--raw_files_path",
        type=str,
        default=os.path.join(ROOT_PATH, "data", "processed"),
        help="Path to the raw files",
    )
    args = arguments.parse_args()


    path_config_file = args.config_file
    raw_files_path = args.raw_files_path

    db_configuration = read_config_from_file(path_config_file)
    db_handler = DatabaseHandlerFactory.get_database_handler(db_config=db_configuration)

    db_handler.setup()
    db_handler.connect()

    if db_handler.is_the_connection_up():
        db_handler.files2tables(raw_files_path)
        db_handler.close_connection()

