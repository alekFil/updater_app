import io
import json
import sys
from typing import Any, Dict, List, Tuple

import joblib
import pandas as pd
import psycopg2
import requests
from cryptography.fernet import Fernet


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
        queries = parse_queries("queries.txt")

        results = {}
        for key, value in queries.items():
            data = pd.read_sql_query(value, connection)
            results[key] = data
        return results
    except Exception as e:
        print(f"Failed to execute queries: {e}")
        sys.exit(1)


def encrypt_data(data: io.BytesIO, key: bytes) -> io.BytesIO:
    """
    Шифрует файл.

    Parameters
    ----------
    data : io.BytesIO
        Байтовый поток (файлы).
    key : bytes
        Ключ шифрования, известный API-приемнику.

    Returns
    -------
    io.BytesIO
        Зашифрованный байтовый поток.
    """
    # Чтение данных из потока
    data.seek(0)
    raw_data = data.read()

    # Шифрование данных
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(raw_data)

    # Запись зашифрованных данных в новый байтовый поток
    encrypted_stream = io.BytesIO(encrypted_data)
    encrypted_stream.seek(0)

    return encrypted_stream


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
    encryption_key = config["encryption_key"].encode()  # Преобразуем ключ в байты

    connection = connect_to_db(db_params)
    results = execute_queries(connection)

    # Сохранение данных в объекты байтового потока (как файл)
    files = {}
    for i, data in enumerate(results.values()):
        buffer: io.BytesIO = io.BytesIO()
        joblib.dump(data, buffer)
        buffer.seek(0)
        # Зашифровываем данные
        encrypted_buffer = encrypt_data(buffer, encryption_key)
        files[f"file{i+1}"] = encrypted_buffer
        if i > 1:
            print("Ошибка загрузки данных: слишком много запросов")
            sys.exit(1)

    # Загрузка данных на сервер FastAPI
    upload_url: str = api_url + "upload-dataframes/"

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
    """Начальная функция для парсинга аргументов командной строки"""
    if len(sys.argv) != 2:
        print("Usage: updater_app <path_to_config>")
        sys.exit(1)

    config_path = sys.argv[1]
    main(config_path)


if __name__ == "__main__":
    run()
