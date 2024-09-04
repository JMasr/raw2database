# Raw2DataBase: a Metabase + PostgreSQL + Docker Solution to Showcase Your Data 📊

## About ✨
Raw2DataBase is a streamlined solution for loading raw CSV data into a [PostgreSQL](https://www.postgresql.org/) database,
leveraging [Docker](https://www.docker.com/) for easy deployment and [Metabase](https://www.metabase.com/) for powerful
data visualization. This project provides a robust framework for managing database connections, processing CSV data,
and seamlessly integrating with Metabase for data analysis and reporting.

## Project Requirements 👨‍🔧
1. Database Connection Handler 🛰️
   - Generic and extensible to support multiple database types (PostgreSQL, MySQL, MongoDB etc.).
   - Handles CSV processing using pandas, converting files into dataframes for database insertion.

2. Main Application Logic ⚙️
   - Script to receive configuration and raw data paths.
   - Manages database connection setup, data processing, and data insertion.

3. Tests 🩹
   - Tests for each feature to ensure correct functionality and reliability.

## Features (✅=DONE, ❌=TODO)
* ✅ Database Connection Handler: A flexible, extensible handler for connecting to various databases.
* ✅ CSV Processing: Efficient CSV data processing using [pandas](https://pandas.pydata.org/), converting raw data into SQL-like objects for database insertion.
* ✅ Dockerized Environment: Easy setup and deployment using [Docker](https://www.docker.com/) and Docker Compose.
* ✅ Data Visualization: Integration with [Metabase](https://www.metabase.com/) for creating and sharing interactive dashboards and reports.
* ❌ Test Coverage: Comprehensive tests using [Pytest](https://docs.pytest.org/en/8.2.x/) to ensure the reliability and correctness of each component.

## General Project Structure 🧱
```
raw2database/
├── docker/
│   ├── .env
│   └── docker-compose.yml
├── src/
│   ├── __init__.py
│   ├── data/
│   │    ├── __init__.py
│   │    └── data_processor.py
│   └── database/
│       ├── __init__.py
│       ├── database.py
│       └── database_loader.py
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_data_loader.py
│   └── test_data_processor.py
├── config/
│   └── your_db_config.json
├── raw_data/
│   └── your_data.csv
├── requirements.txt
├── README.md
└── .gitignore
```

## Getting Started 🤓

⚠️**Recommended Python version: 3.9**⚠️

1. Clone the Repository

```bash
git clone https://github.com/JMasr/raw2database.git
```
2. Navigate to the Project Directory

```bash
cd raw2database
```

3. Create and Activate the Conda Environment

```bash
conda create -n raw2database python=3.9
conda activate raw2database
```

4. Install Requirements

```bash
pip install -r requirements.txt
```

5. Navigate to the Docker Folder
```bash
cd docker
```
6. Configure the **.env** File with your Credentials
```bash
cat <<EOL > .env
POSTGRES_USER=<user_postgres>
POSTGRES_PASSWORD=<pass_postgres>
POSTGRES_DB=<ps_db_name>
PGADMIN_DEFAULT_EMAIL=<root@admin.demo>
PGADMIN_DEFAULT_PASSWORD=<pass_ui-admin_tool>
EOL
```

7. Run Docker Compose
```bash
docker-compose up -d
```
8. Create a configuration folder
```bash
mkdir config
```

9. Configure the Database
Edit the config/postgres_config.json file to set the database connection details:
```bash
cd config
cat <<EOL > postgres_config.json
{
  "db_type": "postgres",
  "DB_NAME": "<ps_db_name>",
  "DB_HOST": "<host>",
  "DB_PORT": <port>,
  "DB_USER": "<user_postgres>",
  "DB_PASSWORD": "<pass_postgres>"
}
EOL
```
10. Running the Application
To load data from a CSV file into the database, run:
```bash
python src/main.py --raw_files_path <path/to/your_data.csv> --config_file config/postgres_config.json --db_type postgres
```

## Contributing 🤗
Contributions are welcome! Please fork the repository and create a pull request with your improvements.

## License 📜
This project is licensed under the MIT License - see the LICENSE file for details.

## Contact 📧
For any questions or issues, please open an issue in the repository or contact the maintainer at **jmramirez@gts.uvigo.es**