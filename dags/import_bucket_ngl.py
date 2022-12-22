from __future__ import annotations

import logging
import sys
import tempfile
import pendulum

from airflow import DAG
from airflow.decorators import task
from minio import Minio

log = logging.getLogger(__name__)

PATH_TO_PYTHON_BINARY = sys.executable

BASE_DIR = tempfile.gettempdir()

client = Minio("172.17.0.1:9000", secure=False, access_key="grupo2", secret_key="admin123")

with DAG(
    dag_id="import_bucket_ngl",
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["minio"],
) as dag:

    @task(task_id="check-minio-connection")
    def check_minio_connection(ds=None, **kwargs):
        client.list_buckets()
        print("Conexão ativa!")
    check_minio_connection_step = check_minio_connection()

    @task(task_id="check-minio-bucket")
    def check_minio_bucket(ds=None, **kwargs):
        existing_buckets = client.list_buckets()
        existing_buckets = [i.name for i in existing_buckets]
        if "ngl" not in existing_buckets:
            client.make_bucket("ngl")
        print(client.list_buckets())
    check_minio_buckets_step = check_minio_bucket()

    @task(task_id="send-file-ngl-2020")
    def send_file_ngl_2020(ds=None, **kwargs):
        client.fput_object("ngl", "ngl-pb-2020.csv", "/opt/notebooks/ngl-pb-2020.csv")
        print("Arquivo enviado com sucesso!")
    send_file_ngl_2020_step = send_file_ngl_2020()

    @task(task_id="send-file-ngl-2021")
    def send_file_ngl_2021(ds=None, **kwargs):
        client.fput_object("ngl", "ngl-pb-2021.csv", "/opt/notebooks/ngl-pb-2021.csv")
        print("Arquivo enviado com sucesso!")
    send_file_ngl_2021_step = send_file_ngl_2021()

    @task(task_id="send-file-ngl-2022")
    def send_file_ngl_2022(ds=None, **kwargs):
        client.fput_object("ngl", "ngl-pb-2022.csv", "/opt/notebooks/ngl-pb-2022.csv")
        print("Arquivo enviado com sucesso!")
    send_file_ngl_2022_step = send_file_ngl_2022()

check_minio_connection_step >> check_minio_buckets_step
check_minio_buckets_step >> send_file_ngl_2020_step
send_file_ngl_2020_step >> send_file_ngl_2021_step
send_file_ngl_2021_step >> send_file_ngl_2022_step