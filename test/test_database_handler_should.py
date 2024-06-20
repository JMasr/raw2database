import json
import os
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from faker import Faker
from pydantic import ValidationError

from logger import BasicLogger
from src.database.database_handler import PostgresHandler, BaseDatabaseHandler, DatabaseHandlerFactory
from test import TEST_FOLDER


def mock_a_dataframe_with_metadata(number_of_rows: int = 100):
    fake = Faker()
    ids = [fake.uuid4() for _ in range(number_of_rows)]
    labels = [fake.boolean() for _ in range(number_of_rows)]
    data = np.random.randint(0, 100, size=number_of_rows)
    genders = [fake.random_element(["Male", "Female"]) for _ in range(number_of_rows)]
    return pd.DataFrame({"id": ids, "label": labels, "data": data, "gender": genders})


def mock_a_dataframe_with_metadata_and_audio(
        path_to_temp_folder: str, sample_rate: int, number_of_rows: int = 100
        , sf=None):
    df_with_metadata = mock_a_dataframe_with_metadata(number_of_rows)

    # Create a temporary audio file
    os.makedirs(path_to_temp_folder, exist_ok=True)

    paths_to_dummy_audio_files = []
    for i in df_with_metadata["id"]:
        path_to_dummy_valid_signal = os.path.join(
            path_to_temp_folder, f"{i}.wav"
        )
        valid_dummy_signal = np.random.uniform(-1, 1, size=(sample_rate * 10, 2))
        sf.write(
            path_to_dummy_valid_signal,
            valid_dummy_signal,
            sample_rate,
            subtype="PCM_24",
        )
        paths_to_dummy_audio_files.append(path_to_dummy_valid_signal)
    df_with_metadata["path"] = paths_to_dummy_audio_files

    return df_with_metadata


DB_2_CLASS = {
    "postgres": PostgresHandler,
}


class TestPostgresHandlerShould:

    @classmethod
    def setup_class(cls):
        # Create a temporary resources for testing
        cls.str_path_temp_folder = os.path.join(TEST_FOLDER, "temp_folder")
        os.makedirs(cls.str_path_temp_folder, exist_ok=True)

        cls.str_path_temp_env_file = os.path.join(cls.str_path_temp_folder, "config_env.json")
        cls.dict_env_vars = {
            "DB_USER": "test_user",
            "DB_PASSWORD": "test_password",
            "DB_HOST": "test_host",
            "DB_PORT": "test_port",
            "DB_NAME": "test_name",
        }

        # Create a temporary json file
        with open(cls.str_path_temp_env_file, "w") as f:
            f.write(json.dumps(cls.dict_env_vars))

        cls.str_path_temp_csv_file = os.path.join(cls.str_path_temp_folder, "temp_file.csv")
        cls.temp_file = Path(cls.str_path_temp_csv_file)

        cls.num_rows = 50
        cls.mock_dataframe = mock_a_dataframe_with_metadata(cls.num_rows)
        cls.mock_dataframe.to_csv(cls.temp_file, index=False, sep=",")

        # Create a logger
        cls.app_logger = BasicLogger(
            log_file=os.path.join(cls.str_path_temp_folder, "logs", "experiment.log")
        ).get_logger()

    @classmethod
    def teardown_class(cls):
        shutil.rmtree(cls.str_path_temp_folder, ignore_errors=True)

    @pytest.mark.parametrize("db_type", ["postgres"])
    def test_initialization_should(self, db_type: str):
        # Arrange & Act
        db_handler = DatabaseHandlerFactory.get_database_handler(db_type, self.str_path_temp_env_file, self.app_logger)

        # Assert
        assert isinstance(db_handler, DB_2_CLASS[db_type])
        assert db_handler.app_logger == self.app_logger
        assert db_handler.path2config == self.str_path_temp_env_file

        with pytest.raises(ValidationError):
            invalid_db_handler = PostgresHandler(
                db_type=db_type,
                path2config=TEST_FOLDER,
                app_logger=self.app_logger,
            )

        with pytest.raises(TypeError):
            invalid_db_handler = BaseDatabaseHandler(
                db_type=db_type,
                path2config=self.str_path_temp_folder,
                app_logger=self.app_logger,
            )

    @pytest.mark.parametrize("db_type", ["postgres"])
    def test_setup_should(self, db_type):
        # Arrange
        db_handler = DatabaseHandlerFactory.get_database_handler(db_type, self.str_path_temp_env_file)

        # Act
        db_handler.setup()

        # Assert
        assert isinstance(db_handler, DB_2_CLASS[db_type])
        assert db_handler.app_logger == self.app_logger
        assert db_handler.configuration_data == self.dict_env_vars


if __name__ == "__main__":
    # Run all tests in the module
    pytest.main()
