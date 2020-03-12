from airflow import DAG
from airflow.operators.docker_operator import DockerOperator
from airflow.operators.python_operator import (
    PythonOperator, BranchPythonOperator)

from airflow.contrib.hooks.mongo_hook import MongoHook

from airflow.operators.subdag_operator import SubDagOperator

from datetime import timedelta
import datetime
from airflow.utils.dates import days_ago
from loguru import logger
import json
import pandas as pd


default_args = {
    'owner': 'eugenepy',
    'start_date': datetime.datetime(2020, 3, 1),
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
        "start": "2000101",
        "symbol_header": 0,
        "field_header": 1,
        "index_col": "date"
    },
    {
        'pool_id': 1,
        'name': 'eco-event-update',
        "start": "2000101",
        "symbol_header": 0,
        "field_header": 1,
        "index_col": "date"
    },
    {
        'pool_id': 2,
        'name': 'intra-day-update',
        "start": "20200201",
        "symbol_header": 0,
        "field_header": 1,
        "index_col": "date"
    }
]
# in each model repo create a special folder, model_archeve
# this is call the airflow shared place, which allow airwlow to sent pull request

def read_csv_and_dump(path, libname):
    
    new_data = pd.read_csv(path, index_col=[0, 1])
    hook = MongoHook(conn_id="arctic_mongo")
    store = hook.get_conn()

    data_ = {}
    if store.library_exists(libname):
        # update from start, in older to overide the start date data point]
        # merge data by replacing
        lib = store.get_library(libname)

        for symbol in data.index.levels[0]:
            new_data = data[symbol]
            store.write(symbol, data=new_data) # simple overide the current data

network = "docker-airflow_default"

def dump_pool_file_to_arctic_subdag(name, pool_id, index_col, symbol_header, field_header, 
                                    start, localhost_dir):
    # we update data at every morning 4AM@utc+8
    build_dir = "/build"
    data_op = DockerOperator(
                        task_id=name,
                        image="eugenepy/akira-data:latest",
                        api_version="auto",
                        command="python -m akira_data variable-task update-pool -i {{ params.pool_id }} -s " +
                        "{{ params.start }} -e {{ ds_nodash }} -l investingdotcom save " + \
                        "--filename {{ params.build_dir }}/{{params.pool_id}}.{{ ds_nodash }}.csv",
                        params={"start": start, "pool_id": pool_id, 
                                "build_dir": build_dir},
                        volumes=[f"{localhost_dir}:{build_dir}"], # save at airflow's container?
                        network_mode=network, # connect2mongodb
                        docker_url="tcp://socat:2375", 
                        auto_remove=True)
    return data_op


def do_all_pools(POOLS, default_args):
    data_ops = []
    localhost_dir = "build"
    
    with DAG(dag_id="update-all-pool", default_args=default_args) as dag:
        for pool in POOLS: 
            op = dump_pool_file_to_arctic_subdag(localhost_dir=localhost_dir, **pool)
            data_ops.append(op)

        #read_data_from = PythonOperator(task_id="read-from-localfile-system", 
        #                                python_callable=read_csv, 
        #                                op_kwargs={"path": localhost_dir, 
        #                                           "index_col": index_col, 
        #                                           "symbol_header": symbol_header,
        #                                           "field_header": field_header}) 
        #data_ops# >> read_data_from

        return dag
    


dag = do_all_pools(POOLS, default_args)