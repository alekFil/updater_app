from setuptools import find_packages, setup

setup(
    name="updater_app",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "cryptography",
        "joblib",
        "pandas",
        "psycopg2",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "updater_app=updater_app.app:run",
        ],
    },
)
