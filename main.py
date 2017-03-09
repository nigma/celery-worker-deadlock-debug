# coding=utf-8

import datetime

from celery import Celery
from celery.utils.log import get_task_logger


class Config:
    accept_content = ['json']

    task_serializer = 'json'
    task_compression = 'gzip'
    task_ignore_result = True
    task_track_started = True

    task_time_limit = datetime.timedelta(minutes=10).total_seconds()
    task_acks_late = True
    task_publish_retry = True
    # task_send_sent_event = True

    result_backend = 'redis://redis:6379/2'
    result_expires = datetime.timedelta(days=1)

    broker_pool_limit = 10
    broker_connection_timeout = 4
    broker_connection_max_retries = 100
    broker_connection_retry = True
    broker_heartbeat = 20

    worker_concurrency = 5
    worker_prefetch_multiplier = 1

    worker_lost_wait = 10.0
    worker_max_memory_per_child = None
    worker_max_tasks_per_child = 10
    worker_disable_rate_limits = False
    worker_send_task_events = True
    worker_hijack_root_logger = True

    worker_pool = 'prefork'


class RedisConfig(Config):
    broker_url = 'redis://redis:6379/1'
    broker_transport_options = {'socket_timeout': 90, 'socket_keepalive': True}

    # Maximum number of connections available in the Redis connection pool used for sending and retrieving results.
    redis_max_connections = 10

    # Socket timeout for connections to Redis from the result backend in seconds (int/float)
    redis_socket_connect_timeout = None

    # Socket timeout for reading/writing operations to the Redis server in seconds (int/float), used by the redis result backend.
    redis_socket_timeout = 10


class RabbitMQConfig(Config):
    broker_url = 'amqp://guest:guest@rabbitmq:5672//'


app = Celery(__name__)
app.config_from_object(RedisConfig)

logger = get_task_logger(__name__)


@app.task(name='sample_task')
def task(num):
    logger.warning('Running task {}'.format(num))


if __name__ == '__main__':
    print(app.conf.humanize(with_defaults=True, censored=False))

    for i in range(1000):
        task.apply_async(args=(i,))
