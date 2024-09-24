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
    db_configuration: Dict[str, Any]

    engine: Optional[Any] = None
    app_logger: Optional[logging.Logger] = None

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

    @abstractmethod
    def setup(self):
        pass

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


class PostgresHandler(BaseDatabaseHandler, ABC):

    def setup(self, max_retries: int = 3):
        # Load configuration data
        db_user = self.db_configuration.get('DB_USER')
        db_password = self.db_configuration.get('DB_PASSWORD')
        db_host = self.db_configuration.get('DB_HOST')
        db_port = self.db_configuration.get('DB_PORT')
        db_name = self.db_configuration.get('DB_NAME')

        if not all([db_user, db_password, db_host, db_port, db_name]):
            raise ValueError(f"PostgresHandler - Missing or invalid configuration data: {self.db_configuration}")

        try:
            engine = create_engine(
                f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
            self.engine = engine

            self.app_logger.info("PostgresHandler - Connected to Postgres.")
        except Exception as e:
            self.app_logger.error(f"PostgresHandler - Error during Postgres Engine Setup: {e}")
            raise SystemError(e)

    def connect(self, max_retries: int = 3) -> bool:
        if self.engine is not None:
            self.app_logger.warning("PostgresHandler - Engine dont setting up, trying to do it...")
            self.setup()

        engine, retries = None, 0
        response: bool = False
        while retries < max_retries:
            try:
                self.engine.connect()
                response = True

                self.app_logger.info("PostgresHandler - Connection Establishing ")
                break
            except Exception as e:
                self.app_logger.error(f"PostgresHandler - Error connecting to Postgres: {e}. Retrying...")
                retries += 1

        if retries == max_retries:
            self.app_logger.error(f"PostgresHandler - Failed to connect after {max_retries} retries.")

        return response

    def is_the_connection_up(self):
        return self.connect(max_retries=1)

    def close_connection(self):
        try:
            self.engine.dispose()
            self.app_logger.info("PostgresHandler - Postgres connection closed.")

        except Exception as e:
            self.app_logger.error(f"PostgresHandler - Error closing the connection: {e}")
            raise ConnectionError("PostgresHandler - Error closing the connection.") from e


    def _files2dataframes(self, raw_files_path: str, raw_files_extension: str) -> Dict[str, pd.DataFrame]:
        try:
            raw_file_names = [file for file in os.listdir(raw_files_path) if file.endswith(raw_files_extension)]
            self.app_logger.info(f"DataProcessor "
                                 f"- Found {len(raw_file_names)} files with extension {raw_files_extension}")

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

    @staticmethod
    def _preprocess_dataframes(dict_with_df: dict):
        """
        Recive a dictionary with dataframes and preprocess them to cast the columns to the correct data types, assign
        the correct column names, remove duplicates, and handle missing values.

        :param dict_with_df: Dictionary with dataframes
        :return: A dictionary with preprocessed dataframes
        """
        clean_dataframes = {}
        for key, df in dict_with_df.items():
            df = df.copy()

            # Infer the data types of the columns
            df = df.infer_objects()

            # Cast categorical columns with a low cardinality to category type
            for col in df.select_dtypes(include=["object"]).columns:
                if df[col].nunique() < 10:
                    df[col] = df[col].astype("category")

            # Remove duplicates
            df = df.drop_duplicates()

            # Handle missing values on numerical columns, filling with 0
            numerical_columns = df.select_dtypes(include=["float64", "int64"]).columns
            df[numerical_columns] = df[numerical_columns].fillna(0)

            # Handle missing values on categorical columns, filling with "No Answer"
            categorical_columns = df.select_dtypes(include=["object"]).columns
            df[categorical_columns] = df[categorical_columns].fillna("No Answer")

            # Assign to categorical columns a string type
            df[categorical_columns] = df[categorical_columns].astype(str)

            clean_dataframes[key] = df

        return clean_dataframes



    def files2tables(self, raw_files_path: str, raw_files_extension: str = ".csv"):
        files_as_dataframes = self._files2dataframes(raw_files_path, raw_files_extension)
        clean_dataframes = self._preprocess_dataframes(files_as_dataframes)

        if len(clean_dataframes) == 0:
            raise ValueError("DataProcessor - No dataframes found. We will not create any table.")

        file: str
        df: pd.DataFrame
        for file, df in clean_dataframes.items():
            self.app_logger.info(f"DataProcessor - Saving dataframe {file} as a table")
            num_row_transformed = df.copy().to_sql(file, con=self.engine, if_exists="replace")
            self.app_logger.info(f"DataProcessor - {num_row_transformed} rows were saved in the table {file}")


class DatabaseHandlerFactory:
    @staticmethod
    def get_database_handler(db_config: Dict[str, Any], app_logger: logging.Logger = None) -> BaseDatabaseHandler:
        db_type = db_config.get("DB_TYPE")
        if db_type == "postgres":
            return PostgresHandler(db_configuration=db_config, app_logger=app_logger)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
