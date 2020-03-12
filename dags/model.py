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

target_dir = ".akira" # the directory that akira-trend to generate arctifact
git_commit_name = "[AKIRA-CI/CD]"

def train_model(model_image, model_id, pool_id, start, default_args):

    with DAG("update-data-task",
             default_args=default_args,
             schedule_interval="@daily", catchup=True) as dag:

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

        train_op = DockerOperator(
            task_id="train-model",
            image=model_image,
            api_version="auto",
            command="make -f Makefile.model train_bmk",
            volumes=[f"{localhost_dir}:{build_dir}"],
            network_mode="akira-project_default",
            docker_url="tcp://socat:2375")
        data_op >> train_op
        return dag


def make_prediction(model_id, pool_id, default_args,
                    localhost_dir, build_dir, start=None):

    with DAG("update-data-task",
             default_args=default_args,
             schedule_interval="@daily", catchup=True) as dag:

        data_op = DockerOperator(
            task_id="update-data-pool-id",
            image="eugenepy/akira-data:latest",
            api_version="auto",
            command="variable-task update-pool -i {{ params.pool_id }} -s " +
            "{{ (execution_date - macros.timedeltas(days=1)).strftime('%Y%m%d') }" +
            " -e {{ execution_date.strftime('%Y%d%m') }} -l investingdotcom save " +
            "--filename /build/akira_data.test.csv",
            params={"pool_id": pool_id},
            volumes=[f"{localhost_dir}:{build_dir}"],
            network_mode="akira-project_default",
            docker_url="tcp://socat:2375")

        predict_op = DockerOperator(
            task_id="train-model",
            image="eugenepy/basket:latest",
            api_version="auto",
            command="python3 -m baksets predict -m /build/bmk.pkl " +
            "-i /build/akira_data.test.csv -o /build/akira_data.predict.csv",
            volumes=[f"{localhost_dir}:{build_dir}"],
            network_mode="akira-project_default",
            docker_url="tcp://socat:2375")
        data_op >> predict_op
        return dag

def model_routine(nday_retrain, default_args):
    with DAG("update-data-task",
            default_args=default_args,
            schedule_interval="@daily", catchup=True) as dag:
        # We can generate the DAG from akira-test

        branching_op = BranchPythonOperator(
            task_id="check-if-retrain", provide_context=True,
            op_args={"nday_retrain": nday_retrain},
            python_callable=retrain_branching)

        subdag = train_model(model_image=model_image,
                            model_id=model_id, pool_id=pool_id,
                            start=start, default_args=default_args)

        train_op = SubDagOperator(task_id="train-model", subdag=subdag)

        subdag = make_prediction(model_image=model_image,
                                model_id=model_id, pool_id=pool_id,
                                start=start, default_args=default_args)
        predict_op = SubDagOperator(task_id="making-prediction", subdag=subdag)

        branching_op >> [train_op, predict_op]
        return dag

model_spec = [{
    "model_id": "bmk",
    "image": "eugenepy/basket",
    "tag": "latest",
    "repo": "https://github.com/EugenePY/basket.git",
    "repo_path": "./basket",
    # this will be generate to your repo
    "model_home": "./basket/.airflow.space:/basket_home",
    "rebuild": "",
    "trading_freq": "",
    "symbols": ["USDKRW INVT Curncy", "USDTWD INVT Curncy",
                "USDSGD INVT INVT Curncy"]
}]