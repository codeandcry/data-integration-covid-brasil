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
# from pandas.io import sql
from sqlalchemy import create_engine
# from pyspark.sql import SparkSession
from pyspark.sql.types import StructType,StructField, StringType, IntegerType,BooleanType,DoubleType

log = logging.getLogger(__name__)

PATH_TO_PYTHON_BINARY = sys.executable

BASE_DIR = tempfile.gettempdir()

client = Minio("172.17.0.1:9000", secure=False, access_key="grupo2", secret_key="admin123")

with DAG(
    dag_id="process_to_datawarehouse",
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["processing"],
) as dag:

    @task(task_id="check_minio_connection")
    def check_minio_connection(ds=None, **kwargs):
        client.list_buckets()
    check_minio_connection_step = check_minio_connection()

    @task(task_id="check_data_warehouse_connection")
    def checkDataWarehouseConnection():
        cnx = create_engine("mysql+pymysql://user:password@172.17.0.1:3306/covid_integration")
        cnx.execute('select @@version as version;')
    check_data_warehouse_connection_step = checkDataWarehouseConnection()

    def processBucketFilesToSingleDataFrame(bucketName):
        dfAll = pd.DataFrame()
        for item in client.list_objects(bucketName, recursive=True):
            print(f'Processing {item.object_name} in bucket={bucketName}')
            file = client.get_object(bucketName, item.object_name, item.object_name)
            df = pd.read_csv(BytesIO(file.read()), sep=";", encoding='utf-8', low_memory=False)
            print(f'{len(df)} rows in {item.object_name}')
            dfAll = pd.concat([dfAll, df], ignore_index=True, sort=False)

        # dfAll = dfAll.fillna('', inplace=True)
        print(f'bucket: {bucketName} rows: {len(dfAll)}')
        return dfAll

    def getNglScheme():
        return StructType([
            StructField("id", IntegerType(), True),
            StructField("dataNotificacao", StringType(), True),
            StructField("dataInicioSintomas", StringType(), True),
            StructField("sintomas", StringType(), True),
            StructField("profissionalSaude", StringType(), True),
            StructField("racaCor", StringType(), True),
            StructField("sexo", StringType(), True),
            StructField("estado", StringType(), True),
            StructField("municipio", StringType(), True),
            StructField("estadoNotificacao", StringType(), True),
            StructField("municipioNotificacao", StringType(), True),
            StructField("dataEncerramento", StringType(), True),
            StructField("evolucaoCaso", StringType(), True),
            StructField("classificacaoFinal", StringType(), True),
            StructField("codigoRecebeuVacina", StringType(), True),
            StructField("dataPrimeiraDose", StringType(), True),
            StructField("dataSegundaDose", StringType(), True),
            StructField("codigoLaboratorioPrimeiraDose", StringType(), True),
            StructField("codigoLaboratorioSegundaDose", StringType(), True),
            StructField("totalTestesRealizados", IntegerType(), True),
            StructField("idade", DoubleType(), True)
        ])

    @task(task_id="process_data_to_datawarehouse")
    def process_data_to_datawarehouse():
        df_ngl = processBucketFilesToSingleDataFrame("ngl-output")
        df_srag = processBucketFilesToSingleDataFrame("srag-output")
        df_vacinacao = processBucketFilesToSingleDataFrame("vacinacao-output")

        # csv = df_ngl.to_csv().encode('utf-8')
        # csv.to

        publishToDataWarehouse("ngl", df_ngl)
        publishToDataWarehouse("srag", df_srag)
        publishToDataWarehouse("vacinacao", df_vacinacao)
    process_data_to_datawarehouse_step = process_data_to_datawarehouse()
        # spark = SparkSession.builder.master("spark://172.17.0.1:7077").appName("process_datasets").getOrCreate()

        # ngl_spark_df = spark.createDataFrame(df_ngl, getNglScheme())
        # ngl_spark_df.createOrReplaceTempView("NGL")

        # srag_spark_df = spark.createDataFrame(df_srag, schemaNgl)
        # srag_spark_df.createOrReplaceTempView("SRAG")
        #
        # vacinacao_spark_df = spark.createDataFrame(df_vacinacao, schemaNgl)
        # vacinacao_spark_df.createOrReplaceTempView("VACINACAO")

        # ngl_spark_df.write.format("jdbc").option("url","jdbc:mysql://172.17.0.1:3306/covid_integraton&useUnicode=true&characterEncoding=UTF-8&useSSL=false") \
        #     .option("driver", "com.mysql.jdbc.Driver").option("dbtable", "students") \
        #     .option("user", "root").option("password", "root").save()
        # .write.csv('dfNglResult.csv')
        # dfResult = spark.sql("select * from NGL n ORDER BY n.dataNotificacao DESC LIMIT 100")
        # dfResult.show()
        # dfResult = pd.read_csv('dfNglResult.csv', sep=",", encoding='utf-8', low_memory=False)
        # publishToDataWarehouse("ngl", dfNglResult)


    def publishToDataWarehouse(tableName, dataFrame):
        # mysql_connection = BaseHook.get_connection('mysql')
        # cnx = create_engine(
        #     mysql_connection.schema + '://' + mysql_connection.login + ':' + mysql_connection.password + '@' + mysql_connection.host)
        cnx = create_engine("mysql+pymysql://user:password@172.17.0.1:3306/covid_integration")

        if cnx.has_table(table_name=tableName):
            cnx.execute('DELETE FROM '+tableName)

        dataFrame.to_sql(tableName, con=cnx, index=False, if_exists='append')
        # dataFrame.to_sql(name=tableName, con=cnx, if_exists='replace')


    check_minio_connection_step >> check_data_warehouse_connection_step >> process_data_to_datawarehouse_step
