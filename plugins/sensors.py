from airflow.sensors.base_sensor_operator import BaseSensorOperator
from airflow.contrib.hooks.mongo_hook import MongoHook
from airflow.contrib.sensors.mongo_sensor import MongoSensor
from arctic import Arctic


class ArcticSymbolSensor(BaseSensorOperator):
    # check specific symmbol, and metadata exist
    def __init__(self, symbol: str,
                 target_metadata: dict, libname: str,
                 mongo_conn_id="arctic",
                 python_callback=lambda target_meta, metadata: target_meta ==
                 metadata, *arg, **kwargs):

        super(ArcticSymbolSensor, self).__init__(arg, **kwargs)
        self.symbol = symbol
        self.meta = target_metadata
        self.libname = libname
        self.mongo_conn_id = mongo_conn_id

    def poke(self, context):
        hook = MongoHook(self.mongo_conn_id, libname=self.libname)
        client = hook.get_conn()
        store = Arctic(client)

        self.log.info(
            f'Poking for {self.mongo_conn_id}, {self.libname}: {self.symbol}')

        try:
            if store.library_exists(self.libname):
                lib = store.get_library(self.libname)
                if lib.has_symbol(self.symbol):
                    return self.python_call_back(
                        self.meta, lib.read_meta(self.symbol).metadata)
        except OSError:
            return False
        return False
