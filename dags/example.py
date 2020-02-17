from airflow import DAG
from airflow.operators.docker_operator import DockerOperator
from airflow.operators.email_operator import EmailOperator
from datetime import timedelta
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': days_ago(2),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2)}


with DAG("data-task",
         default_args=default_args,
         schedule_interval=timedelta(days=1)) as dag:

    datatask = DockerOperator(
        task_id="update-variables",
        image="eugenepy/akira-data:lastest",
        api_version="3",
        command="update_variables \'{{ prev_execution_date_success }}\' \'{{ ds_nodash }}\'",
        environment={
            "MONGODB_URI": "mongodb://akira_data:akira_data@mongo:27017"},
        xcom_push=True)
