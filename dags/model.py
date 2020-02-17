from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta
from airflow.operators.docker_operator import DockerOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor

default_args = {
    'owner': 'airflow',
    'description': 'Use of the DockerOperator',
    'depend_on_past': False,
    'start_date': datetime(2020, 1, 3),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

with DAG('smirks', default_args=default_args, schedule_interval="5 * * * *", 
         catchup=False) as dag:
    t1 = ExternalTaskSensor(task_id="update_pool",
                            external_dag_id="daiy_symbol_update")

    t2 = DockerOperator(
        task_id='smirks_update',
        image='akira-model:latest',
        api_version='auto',
        auto_remove=True,
        command="python -m akira.model.smirks fit {start} {end}",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge"
    )

    t2 = DockerOperator(
        task_id='smirks_report',
        image='akira-model:latest',
        api_version='auto',
        auto_remove=True,
        command="python -m akira.model.smirks report {end}",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge"
    )

    t1 >> t2
