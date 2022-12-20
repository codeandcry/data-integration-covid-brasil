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
    dag_id="processing_datasets",
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["processing"],
) as dag:

    @task(task_id="check-minio-connection")
    def check_minio_connection(ds=None, **kwargs):
        client.list_buckets()
        print("Conexão ativa!")
    check_minio_connection_step = check_minio_connection()

    @task(task_id="get-ngl-output-file")
    def get_ngl_output_file(ds=None, **kwargs):
        arquivo = client.get_object("ngl-output", "ngl-output.csv")
        df = pd.read_csv(BytesIO(arquivo.read()))
        print(df.head())
    get_ngl_output_file_step = get_ngl_output_file()

    @task(task_id="get-srag-output-file")
    def get_srag_output_file(ds=None, **kwargs):
        arquivo = client.get_object("srag-output", "srag-output.csv")
        df = pd.read_csv(BytesIO(arquivo.read()))
        print(df.head())
    get_srag_output_file_step = get_srag_output_file()

    @task(task_id="get-vacinacao-output-file")
    def get_vacinacao_output_file(ds=None, **kwargs):
        arquivo = client.get_object("vacinacao-output", "vacinacao-output.csv")
        df = pd.read_csv(BytesIO(arquivo.read()))
        print(df.head())
    get_vacinacao_output_file_step = get_vacinacao_output_file()


check_minio_connection_step >> get_ngl_output_file_step
get_ngl_output_file_step >> get_srag_output_file_step
get_srag_output_file_step >> get_vacinacao_output_file_step