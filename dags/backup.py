from datetime import timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import ShortCircuitOperator
from airflow.operators.docker_operator import DockerOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": days_ago(2),
    "email": ["airflow@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

target_path = ["mongodata:/data/db"]


def docker_move_subdag(host_top_dir, input_path, output_path):
    host_path = f"{host_top_dir}/{input_path}"

    with DAG("docker_backup_db", default_args=default_args,
             schedule_interval=timedelta(minutes=10)) as dag:

        locate_file_cmd = """
            sleep 10
            find {{params.source_location}} -type f  -printf "%f\n" | head -1
        """

        t_view = BashOperator(
            task_id="view_file",
            bash_command=locate_file_cmd,
            xcom_push=True,
            params={"source_location": host_path}
        )

        def is_data_available(*args, **kwargs):
            ti = kwargs["ti"]
            data = ti.xcom_pull(key=None, task_ids="view_file")
            return data is not None

        t_is_data_available = ShortCircuitOperator(
            task_id="check_if_data_available",
            python_callable=is_data_available
        )

        t_move = DockerOperator(
            api_version="auto",
            docker_url="tcp://socat:2375",  # replace it with swarm/docker endpoint
            image="centos:latest",
            network_mode="bridge",
            volumes=[
                f"{host_path}:{input_path}",
                f"{host_top_dir}/{input_path}:{output_path}",
            ],
            command=[
                "/bin/bash",
                "-c",
                "/bin/sleep 30; "
                "/bin/mv {{params.source_location}}/{{ ti.xcom_pull('view_file') }} {{params.target_location}};"
                "/bin/echo '{{params.target_location}}/{{ ti.xcom_pull('view_file') }}';",
            ],
            task_id="move_data",
            xcom_push=True,
            params={"source_location": f"{input_path}",
                    "target_location": f"{output_path}"},
        )

        print_templated_cmd = """
            cat {{ ti.xcom_pull('move_data') }}
        """

        t_print = DockerOperator(
            api_version="auto",
            docker_url="tcp://socat:2375",
            image="centos:latest",
            volumes=[f"{host_top_dir}/{output_path}:{output_path}"],
            command=print_templated_cmd,
            task_id="print",
        )

        t_view.set_downstream(t_is_data_available)
        t_is_data_available.set_downstream(t_move)
        t_move.set_downstream(t_print)


def backup():
    # backup:
        # docker run --rm --volumes-from akira-project_mongo_1 -v $(pwd)/akira-project/backup:/backup centos bash -c "cd /data/db && tar cvf /backup/akira-mongo.tar ."
        # docker run --rm --volumes-from akira-project_mongo_1 -v $(pwd)/akira-project/backup:/backup centos bash -c "cd /data/db && tar xvf /backup/akira-mongo.tar --strip 1"
    pass
