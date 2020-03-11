from airflow import DAG
from airflow.operators.docker_operator import DockerOperator
from airflow.operators.python_operator import (
    PythonOperator, BranchPythonOperator)

from airflow.operators.subdag_operator import SubDagOperator

from datetime import timedelta
import datetime
from airflow.utils.dates import days_ago
from loguru import logger
import json

default_args = {
    'owner': 'eugenepy',
    'start_date': datetime.datetime(2020, 2, 24),
    'email': ['tn00372136@gamil.com'],
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'environment': {
        "MONGODB_URI": "mongodb://akira_data:akira_data@mongo:27017"},
}

POOLS = [
    {
        'pool_id': 0,
        'name': 'daily-fx-rate-update',
        'params': {"start": "2000101"},
        'schedule_interval': "@daily",
    },
    {
        'pool_id': 1,
        'name': 'eco-event-update',
        'schedule_interval': '@daily',
    },
    {
        'pool_id': 2,
        'name': 'eco-event-update',
        'schedule_interval': '@daily',
    }
]
# in each model repo create a special folder, model_archeve
# this is call the airflow shared place, which allow airwlow to sent pull request

pool_id = 0
start = "20200101"
build_dir = "/build"
model_image = "eugenepy/basket:latest"
model_id = "bmk"
nday_retrain = 5
predict_frequency = 10


def retrain_branching(nday_retrain, **ctx):
    if context['execution_date'].day % nday_retrain == 0:
        return "train-model"
    else:
        return "make-predict"


def symbol_fetch_subdag(symbol):
    data_op = DockerOperator(
        task_id="update-data-pool-id",
        image="eugenepy/akira-data:latest",
        api_version="auto",
        command="variable-task update-pool -i {{ params.pool_id }} -s " +
        "{{ params.start }} -e {{ ds_nodash }} -l investingdotcom save " +
        "--filename /build/akira_data.csv",
        params={"start": start, "pool_id": pool_id},
        volumes=[f"{localhost_dir}:{build_dir}"],
        network_mode="akira-project_default",
        docker_url="tcp://socat:2375")

def symbol_compare_existing_database():
    pass
    
def symbol_task(symbol, start, end): # update a signal symbol and keep it up to date.
    # check the Arctic's Status 
    # Check the difference
    # Update the missing data
    pass