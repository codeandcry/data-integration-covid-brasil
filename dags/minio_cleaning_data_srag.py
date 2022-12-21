from __future__ import annotations

import logging
import sys
import tempfile
from io import BytesIO

import pandas as pd
import pendulum
from airflow import DAG
from airflow.decorators import task
from minio import Minio

log = logging.getLogger(__name__)

PATH_TO_PYTHON_BINARY = sys.executable

BASE_DIR = tempfile.gettempdir()

client = Minio("172.17.0.1:9000", secure=False, access_key="grupo2", secret_key="admin123")

with DAG(
        dag_id="minio_cleaning_data_srag",
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


    @task(task_id="check-minio-bucket-output")
    def check_minio_bucket(ds=None, **kwargs):
        existing_buckets = client.list_buckets()
        existing_buckets = [i.name for i in existing_buckets]
        if "srag-output" not in existing_buckets:
            client.make_bucket("srag-output")
        print(client.list_buckets())


    check_minio_buckets_step = check_minio_bucket()


    @task(task_id="cleaning_file_srag_for_output")
    def cleaning_file_srag_for_output(ds=None, **kwargs):
        srag_2020_obj = client.get_object("srag", "srag-2020.csv")
        srag_2021_obj = client.get_object("srag", "srag-2021.csv")
        srag_2022_obj = client.get_object("srag", "srag-2022.csv")

        srag_2020_df = pd.read_csv(srag_2020_obj, sep=';', low_memory=False)
        srag_2021_df = pd.read_csv(srag_2021_obj, sep=';', low_memory=False)
        srag_2022_df = pd.read_csv(srag_2022_obj, sep=';', low_memory=False)

        srag_2020_df.drop_duplicates(keep='first', inplace=True)
        srag_2021_df.drop_duplicates(keep='first', inplace=True)
        srag_2022_df.drop_duplicates(keep='first', inplace=True)

        srag_2020_df_mask = srag_2020_df['SG_UF_NOT'] == 'PB'
        srag_2020_filtered_df = srag_2020_df[srag_2020_df_mask]

        srag_2021_df_mask = srag_2021_df['SG_UF_NOT'] == 'PB'
        srag_2021_filtered_df = srag_2021_df[srag_2021_df_mask]

        srag_2022_df_mask = srag_2022_df['SG_UF_NOT'] == 'PB'
        srag_2022_filtered_df = srag_2022_df[srag_2022_df_mask]

        srag_2020_csv = srag_2020_filtered_df.to_csv().encode('utf-8')
        srag_2021_csv = srag_2021_filtered_df.to_csv().encode('utf-8')
        srag_2022_csv = srag_2022_filtered_df.to_csv().encode('utf-8')

        srag_2020_csv["College"].fillna("No College", inplace=True)

        client.put_object("srag-output", "output-srag-pb-2020.csv", data=BytesIO(srag_2020_csv),
                          length=len(srag_2020_csv), content_type='application/csv')
        client.put_object("srag-output", "output-srag-pb-2021.csv", data=BytesIO(srag_2021_csv),
                          length=len(srag_2021_csv), content_type='application/csv')
        client.put_object("srag-output", "output-srag-pb-2022.csv", data=BytesIO(srag_2022_csv),
                          length=len(srag_2022_csv), content_type='application/csv')


    cleaning_file_srag_for_output_step = cleaning_file_srag_for_output()

check_minio_connection_step >> check_minio_buckets_step
check_minio_buckets_step >> cleaning_file_srag_for_output_step
