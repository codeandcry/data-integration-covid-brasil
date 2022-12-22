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
        dag_id="clean_data_ngl",
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
        if "ngl-output" not in existing_buckets:
            client.make_bucket("ngl-output")
        print(client.list_buckets())


    check_minio_buckets_step = check_minio_bucket()


    @task(task_id="cleaning_file_ngl_for_output")
    def cleaning_file_ngl_for_output(ds=None, **kwargs):
        ngl_pb_2020_obj = client.get_object("ngl", "ngl-pb-2020.csv")
        ngl_pb_2021_obj = client.get_object("ngl", "ngl-pb-2021.csv")
        ngl_pb_2022_obj = client.get_object("ngl", "ngl-pb-2022.csv")

        ngl_pb_2020_df = pd.read_csv(ngl_pb_2020_obj, sep=';', low_memory=False)
        ngl_pb_2021_df = pd.read_csv(ngl_pb_2021_obj, sep=';', low_memory=False)
        ngl_pb_2022_df = pd.read_csv(ngl_pb_2022_obj, sep=';', low_memory=False)

        ngl_pb_2020_df.drop_duplicates(keep='first', inplace=True)
        ngl_pb_2021_df.drop_duplicates(keep='first', inplace=True)
        ngl_pb_2022_df.drop_duplicates(keep='first', inplace=True)

        relevant_columns = ['dataNotificacao', 'dataInicioSintomas', 'sintomas', 'profissionalSaude', 'racaCor', 'sexo',
               'estado','municipio', 'estadoNotificacao', 'municipioNotificacao', 'dataEncerramento', 'evolucaoCaso',
               'classificacaoFinal', 'codigoRecebeuVacina', 'dataPrimeiraDose', 'dataSegundaDose', 'codigoLaboratorioPrimeiraDose',
                         'codigoLaboratorioSegundaDose','totalTestesRealizados', 'idade']

        ngl_pb_2020_df = ngl_pb_2020_df.filter(relevant_columns,axis=1)
        ngl_pb_2021_df = ngl_pb_2021_df.filter(relevant_columns, axis=1)
        ngl_pb_2022_df = ngl_pb_2022_df.filter(relevant_columns, axis=1)

        ngl_pb_2020_csv = ngl_pb_2020_df.to_csv(index=False, sep=';').encode('utf-8')
        ngl_pb_2021_csv = ngl_pb_2021_df.to_csv(index=False, sep=';').encode('utf-8')
        ngl_pb_2022_csv = ngl_pb_2022_df.to_csv(index=False, sep=';').encode('utf-8')

        client.put_object("ngl-output", "output-ngl-pb-2020.csv", data=BytesIO(ngl_pb_2020_csv),
                          length=len(ngl_pb_2020_csv), content_type='application/csv')
        client.put_object("ngl-output", "output-ngl-pb-2021.csv", data=BytesIO(ngl_pb_2021_csv),
                          length=len(ngl_pb_2021_csv), content_type='application/csv')
        client.put_object("ngl-output", "output-ngl-pb-2022.csv", data=BytesIO(ngl_pb_2022_csv),
                          length=len(ngl_pb_2022_csv), content_type='application/csv')


    cleaning_file_ngl_for_output_step = cleaning_file_ngl_for_output()

check_minio_connection_step >> check_minio_buckets_step
check_minio_buckets_step >> cleaning_file_ngl_for_output_step