# Приложение для обновления ресурсов сервиса сопоставления наименований школ

Updater App — это Python-приложение, предназначенное для выполнения SQL-запросов к базе 
данных PostgreSQL, шифрования полученных данных и их отправки на удаленный API для 
обновления ресурсов этого API (референсные названия школ и их синонимы). 
Приложение упаковано в Docker-контейнер для удобного развертывания и использования. 
Возможно также использование приложения, как пакета Python.

* **Основной сервис сопоставления наименований школ**: 
[School Matcher App](https://school-matcher.streamlit.app/)

## Запуск приложения, как docker-контейнера (без сборки)

1. **Требования**

- Docker установлен и настроен.
- Имеется возможность организации доступа к базе данных PostgreSQL из контейнера 
приложения (см. хинт в конце инструкции).

1. **Скачивание docker-образа:**
   ```sh
   docker pull alekfil/updater-app:0.1.0
   ```

2. **Создание конфигурационных файлов:**

   ```sh
   mkdir /home/<user_name>/uapp_resources
   cd /home/<user_name>/uapp_resources
   touch config.json
   nano config.json
   ```
   Заготовка файла `config.json` представлена в репозитории в файле `config_sample.json`. 
   Внесите данные для работы в файл и сохраните его.
   Возможны трудности в подключении к базе данных из docker (см. раздел "Возможные проблемы").

   ```sh
   cd /home/<user_name>/uapp_resources
   touch queries.txt
   nano queries.txt
   ```
   Заготовка файла `queries.txt` представлена в репозитории в файле `queries_sample.txt`. 
   Внесите данные для работы в файл и сохраните его.

3. **Запуск Docker-контейнера:**

   Запустите контейнер со следующими параметрами

   ```bash
   docker run \
      -v /home/<user_name>/uapp_resources:/app/resources \
      --name <container_name> \
      alekfil/updater_app:0.1.0 \
      resources/config.json \
      resources/queries.txt
   ```
   
4. В логах контейнера должна быть следующая информация

   Команда для просмотра логов контейнера:
   ```sh
   docker logs <container_name>
   ```

   Вывод команды для просмотра логов контейнера:
   ```text
   ...
   /app/updater_app/app.py:98: UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
   data = pd.read_sql_query(value, connection)
   Данные успешно загружены!
   Сервис успешно перезагружен!
   ```

5. **После обновления можно воспользоваться сервисом:**

   ```text
   Откройте браузер и перейдите по адресу [School Matcher App](https://school-matcher.streamlit.app/)
   ```

## Возможные проблемы

### Контейнер не может подключиться к базе данных

Ситуация 1: *Контейнер пытается подключиться к базе данных, расположенной на том же хосте,*
*по его внешнему IP-адресу, но соединение не устанавливается*

Ситуация 2: *Контейнер пытается подключиться к базе данных, расположенной на том же хосте,*
*по localhost, но соединение не устанавливается* 

Причина: Внутри Docker-контейнера localhost указывает на сам контейнер, а не на 
хост-машину. При попытке подключиться к базе данных на хосте по её внешнему IP-адресу, 
соединение может быть заблокировано по разным причинам (например, фаерволом 
или сетевыми правилами).

**Решение 1. Использование `host.docker.internal`.**

Linux: Для подключения к базе данных на хосте можно использовать IP-адрес интерфейса Docker bridge. 

Команда для определения IP-адреса интерфейса Docker bridge:

   ```sh
   ip addr show docker0
   ```

Вывод:
   ```text
   4: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default
      link/ether 02:42:ac:11:00:01 brd ff:ff:ff:ff:ff:ff
      inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
         valid_lft forever preferred_lft forever
   ```

IP-адрес хоста для контейнера будет 172.17.0.1

Windows и macOS: можно использовать host.docker.internal — специальное DNS-имя, которое 
автоматически настроено на хост-машину из контейнера Docker.

Указанные данные необходимо прописать в config.json:
 
```text
{
   "db_params": {
      "dbname": "dbname",
      "user": "user",
      "password": "password",
      "host": "172.17.0.1",
      "port": "port"
   },
   "api_url": "http://api_host:port/",
   "api_key": "kAe-CmN-api_key-J7J",
   "encryption_key": "encryption_key"
}
```

или

```text
{
   "db_params": {
      "dbname": "dbname",
      "user": "user",
      "password": "password",
      "host": "host.docker.internal",
      "port": "port"
   },
   "api_url": "http://api_host:port/",
   "api_key": "kAe-CmN-api_key-J7J",
   "encryption_key": "encryption_key"
}
```

**Решение 2. Использование пользовательской сети, в которой запущены оба контейнера**
**— база данных и приложение.**

Необходимо использовать параметр --network при запуске контейнера с указанием 
пользовательской сети, в которой запущен контейнер базы данных. Это позволит контейнерам 
напрямую взаимодействовать друг с другом через общую виртуальную сеть Docker. 

Запустите контейнер со следующими параметрами:

```bash
docker run \
   -v /home/<user_name>/uapp_resources:/app/resources \
   --name <container_name> \
   --network <network_name> \
   alekfil/updater_app:0.1.0 \
   resources/config.json \
   resources/queries.txt
```

Теперь контейнер с приложением сможет подключиться к базе данных, используя имя контейнера базы данных в качестве хоста. В конфигурационном файле config.json необходимо указать имя контейнера базы данных в поле host.


```text
{
   "db_params": {
      "dbname": "dbname",
      "user": "user",
      "password": "password",
      "host": "<db_container_name>",
      "port": "port"
   },
   "api_url": "http://api_host:port/",
   "api_key": "kAe-CmN-api_key-J7J",
   "encryption_key": "encryption_key"
}
```

**Решение 3. Использование параметра --network="host"**

Можно сделать так, чтобы контейнер был полностью интегрирован в сеть хоста 
(например, чтобы использовать localhost для подключения к сервисам на хосте). Для этого
необходимо использовать параметр --network="host" при запуске контейнера:

```bash
docker run \
   -v /home/<user_name>/uapp_resources:/app/resources \
   --name <container_name> \
   --network="host" \
   alekfil/updater_app:0.1.0 \
   resources/config.json \
   resources/queries.txt
```

**Этот метод уменьшает изоляцию между контейнером и хостом, что может иметь последствия для безопасности.** Теперь контейнер с приложением сможет подключиться к базе данных, используя localhost в качестве хоста. В конфигурационном файле config.json необходимо указать:


```text
{
   "db_params": {
      "dbname": "dbname",
      "user": "user",
      "password": "password",
      "host": "localhost",
      "port": "port"
   },
   "api_url": "http://api_host:port/",
   "api_key": "kAe-CmN-api_key-J7J",
   "encryption_key": "encryption_key"
}
```

## Запуск приложения как пакета из файла .whl

1. **Клонирование репозитория с проектом:**

   ```bash
   git clone https://github.com/alekfil/updater_app.git
   cd updater_app
   ```

2. **Установка пакета:**

   ```bash
   pip install dist/updater_app-0.1.0-py3-none-any.whl
   ```

3. **Создание конфигурационных файлов:**

   ```sh
   mkdir /home/<user_name>/uapp_resources
   cd /home/<user_name>/uapp_resources
   touch config.json
   nano config.json
   ```
   Заготовка файла `config.json` представлена в репозитории в файле `config_sample.json`. 
   Внесите данные для работы в файл и сохраните его.

   ```sh
   cd /home/<user_name>/uapp_resources
   touch queries.txt
   nano queries.txt
   ```
   Заготовка файла `queries.txt` представлена в репозитории в файле `queries_sample.txt`. 
   Внесите данные для работы в файл и сохраните его.


4. **Запуск приложения:**

   Используйте в качестве параметров запуска пути к файлам `config.json` и `queries.txt`.

   ```bash
   updater_app /path/to/config.json /path/to/queries.txt
   ```

## Контакты
Автор проекта - Алексей Филатов: [telegram @alekFil](https://t.me/alekfil).

