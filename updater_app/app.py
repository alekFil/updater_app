import io
import json
import sys
from typing import Any, Dict, List, Tuple

import joblib
import pandas as pd
import psycopg2
import requests


def load_config(config_path: str) -> dict:
    """Loads configuration from a JSON file."""
    with open(config_path, "r") as config_file:
        return json.load(config_file)


def connect_to_db(db_params: Dict[str, str]) -> psycopg2.extensions.connection:
    """
    Устанавливает соединение с базой данных.

    Parameters
    ----------
    db_params : dict
        Словарь с данными для подлючения к базе данных.
        Ожидаемые ключи: 'dbname', 'user', 'password', 'host', and 'port'.

    Returns
    -------
    psycopg2.extensions.connection
        Объект connection.

    Raises
    ------
    SystemExit
        Если не удалось подключиться.
    """
    try:
        connection = psycopg2.connect(**db_params)
        return connection
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        sys.exit(1)


def parse_queries(file_path: str) -> Dict[str, str]:
    """
    Считывает запросы к базе данных из файла

    Parameters
    ----------
    file_path : str
        Путь к файлу с запросами.

    Returns
    -------
    Dict[str, str]
        Словарь, где ключи первые символы до двоеточия в фале, значения - полученные данные.
    """
    queries = {}
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            key, query = line.split(": ", 1)
            queries[key] = query.strip()
    return queries


def execute_queries(
    connection: psycopg2.extensions.connection,
) -> Dict[str, List[Tuple[Any, ...]]]:
    """
    Выполняет запросы к базе данных из файла.

    Parameters
    ----------
    connection : psycopg2.extensions.connection
        Объект подключения к базе данных.

    Returns
    -------
    Dict[str, List[Tuple[Any, ...]]]
        Словарь, содержащий результаты запросов.
        Ключами словаря являются названия запросов (строки),
        значениями — списки кортежей, представляющих строки результатов запросов.

    Raises
    ------
    SystemExit
        Если выполнение запросов завершилось с ошибкой.
    """
    try:
        cursor = connection.cursor()
        queries = parse_queries("queries.txt")

        results = {}
        for key, value in queries.items():
            cursor.execute(value)
            results[key] = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Failed to execute queries: {e}")
        sys.exit(1)


def main(config_path: str) -> None:
    """
    Выполняет основной функционал скрипта: устанавливает соединение с базой данных,
    запрашивает информацию, преобразует данные в формат, требуемый API (pd.DataFrame),
    сохраняет в байтовый поток и отправляет как файлы в API.
    Сейчас работает, как костыль с конкретными форматами файлов.

    Parameters
    ----------
    db_params : dict
        Словарь с данными для подключения к базе данных.
    api_url : str
        Адрес API.
    """
    config = load_config(config_path)

    db_params = config["db_params"]
    api_url = config["api_url"]
    api_key = config["api_key"]

    connection = connect_to_db(db_params)
    results = execute_queries(connection)

    schools_df = pd.DataFrame(results["schools"], columns=["id", "name", "region"])
    similar_schools_df = pd.DataFrame(
        results["similar_schools"],
        columns=["school_id", "name", "reference", "region"],
    )

    # Сохранение данных в объекты байтового потока (как файл)
    buffer_1: io.BytesIO = io.BytesIO()
    joblib.dump(schools_df, buffer_1)
    buffer_1.seek(0)

    buffer_2: io.BytesIO = io.BytesIO()
    joblib.dump(similar_schools_df, buffer_2)
    buffer_2.seek(0)

    # Загрузка данных на сервер FastAPI
    upload_url: str = api_url + "upload-dataframes/"

    files = {
        "file1": buffer_1,
        "file2": buffer_2,
    }
    headers = {"api_key": api_key}

    # Запрос на загрузку
    response: requests.Response = requests.post(
        upload_url, files=files, headers=headers
    )

    # Проверка ответа
    if response.status_code == 200:
        print("Данные успешно загружены!")
    else:
        print(f"Ошибка загрузки данных: {response.text}")

    response = requests.get(api_url + "reload-resources/")
    if response.status_code == 200:
        print("Сервис успешно перезагружен!")
    else:
        print("Ошибка перезагрузки сервиса:", response.status_code)


def run() -> None:
    """Entry point for the script to process command-line arguments."""
    if len(sys.argv) != 2:
        print("Usage: updater_app <path_to_config>")
        sys.exit(1)

    config_path = sys.argv[1]
    main(config_path)


if __name__ == "__main__":
    run()
