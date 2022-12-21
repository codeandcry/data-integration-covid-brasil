from __future__ import annotations

import logging
import sys
import tempfile
import pendulum

from airflow import DAG
from airflow.decorators import task
from minio import Minio
from io import BytesIO
import pandas as pd
from sqlalchemy import create_engine
from airflow.hooks.base import BaseHook

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

    @task(task_id="check_minio_connection")
    def check_minio_connection(ds=None, **kwargs):
        client.list_buckets()
        print("Conexão ativa!")
    check_minio_connection_step = check_minio_connection()

    @task(task_id="check_data_warehouse_connection")
    def checkDataWarehouseConnection():
        dataWarehouseConn = BaseHook.get_connection('data_warehouse_connection')
        cnx = create_engine(
            dataWarehouseConn.schema + '://' + dataWarehouseConn.login + ':' + dataWarehouseConn.password + '@' + dataWarehouseConn.host)
        cnx.execute('select @@version as version;')
    check_data_warehouse_connection_step = checkDataWarehouseConnection()

    def processBucketFilesToSingleDataFrame(bucketName):
        dfAll = pd.DataFrame()
        for item in client.list_objects(bucketName, recursive=True):
            print(f'Processing {item.object_name} in bucket={bucketName}')
            file = client.get_object(bucketName, item.object_name, item.object_name)
            df = pd.read_csv(BytesIO(file.read()), sep=";", encoding='utf-8', low_memory=False)
            print(f'{len(df)} rows in "{item.object_name}')
            dfAll = pd.concat([dfAll, df], ignore_index=True, sort=False)

        dfAll.fillna('', inplace=True)
        print(f'bucket: {bucketName} rows: {len(dfAll)}')
        return dfAll

    @task(task_id="get_ngl_output")
    def getNglOutput():
        return processBucketFilesToSingleDataFrame("ngl-output")
    get_ngl_output_step = getNglOutput()

    @task(task_id="get_srag_output")
    def getSragOutput():
        return processBucketFilesToSingleDataFrame("srag-output")
    get_srag_output_step = getSragOutput()

    @task(task_id="get_vacinacao_output")
    def getVacinacaoOutput():
        return processBucketFilesToSingleDataFrame("vacinacao-output")
    get_vacinacao_output_step = getVacinacaoOutput()

    @task(task_id="merge_datasets")
    def mergeDatasets(**kwargs):
        ti = kwargs['ti']
        dfNglRetorno = ti.xcom_pull(task_ids='get_ngl_output')
        dfSragRetorno = ti.xcom_pull(task_ids='get_srag_output')
        dfVacinacaoRetorno = ti.xcom_pull(task_ids='get_vacinacao_output')
        print(f'count {len(dfNglRetorno)}')
        print(f'count {len(dfSragRetorno)}')
        print(f'count {len(dfVacinacaoRetorno)}')
        print(f'merge datasets executed')
    merge_data_step = mergeDatasets()

    # @task(task_id="publish_to_data_warehouse")
    # def publishToDataWarehouse(tableName, dataFrame):
    #     mysql_connection = BaseHook.get_connection('data_warehouse_connection')
    #     cnx = create_engine(
    #         mysql_connection.schema + '://' + mysql_connection.login + ':' + mysql_connection.password + '@' + mysql_connection.host)
    #     dataFrame.to_sql(name=tableName, con=cnx, if_exists='replace')
    # publish_to_data_warehouse_step = publishToDataWarehouse()



check_minio_connection_step >> get_ngl_output_step >> get_srag_output_step >> get_vacinacao_output_step >> merge_data_step >> check_data_warehouse_connection_step
