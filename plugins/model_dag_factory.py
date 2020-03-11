def model_update_dag_factory(model_id, data_spec_path, model_spec_path,
                             retrain_interval, trading_interval, repo, image_name, tag):
    """The Model update dag should contains a commandline interface
    """
    update_schema_tag = "extensive"

    with DAG(f"update-model-task:{update_schema_tag}",
             default_args=default_args,
             schedule_interval="@daily", catchup=True) as dag:

        datatask = []

        # filter and map
        for symbol in info_symbols:
            sudag = _data_symbol_dag_factory(symbol, default_args)
            datatask.append(sudag)

        data_tasks = SubDagOperator(
            task_id='data_symbol_tasks',
            subdag=datatask,
            default_args=default_args,
        )
        # checkupdate

        # rebuild model

        PythonBranchOperator(task_id="check-if-retrain", python_callable=
                             provide_context=True)
        train_op = DockerOperator(
            task_id=f"{model_id}-train",
            image=f"{image_name}:{tag}",
            api_version="auto",
            command="update --model_id bmk " +
            "--input_path {{ macros.ds_format(macros.ds_add(ds, -1), '%Y-%m-%d', '%Y%m%d') }} -o {{ ds_nodash }}",
            volumes={},
            docker_url="tcp://socat:2375")

        # dumping predction
        predict = DockerOperator(
            task_id=f"{model_id}-predict",
            image=f"{image_name}:{tag}",
            api_version="auto",
            command="predict --model_id bmk " +
            "--input_pkl {{ pkl_path }} -o {{ position_file_path }}",
            volumes={},
            docker_url="tcp://socat:2375")

        # trading-databse, using elasticsearch
        data_tasks >> train_op >> predict

    return dag




def generate_datatask_dag_factory(pool_spec):
    with DAG("update-data-task",
             default_args=default_args,
             schedule_interval="@daily", catchup=True) as dag:
        # extract required datetime_range
        # pull data from arctic
        # update data
        get_all = DockerOperator(
            task_id="update-data-pool-id",
            image="eugenepy/akira-data:latest",
            api_version="auto",
            command="variable-task update-pool -i {{ params.pool_id }} -s " +
            "{{ macros.ds_format(macros.ds_add(ds, -1), '%Y-%m-%d', '%Y%m%d') }} -e {{ ds_nodash }}",
            docker_url="tcp://socat:2375")

# using filter to genetate dynamic dag


def _data_symbol_dag_factory(symbol, pool_id, schedule_interval, default_args):
    # check symbol is up-to-date
    # check symbol not or it's up to date

    with DAG("update-symbol-task",
             default_args=default_args,
             schedule_interval="@daily", catchup=True) as dag:

        sensor_op = ArcticSymbolDataSensor(symbol)
        branching_op = PythonBranchOperator(task_id="branching",
                                            provide_context=True)
        # If update-to-date
        do_nothing = DummyOperation()

        # If not up-to-date-update
        query_op = DockerOperator(
            task_id="querying-arctic",
            image="eugenepy/akira-data:latest",
            api_version="auto",
            docker_url="tcp://socat:2375")

        # looking missing date then update the data to today
        update_op = DockerOperator(
            task_id="querying-arctic",
            image="eugenepy/akira-data:latest",
            api_version="auto",
            docker_url="tcp://socat:2375")

        dumping_op = DockerOperator(
            task_id="querying-arctic",
            image="eugenepy/akira-data:latest",
            api_version="auto",
            docker_url="tcp://socat:2375")
    return dag