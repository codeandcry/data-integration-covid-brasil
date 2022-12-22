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
        dag_id="clean_data_vacinacao",
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
        if "vacinacao-output" not in existing_buckets:
            client.make_bucket("vacinacao-output")
        print(client.list_buckets())


    check_minio_buckets_step = check_minio_bucket()


    @task(task_id="cleaning_file-vacinacao-covid-pb")
    def cleaning_file_vacinacao_covid_pb_for_output(ds=None, **kwargs):
        vacinacao_obj = client.get_object("vacinacao", "vacinacao-covid-pb.csv")

        vacinacao_df = pd.read_csv(vacinacao_obj, sep=';', low_memory=False)

        vacinacao_df.drop_duplicates(keep='first', inplace=True)

        relevant_columns = [
            'paciente_idade',
            'paciente_dataNascimento',
            'paciente_enumSexoBiologico',
            'paciente_racaCor_valor',
            'paciente_endereco_nmMunicipio',
            'paciente_endereco_uf',
            'estabelecimento_razaoSocial',
            'estabelecimento_municipio_nome',
            'vacina_categoria_nome',
            'vacina_fabricante_nome',
            'vacina_nome'
        ]

        vacinacao_filtered = vacinacao_df.filter(relevant_columns, axis=1)

        vacinacao_csv = vacinacao_filtered.to_csv(index=False, sep=';').encode('utf-8')

        client.put_object("vacinacao-output", "output-vacinacao-covid-pb.csv", data=BytesIO(vacinacao_csv),
                          length=len(vacinacao_csv), content_type='application/csv')


    cleaning_file_vacinacao_covid_pb_for_output_step = cleaning_file_vacinacao_covid_pb_for_output()

check_minio_connection_step >> check_minio_buckets_step
check_minio_buckets_step >> cleaning_file_vacinacao_covid_pb_for_output_step
