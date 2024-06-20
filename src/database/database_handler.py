import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Any, Dict

import pandas as pd
from pydantic import BaseModel
from sqlalchemy import create_engine

from src.logger import BasicLogger


class BaseDatabaseHandler(ABC, BaseModel):
    db_type: str
    path2config: str

    engine: Optional[Any] = None
    app_logger: Optional[logging.Logger] = None
    configuration_data: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        self._logger_setup()

    def _logger_setup(self):
        if self.app_logger is None:
            try:
                self.app_logger = BasicLogger(
                    log_file=os.path.join(Path(__file__).parent.parent.parent, "logs", "experiment.log")
                ).get_logger()
                self.app_logger.warning(
                    f"DatabaseHandler - No logger was passed. Using a default one."
                )
            except Exception as e:
                raise ValueError("DatabaseHandler - Error setting up the logger.") from e
        else:
            try:
                self.app_logger.info("DatabaseHandler - Logger already set up.")
            except Exception as e:
                raise ValueError("DatabaseHandler - Error on the Logger provided.") from e

    def _read_config_from_file(self) -> Dict[str, Any]:
        # Read the configuration file based on the extension
        if not os.path.isfile(self.path2config):
            raise FileNotFoundError(f"DatabaseHandler - Configuration file not found: {self.path2config}")

        if self.path2config.endswith(".json"):
            with open(self.path2config, "r") as file:
                configuration_as_dict = json.load(file)
        else:
            raise ValueError(f"DatabaseHandler - Unsupported file extension: {self.path2config}")
        return configuration_as_dict

    def setup(self):
        self._logger_setup()
        self.configuration_data = self._read_config_from_file()

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def is_the_connection_up(self):
        pass

    @abstractmethod
    def close_connection(self):
        pass

    def get_engine(self):
        if self.engine is None:
            raise ConnectionError("Database not connected. Call `connect` first.")
        return self.engine


class PostgresHandler(BaseDatabaseHandler):

    def _try_to_connect_n_times(self, db_host, db_name, db_password, db_port, db_user, max_retries):
        engine, retries = None, 0
        while retries < max_retries:
            try:
                engine = create_engine(
                    f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
                self.app_logger.info("PostgresHandler - Connected to Postgres.")
                break
            except Exception as e:
                self.app_logger.error(f"PostgresHandler - Error connecting to Postgres: {e}. Retrying...")
                retries += 1
        if retries == max_retries:
            raise ConnectionError(f"PostgresHandler - Failed to connect after multiple retries.")

        return engine

    def connect(self, max_retries: int = 3):
        # Load configuration data
        db_user = self.configuration_data.get('DB_USER')
        db_password = self.configuration_data.get('DB_PASSWORD')
        db_host = self.configuration_data.get('DB_HOST')
        db_port = self.configuration_data.get('DB_PORT')
        db_name = self.configuration_data.get('DB_NAME')

        # Input validation and sanitization
        if not all([db_user, db_password, db_host, db_port, db_name]):
            raise ValueError(f"PostgresHandler - Missing or invalid configuration data: {self.configuration_data}")

        self.engine = self._try_to_connect_n_times(db_host, db_name, db_password, db_port, db_user, max_retries)

    def is_the_connection_up(self) -> bool:
        try:
            self.engine.connect()
            self.app_logger.info("Postgres is running")
            return True
        except Exception as e:
            self.app_logger.error(f"PostgresHandler - Error connecting to Postgres: {e}. Try call `connect` first ")
            return False

    def close_connection(self):
        try:
            if self.is_the_connection_up():
                self.engine.dispose()
                self.app_logger.info("PostgresHandler - Postgres connection closed.")
            else:
                self.app_logger.warning("PostgresHandler - Postgres connection already closed.")
        except Exception as e:
            self.app_logger.error(f"PostgresHandler - Error closing the connection: {e}")
            raise ConnectionError("PostgresHandler - Error closing the connection.") from e

    def _files2dataframes(self, raw_files_path: str, raw_files_extension: str) -> Dict[str, pd.DataFrame]:
        try:
            raw_file_names = [file for file in os.listdir(raw_files_path) if file.endswith(raw_files_extension)]
            self.app_logger.info(f"DataProcessor "
                                 f"- Found {len(raw_file_names)} files with extension {raw_files_extension}")

            # Storage each file ina pandas dataframe
            files2dataframes = {}
            for file_name in raw_file_names:
                self.app_logger.info(f"DataProcessor - Reading file {file_name}")
                # Read the file
                path_to_file = os.path.join(raw_files_path, file_name)
                if raw_files_extension == ".csv":
                    df = pd.read_csv(path_to_file)
                elif raw_files_extension == ".json":
                    df = pd.read_json(path_to_file)
                else:
                    self.app_logger.warning(f"DataProcessor - Unsupported file extension for: {file_name}. Skipping!")
                    continue

                # Store the dataframe
                files2dataframes[file_name.split(".")[0]] = df

            if len(files2dataframes) == 0:
                self.app_logger.warning("DataProcessor - No files were read.")
                files2dataframes = {}
            elif len(files2dataframes) < len(raw_file_names):
                self.app_logger.warning(f"DataProcessor -"
                                        f" {len(files2dataframes) - len(raw_file_names)} files were not read")
            elif len(files2dataframes) == len(raw_file_names):
                self.app_logger.info("DataProcessor - All files were read.")
        except Exception as e:
            self.app_logger.error(f"DataProcessor - Error reading the files: {e}")
            files2dataframes = {}

        return files2dataframes

    def files2tables(self, raw_files_path: str, raw_files_extension: str = ".csv"):
        files_as_dataframes = self._files2dataframes(raw_files_path, raw_files_extension)
        if len(files_as_dataframes) == 0:
            raise ValueError("DataProcessor - No dataframes found. We will not create any table.")

        file: str
        df: pd.DataFrame
        for file, df in files_as_dataframes.items():
            self.app_logger.info(f"DataProcessor - Saving dataframe {file} as a table")
            num_row_transformed = df.copy().to_sql(file, con=self.engine, if_exists="replace")
            self.app_logger.info(f"DataProcessor - {num_row_transformed} rows were saved in the table {file}")


class DatabaseHandlerFactory:
    @staticmethod
    def get_database_handler(db_type: str, path_to_config: str,
                             app_logger: logging.Logger = None) -> BaseDatabaseHandler:
        if db_type == "postgres":
            return PostgresHandler(
                db_type=db_type,
                path2config=path_to_config,
                app_logger=app_logger,
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
