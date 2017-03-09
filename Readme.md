## Overview

Celery workers freeze when using Redis broker and `hiredis` package is present.

This is/was causing issues with worker pool running on AWS ElasticBeanstalk Docker with AWS ElastiCache Redis broker as reported in https://gist.github.com/nigma/a4e572a3c3aaf50395a704b05b480bbf.


## Environment

1. Celery 4.0.2 from master branch (see `requirements.txt`)
2. Redis 3.2.4 or 3.2.8
3. `hiredis` package 0.2.0 or `5cfdf41` (current master)
4. Sample configuration in `main.py`

```
celery worker --app main --hostname default@%h --events --loglevel info -O fair
```

## About hiredis

See https://github.com/andymccurdy/redis-py#parsers

`redis-py` is a library used by Celery to connect with redis server and  ships with two parser classes, the PythonParser and the HiredisParser. By default, redis-py will attempt to use the HiredisParser if you have the hiredis module installed and will fallback to the PythonParser otherwise.

Hiredis is a C library maintained by the core Redis team. Using Hiredis can provide up to a 10x speed improvement in parsing responses from the Redis server.

## Reproducing the issue

Provided is `docker-compose.yml` env definition and celery settings + app (`main.py`).

To build & run the service and populate tasks queue run:

```
make clean && make run
```


## Problems observed

1. Celery worker pool freezes and gets offline without any error message after reaching `worker_max_tasks_per_child` processed tasks.
2. Celery freezes with 100% CPU usage when workers try to exit after reaching `worker_max_tasks_per_child` processed tasks.
    - `redis.exceptions.ConnectionError: Error 32 while writing to socket. Broken pipe.`
3. Worker pool gets offline after workers reach `worker_max_tasks_per_child` processed tasks, resumes after broker connection timeout and then crashes after next batch of tasks:
    - Connection to broker lost / `BrokenPipeError`
    - `billiard.exceptions.WorkerLostError: Worker exited prematurely: exitcode 155.`
    - `redis.exceptions.ConnectionError: Error while reading from socket: ('Connection closed by server.',)`
    - `redis.exceptions.TimeoutError: Timeout reading from socket`
    - `redis.exceptions.ConnectionError: Error 32 while writing to socket. Broken pipe.`
    - Kombu: `Unrecoverable error: AttributeError("'NoneType' object has no attribute 'fileno'",)`


Above problems were not observed when `hiredis` package is not present in the system.

Originally ElasticBeanstalk/ElastiCache or NewRelic monitoring agent was suspected of causing worker errors but that hypothesis was ruled out while testing various combinations of software stack.


## Sample tracebacks

```
[2017-03-09 00:21:57,427: WARNING/PoolWorker-3] 48
[2017-03-09 00:21:57,427: WARNING/PoolWorker-4] 49
[2017-03-09 00:21:57,427: INFO/PoolWorker-3] Task sample_task[3e2599e8-461e-4098-b79e-49baf9db42ec] succeeded in 0.00025000300956889987s: None
[2017-03-09 00:21:57,427: INFO/PoolWorker-4] Task sample_task[6f5d6d97-105f-4299-9e8c-e7cd901f4626] succeeded in 0.0003138270112685859s: None
[2017-03-09 00:21:57,429: INFO/MainProcess] Received task: sample_task[895824ff-adcd-4120-9738-18b66672adac]
[2017-03-09 00:21:57,514: WARNING/MainProcess] consumer: Connection to broker lost. Trying to re-establish the connection...
Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 543, in send_packed_command
    self._sock.sendall(item)
BrokenPipeError: [Errno 32] Broken pipe

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 320, in start
    blueprint.start(self)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 119, in start
    step.start(parent)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 596, in start
    c.loop(*c.loop_args())
  File "/usr/local/lib/python3.6/site-packages/celery/worker/loops.py", line 88, in asynloop
    next(loop)
  File "/usr/local/lib/python3.6/site-packages/kombu/async/hub.py", line 277, in create_loop
    tick_callback()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 1032, in on_poll_start
    cycle_poll_start()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 315, in on_poll_start
    self._register_BRPOP(channel)
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 301, in _register_BRPOP
    channel._brpop_start()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 707, in _brpop_start
    self.client.connection.send_command('BRPOP', *keys)
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 563, in send_command
    self.send_packed_command(self.pack_command(*args))
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 556, in send_packed_command
    (errno, errmsg))
redis.exceptions.ConnectionError: Error 32 while writing to socket. Broken pipe.
[2017-03-09 00:21:57,516: WARNING/MainProcess] Restoring 3 unacknowledged message(s)
[2017-03-09 00:21:57,582: INFO/MainProcess] Connected to redis://redis:6379/1
[2017-03-09 00:21:57,591: INFO/MainProcess] mingle: searching for neighbors
[2017-03-09 00:21:57,596: CRITICAL/MainProcess] Unrecoverable error: KeyError(25,)
Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/celery/worker/worker.py", line 203, in start
    self.blueprint.start(self)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 119, in start
    step.start(parent)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 370, in start
    return self.obj.start()
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 320, in start
    blueprint.start(self)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 119, in start
    step.start(parent)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/mingle.py", line 38, in start
    self.sync(c)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/mingle.py", line 42, in sync
    replies = self.send_hello(c)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/mingle.py", line 55, in send_hello
    replies = inspect.hello(c.hostname, our_revoked._data) or {}
  File "/usr/local/lib/python3.6/site-packages/celery/app/control.py", line 129, in hello
    return self._request('hello', from_node=from_node, revoked=revoked)
  File "/usr/local/lib/python3.6/site-packages/celery/app/control.py", line 81, in _request
    timeout=self.timeout, reply=True,
  File "/usr/local/lib/python3.6/site-packages/celery/app/control.py", line 436, in broadcast
    limit, callback, channel=channel,
  File "/usr/local/lib/python3.6/site-packages/kombu/pidbox.py", line 321, in _broadcast
    channel=chan)
  File "/usr/local/lib/python3.6/site-packages/kombu/pidbox.py", line 360, in _collect
    self.connection.drain_events(timeout=timeout)
  File "/usr/local/lib/python3.6/site-packages/kombu/connection.py", line 301, in drain_events
    return self.transport.drain_events(self.connection, **kwargs)
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/virtual/base.py", line 961, in drain_events
    get(self._deliver, timeout=timeout)
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 359, in get
    ret = self.handle_event(fileno, event)
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 341, in handle_event
    return self.on_readable(fileno), self
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 335, in on_readable
    chan, type = self._fd_to_chan[fileno]
KeyError: 25
```

---

```
[2017-03-09 00:35:57,253: INFO/MainProcess] Received task: sample_task[83c3db81-5d15-4623-91d3-82f82ce06a8f]
[2017-03-09 00:35:57,255: INFO/MainProcess] Received task: sample_task[28c3b229-49c8-4358-a960-c2bfcd9db7a6]
[2017-03-09 00:35:57,256: WARNING/PoolWorker-1] 49
[2017-03-09 00:35:57,256: INFO/PoolWorker-1] Task sample_task[28c3b229-49c8-4358-a960-c2bfcd9db7a6] succeeded in 0.00023082600091584027s: None
[2017-03-09 00:35:57,257: WARNING/PoolWorker-5] 48
[2017-03-09 00:35:57,257: INFO/PoolWorker-5] Task sample_task[83c3db81-5d15-4623-91d3-82f82ce06a8f] succeeded in 0.0003662639937829226s: None
[2017-03-09 00:35:57,258: INFO/MainProcess] Received task: sample_task[51d998dc-43ce-4ad7-8c6e-7956ab6a6370]
[2017-03-09 00:35:57,376: WARNING/MainProcess] consumer: Connection to broker lost. Trying to re-establish the connection...
Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 543, in send_packed_command
    self._sock.sendall(item)
BrokenPipeError: [Errno 32] Broken pipe

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 320, in start
    blueprint.start(self)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 119, in start
    step.start(parent)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 596, in start
    c.loop(*c.loop_args())
  File "/usr/local/lib/python3.6/site-packages/celery/worker/loops.py", line 88, in asynloop
    next(loop)
  File "/usr/local/lib/python3.6/site-packages/kombu/async/hub.py", line 277, in create_loop
    tick_callback()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 1032, in on_poll_start
    cycle_poll_start()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 315, in on_poll_start
    self._register_BRPOP(channel)
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 301, in _register_BRPOP
    channel._brpop_start()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 707, in _brpop_start
    self.client.connection.send_command('BRPOP', *keys)
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 563, in send_command
    self.send_packed_command(self.pack_command(*args))
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 556, in send_packed_command
    (errno, errmsg))
redis.exceptions.ConnectionError: Error 32 while writing to socket. Broken pipe.
[2017-03-09 00:35:57,379: WARNING/MainProcess] Restoring 3 unacknowledged message(s)
[2017-03-09 00:35:57,398: INFO/MainProcess] Connected to redis://redis:6379/1
[2017-03-09 00:35:57,406: INFO/MainProcess] mingle: searching for neighbors
[2017-03-09 00:35:58,413: INFO/MainProcess] mingle: all alone
[2017-03-09 00:35:58,451: ERROR/MainProcess] Task handler raised error: WorkerLostError('Worker exited prematurely: exitcode 155.',)
Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/billiard/pool.py", line 1224, in mark_as_worker_lost
    human_status(exitcode)),
billiard.exceptions.WorkerLostError: Worker exited prematurely: exitcode 155.
[2017-03-09 00:35:58,454: ERROR/MainProcess] Task handler raised error: WorkerLostError('Worker exited prematurely: exitcode 155.',)
Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/billiard/pool.py", line 1224, in mark_as_worker_lost
    human_status(exitcode)),
billiard.exceptions.WorkerLostError: Worker exited prematurely: exitcode 155.
[2017-03-09 00:37:28,537: WARNING/MainProcess] consumer: Connection to broker lost. Trying to re-establish the connection...
Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 346, in read_response
    raise socket.error(SERVER_CLOSED_CONNECTION_ERROR)
OSError: Connection closed by server.

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/redis/client.py", line 2165, in _execute
    return command(*args)
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 577, in read_response
    response = self._parser.read_response()
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 357, in read_response
    (e.args,))
redis.exceptions.ConnectionError: Error while reading from socket: ('Connection closed by server.',)

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 344, in read_response
    bufflen = self._sock.recv_into(self._buffer)
socket.timeout: timed out

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 320, in start
    blueprint.start(self)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 119, in start
    step.start(parent)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 596, in start
    c.loop(*c.loop_args())
  File "/usr/local/lib/python3.6/site-packages/celery/worker/loops.py", line 88, in asynloop
    next(loop)
  File "/usr/local/lib/python3.6/site-packages/kombu/async/hub.py", line 345, in create_loop
    cb(*cbargs)
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 1039, in on_readable
    self.cycle.on_readable(fileno)
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 337, in on_readable
    chan.handlers[type]()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 672, in _receive
    ret.append(self._receive_one(c))
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 678, in _receive_one
    response = c.parse_response()
  File "/usr/local/lib/python3.6/site-packages/redis/client.py", line 2183, in parse_response
    return self._execute(connection, connection.read_response)
  File "/usr/local/lib/python3.6/site-packages/redis/client.py", line 2176, in _execute
    return command(*args)
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 577, in read_response
    response = self._parser.read_response()
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 353, in read_response
    raise TimeoutError("Timeout reading from socket")
redis.exceptions.TimeoutError: Timeout reading from socket
[2017-03-09 00:37:28,560: INFO/MainProcess] Connected to redis://redis:6379/1
[2017-03-09 00:37:28,570: INFO/MainProcess] mingle: searching for neighbors
[2017-03-09 00:37:29,577: INFO/MainProcess] mingle: all alone
[2017-03-09 00:37:30,117: INFO/MainProcess] Received task: sample_task[51d998dc-43ce-4ad7-8c6e-7956ab6a6370]
[2017-03-09 00:37:30,121: INFO/MainProcess] Received task: sample_task[28c3b229-49c8-4358-a960-c2bfcd9db7a6]
[2017-03-09 00:37:30,122: WARNING/PoolWorker-10] 50
[2017-03-09 00:37:30,122: WARNING/PoolWorker-6] 49
[2017-03-09 00:37:30,123: INFO/PoolWorker-6] Task sample_task[28c3b229-49c8-4358-a960-c2bfcd9db7a6] succeeded in 0.0008835489861667156s: None
[2017-03-09 00:37:30,123: INFO/PoolWorker-10] Task sample_task[51d998dc-43ce-4ad7-8c6e-7956ab6a6370] succeeded in 0.0010674310033209622s: None
[2017-03-09 00:37:30,123: INFO/MainProcess] Received task: sample_task[83c3db81-5d15-4623-91d3-82f82ce06a8f]
[2017-03-09 00:37:30,125: INFO/MainProcess] Received task: sample_task[7c66284d-c125-4f29-8db4-299cb74b452e]
[2017-03-09 00:37:30,127: WARNING/PoolWorker-8] 48
[2017-03-09 00:37:30,127: WARNING/PoolWorker-9] 51
[2017-03-09 00:37:30,127: INFO/PoolWorker-8] Task sample_task[83c3db81-5d15-4623-91d3-82f82ce06a8f] succeeded in 0.0006798919930588454s: None
[2017-03-09 00:37:30,128: INFO/MainProcess] Received task: sample_task[3e8f66fd-c5e4-4cba-a3db-b1ab7a4889c9]
[2017-03-09 00:37:30,129: INFO/PoolWorker-9] Task sample_task[7c66284d-c125-4f29-8db4-299cb74b452e] succeeded in 0.002173115994082764s: None
[2017-03-09 00:37:30,130: INFO/MainProcess] Received task: sample_task[881cb653-5739-4b86-8ee8-4f8bc1d988c0]
[2017-03-09 00:37:30,131: WARNING/PoolWorker-6] 52
[2017-03-09 00:37:30,132: WARNING/PoolWorker-7] 53
[2017-03-09 00:37:30,133: INFO/MainProcess] Received task: sample_task[8a4a2f82-0b13-453b-aa61-f37c99c72ea9]
[2017-03-09 00:37:30,133: INFO/PoolWorker-7] Task sample_task[881cb653-5739-4b86-8ee8-4f8bc1d988c0] succeeded in 0.0012125579814892262s: None
[2017-03-09 00:37:30,131: INFO/PoolWorker-6] Task sample_task[3e8f66fd-c5e4-4cba-a3db-b1ab7a4889c9] succeeded in 0.00024440899142064154s: None
[2017-03-09 00:37:30,135: INFO/MainProcess] Received task: sample_task[94f1a955-2e83-423d-9c91-5ac5c254026b]
[2017-03-09 00:37:30,136: WARNING/PoolWorker-9] 54
[2017-03-09 00:37:30,138: WARNING/PoolWorker-10] 55
[2017-03-09 00:37:30,138: INFO/PoolWorker-10] Task sample_task[94f1a955-2e83-423d-9c91-5ac5c254026b] succeeded in 0.0003887370112352073s: None
[2017-03-09 00:37:30,137: INFO/PoolWorker-9] Task sample_task[8a4a2f82-0b13-453b-aa61-f37c99c72ea9] succeeded in 0.0005154869868420064s: None
[2017-03-09 00:37:30,139: INFO/MainProcess] Received task: sample_task[f1c6b5cb-74e0-4655-8ad4-51c5987aa956]
[2017-03-09 00:37:30,141: INFO/MainProcess] Received task: sample_task[e8469681-e458-4623-bb9a-c6062bb082f7]
[2017-03-09 00:37:30,142: WARNING/PoolWorker-7] 56
[2017-03-09 00:37:30,142: WARNING/PoolWorker-8] 57
[2017-03-09 00:37:30,142: INFO/PoolWorker-7] Task sample_task[f1c6b5cb-74e0-4655-8ad4-51c5987aa956] succeeded in 0.00024830500478856266s: None
[2017-03-09 00:37:30,142: INFO/PoolWorker-8] Task sample_task[e8469681-e458-4623-bb9a-c6062bb082f7] succeeded in 0.00026468498981557786s: None
[2017-03-09 00:37:30,144: INFO/MainProcess] Received task: sample_task[47fe7cf3-0279-42ec-a9f5-9bbaea6e9163]
[2017-03-09 00:37:30,145: INFO/MainProcess] Received task: sample_task[a6696fac-0985-4c85-bf66-feeb75b59742]
[2017-03-09 00:37:30,146: WARNING/PoolWorker-10] 58
[2017-03-09 00:37:30,146: WARNING/PoolWorker-6] 59
[2017-03-09 00:37:30,146: INFO/PoolWorker-10] Task sample_task[47fe7cf3-0279-42ec-a9f5-9bbaea6e9163] succeeded in 0.00023591998615302145s: None
[2017-03-09 00:37:30,146: INFO/PoolWorker-6] Task sample_task[a6696fac-0985-4c85-bf66-feeb75b59742] succeeded in 0.0005030019965488464s: None
[2017-03-09 00:37:30,148: INFO/MainProcess] Received task: sample_task[ab1e67e9-dd92-4fac-a4ef-c20d3ebec672]
[2017-03-09 00:37:30,150: INFO/MainProcess] Received task: sample_task[c31feb94-e50e-4c5f-8dee-536c1fd66804]
[2017-03-09 00:37:30,151: WARNING/PoolWorker-8] 60
[2017-03-09 00:37:30,151: WARNING/PoolWorker-9] 61
[2017-03-09 00:37:30,151: INFO/PoolWorker-8] Task sample_task[ab1e67e9-dd92-4fac-a4ef-c20d3ebec672] succeeded in 0.00022323502344079316s: None
[2017-03-09 00:37:30,151: INFO/PoolWorker-9] Task sample_task[c31feb94-e50e-4c5f-8dee-536c1fd66804] succeeded in 0.00022563201491720974s: None
[2017-03-09 00:37:30,153: INFO/MainProcess] Received task: sample_task[242c5900-4d49-4091-a4ef-53062bb97625]
[2017-03-09 00:37:30,154: INFO/MainProcess] Received task: sample_task[e986dd00-07b2-4528-852d-055479ad0e2d]
[2017-03-09 00:37:30,155: WARNING/PoolWorker-7] 63
[2017-03-09 00:37:30,155: INFO/PoolWorker-7] Task sample_task[e986dd00-07b2-4528-852d-055479ad0e2d] succeeded in 0.00020785300876013935s: None
[2017-03-09 00:37:30,156: WARNING/PoolWorker-6] 62
[2017-03-09 00:37:30,156: INFO/PoolWorker-6] Task sample_task[242c5900-4d49-4091-a4ef-53062bb97625] succeeded in 0.0001918720081448555s: None
[2017-03-09 00:37:30,157: INFO/MainProcess] Received task: sample_task[3cc8f8e0-ac7c-45e4-a869-d421c0a9cecc]
[2017-03-09 00:37:30,159: INFO/MainProcess] Received task: sample_task[87aeef42-8f54-4111-a098-6dd30f1f0985]
[2017-03-09 00:37:30,160: WARNING/PoolWorker-10] 65
[2017-03-09 00:37:30,160: WARNING/PoolWorker-9] 64
[2017-03-09 00:37:30,160: INFO/PoolWorker-9] Task sample_task[3cc8f8e0-ac7c-45e4-a869-d421c0a9cecc] succeeded in 0.0001904729870148003s: None
[2017-03-09 00:37:30,160: INFO/PoolWorker-10] Task sample_task[87aeef42-8f54-4111-a098-6dd30f1f0985] succeeded in 0.00021464499877765775s: None
[2017-03-09 00:37:30,161: INFO/MainProcess] Received task: sample_task[96cf338e-c515-4952-a734-70cd8967e70b]
[2017-03-09 00:37:30,163: INFO/MainProcess] Received task: sample_task[beebfa9d-83ba-4033-aab2-8e17f5d3e3a9]
[2017-03-09 00:37:30,164: WARNING/PoolWorker-7] 66
[2017-03-09 00:37:30,164: WARNING/PoolWorker-8] 67
[2017-03-09 00:37:30,164: INFO/PoolWorker-7] Task sample_task[96cf338e-c515-4952-a734-70cd8967e70b] succeeded in 0.0002000620006583631s: None
[2017-03-09 00:37:30,164: INFO/PoolWorker-8] Task sample_task[beebfa9d-83ba-4033-aab2-8e17f5d3e3a9] succeeded in 0.00023112597409635782s: None
[2017-03-09 00:37:30,165: INFO/MainProcess] Received task: sample_task[31926b81-b5ed-4238-b9a0-30bacd6efde4]
[2017-03-09 00:37:30,167: INFO/MainProcess] Received task: sample_task[6b7dd428-bfda-49d4-af3e-17ad5743bbc9]
[2017-03-09 00:37:30,168: WARNING/PoolWorker-10] 68
[2017-03-09 00:37:30,168: WARNING/PoolWorker-6] 69
[2017-03-09 00:37:30,168: INFO/PoolWorker-10] Task sample_task[31926b81-b5ed-4238-b9a0-30bacd6efde4] succeeded in 0.00019486801465973258s: None
[2017-03-09 00:37:30,168: INFO/PoolWorker-6] Task sample_task[6b7dd428-bfda-49d4-af3e-17ad5743bbc9] succeeded in 0.00018438100232742727s: None
[2017-03-09 00:37:30,169: INFO/MainProcess] Received task: sample_task[d237b106-7857-40fb-b784-cf7862df8f13]
[2017-03-09 00:37:30,171: INFO/MainProcess] Received task: sample_task[c09430d7-311b-4773-81d6-c7063a42b296]
[2017-03-09 00:37:30,172: WARNING/PoolWorker-8] 70
[2017-03-09 00:37:30,172: WARNING/PoolWorker-9] 71
[2017-03-09 00:37:30,172: INFO/PoolWorker-9] Task sample_task[c09430d7-311b-4773-81d6-c7063a42b296] succeeded in 0.00021304600522853434s: None
[2017-03-09 00:37:30,172: INFO/PoolWorker-8] Task sample_task[d237b106-7857-40fb-b784-cf7862df8f13] succeeded in 0.00022862799232825637s: None
[2017-03-09 00:37:30,173: INFO/MainProcess] Received task: sample_task[a1e56113-6c8c-489e-9707-e3c0bd06f822]
[2017-03-09 00:37:30,175: INFO/MainProcess] Received task: sample_task[e0363e59-8ca0-4164-9a68-36608bcc5d89]
[2017-03-09 00:37:30,176: WARNING/PoolWorker-7] 73
[2017-03-09 00:37:30,176: INFO/PoolWorker-7] Task sample_task[e0363e59-8ca0-4164-9a68-36608bcc5d89] succeeded in 0.00019826399511657655s: None
[2017-03-09 00:37:30,177: WARNING/PoolWorker-6] 72
[2017-03-09 00:37:30,177: INFO/PoolWorker-6] Task sample_task[a1e56113-6c8c-489e-9707-e3c0bd06f822] succeeded in 0.00018697697669267654s: None
[2017-03-09 00:37:30,178: INFO/MainProcess] Received task: sample_task[f437dead-7795-44ac-9350-15ba41cd9e72]
[2017-03-09 00:37:30,180: INFO/MainProcess] Received task: sample_task[1401b93b-dbac-4265-bf19-0fd78e14e584]
[2017-03-09 00:37:30,181: WARNING/PoolWorker-10] 75
[2017-03-09 00:37:30,182: WARNING/PoolWorker-9] 74
[2017-03-09 00:37:30,182: INFO/PoolWorker-9] Task sample_task[f437dead-7795-44ac-9350-15ba41cd9e72] succeeded in 0.00023412099108099937s: None
[2017-03-09 00:37:30,181: INFO/PoolWorker-10] Task sample_task[1401b93b-dbac-4265-bf19-0fd78e14e584] succeeded in 0.00025050199474208057s: None
[2017-03-09 00:37:30,183: INFO/MainProcess] Received task: sample_task[ddd3d31b-b46b-4ce3-aefd-b5b86fa289bb]
[2017-03-09 00:37:30,185: INFO/MainProcess] Received task: sample_task[97bde402-f90e-4ce4-b29c-d9983149009d]
[2017-03-09 00:37:30,186: WARNING/PoolWorker-7] 76
[2017-03-09 00:37:30,186: WARNING/PoolWorker-8] 77
[2017-03-09 00:37:30,186: INFO/PoolWorker-7] Task sample_task[ddd3d31b-b46b-4ce3-aefd-b5b86fa289bb] succeeded in 0.0002481049741618335s: None
[2017-03-09 00:37:30,186: INFO/PoolWorker-8] Task sample_task[97bde402-f90e-4ce4-b29c-d9983149009d] succeeded in 0.0002814650069922209s: None
[2017-03-09 00:37:30,187: INFO/MainProcess] Received task: sample_task[e4d59bd8-3e2b-40ce-8326-0bf40a520a8a]
[2017-03-09 00:37:30,189: INFO/MainProcess] Received task: sample_task[f5f4179f-c03d-49a8-a400-ca91fde37cb3]
[2017-03-09 00:37:30,190: WARNING/PoolWorker-10] 78
[2017-03-09 00:37:30,190: WARNING/PoolWorker-6] 79
[2017-03-09 00:37:30,190: INFO/PoolWorker-10] Task sample_task[e4d59bd8-3e2b-40ce-8326-0bf40a520a8a] succeeded in 0.0002445089921820909s: None
[2017-03-09 00:37:30,190: INFO/PoolWorker-6] Task sample_task[f5f4179f-c03d-49a8-a400-ca91fde37cb3] succeeded in 0.00022942700888961554s: None
[2017-03-09 00:37:30,192: INFO/MainProcess] Received task: sample_task[2d2e8152-3580-4fde-b502-3c0d7e08c765]
[2017-03-09 00:37:30,194: INFO/MainProcess] Received task: sample_task[ad73c0da-5591-46de-b681-4ae2a3f522b9]
[2017-03-09 00:37:30,195: WARNING/PoolWorker-8] 80
[2017-03-09 00:37:30,195: WARNING/PoolWorker-9] 81
[2017-03-09 00:37:30,195: INFO/PoolWorker-8] Task sample_task[2d2e8152-3580-4fde-b502-3c0d7e08c765] succeeded in 0.0002931519993580878s: None
[2017-03-09 00:37:30,195: INFO/PoolWorker-9] Task sample_task[ad73c0da-5591-46de-b681-4ae2a3f522b9] succeeded in 0.0002947490138467401s: None
[2017-03-09 00:37:30,197: INFO/MainProcess] Received task: sample_task[bba0fb2b-7bce-4d5b-acdc-afdeaed877c0]
[2017-03-09 00:37:30,199: INFO/MainProcess] Received task: sample_task[dfe333c6-031b-4b3b-8d55-bb1434f97b44]
[2017-03-09 00:37:30,200: WARNING/PoolWorker-7] 83
[2017-03-09 00:37:30,201: INFO/PoolWorker-7] Task sample_task[dfe333c6-031b-4b3b-8d55-bb1434f97b44] succeeded in 0.00046804401790723205s: None
[2017-03-09 00:37:30,201: WARNING/PoolWorker-6] 82
[2017-03-09 00:37:30,202: INFO/PoolWorker-6] Task sample_task[bba0fb2b-7bce-4d5b-acdc-afdeaed877c0] succeeded in 0.0004863219801336527s: None
[2017-03-09 00:37:30,203: INFO/MainProcess] Received task: sample_task[eb20f859-4286-4cb8-9c7c-498259e915ac]
[2017-03-09 00:37:30,204: INFO/MainProcess] Received task: sample_task[5562513a-e9d3-4e1d-81fb-1c465a7880d9]
[2017-03-09 00:37:30,205: WARNING/PoolWorker-10] 85
[2017-03-09 00:37:30,206: WARNING/PoolWorker-9] 84
[2017-03-09 00:37:30,206: INFO/PoolWorker-10] Task sample_task[5562513a-e9d3-4e1d-81fb-1c465a7880d9] succeeded in 0.00028865598142147064s: None
[2017-03-09 00:37:30,206: INFO/PoolWorker-9] Task sample_task[eb20f859-4286-4cb8-9c7c-498259e915ac] succeeded in 0.0002765709941741079s: None
[2017-03-09 00:37:30,208: INFO/MainProcess] Received task: sample_task[f591a682-3dc7-432a-95c1-3287eb828c9e]
[2017-03-09 00:37:30,210: INFO/MainProcess] Received task: sample_task[90385bef-eb65-448d-ad2d-5f46f29eec94]
[2017-03-09 00:37:30,211: WARNING/PoolWorker-7] 86
[2017-03-09 00:37:30,211: WARNING/PoolWorker-8] 87
[2017-03-09 00:37:30,211: INFO/PoolWorker-7] Task sample_task[f591a682-3dc7-432a-95c1-3287eb828c9e] succeeded in 0.00038494201726280153s: None
[2017-03-09 00:37:30,211: INFO/PoolWorker-8] Task sample_task[90385bef-eb65-448d-ad2d-5f46f29eec94] succeeded in 0.00037595300818793476s: None
[2017-03-09 00:37:30,213: INFO/MainProcess] Received task: sample_task[b61548fc-881e-40e0-b74c-efecc99e607a]
[2017-03-09 00:37:30,214: INFO/MainProcess] Received task: sample_task[22b4a7aa-ba45-4ca1-a6ff-bd4428fdd646]
[2017-03-09 00:37:30,215: WARNING/PoolWorker-10] 88
[2017-03-09 00:37:30,215: WARNING/PoolWorker-6] 89
[2017-03-09 00:37:30,216: INFO/PoolWorker-6] Task sample_task[22b4a7aa-ba45-4ca1-a6ff-bd4428fdd646] succeeded in 0.0002885569992940873s: None
[2017-03-09 00:37:30,216: INFO/PoolWorker-10] Task sample_task[b61548fc-881e-40e0-b74c-efecc99e607a] succeeded in 0.000283862987998873s: None
[2017-03-09 00:37:30,217: INFO/MainProcess] Received task: sample_task[5a4550a0-c75f-4f0e-8086-bf41bb406e9f]
[2017-03-09 00:37:30,219: INFO/MainProcess] Received task: sample_task[0a7088be-09c1-42d7-9579-1897a8bbe17c]
[2017-03-09 00:37:30,220: WARNING/PoolWorker-8] 90
[2017-03-09 00:37:30,220: WARNING/PoolWorker-9] 91
[2017-03-09 00:37:30,221: INFO/PoolWorker-8] Task sample_task[5a4550a0-c75f-4f0e-8086-bf41bb406e9f] succeeded in 0.0005578370182774961s: None
[2017-03-09 00:37:30,221: INFO/PoolWorker-9] Task sample_task[0a7088be-09c1-42d7-9579-1897a8bbe17c] succeeded in 0.0005019039963372052s: None
[2017-03-09 00:37:30,222: INFO/MainProcess] Received task: sample_task[333f27ea-943d-4ebb-80ea-06c7c5076bb3]
[2017-03-09 00:37:30,224: INFO/MainProcess] Received task: sample_task[27544b3a-0929-46cd-b9ad-66c218999396]
[2017-03-09 00:37:30,225: WARNING/PoolWorker-7] 93
[2017-03-09 00:37:30,225: INFO/PoolWorker-7] Task sample_task[27544b3a-0929-46cd-b9ad-66c218999396] succeeded in 0.00027936798869632185s: None
[2017-03-09 00:37:30,226: WARNING/PoolWorker-6] 92
[2017-03-09 00:37:30,226: INFO/PoolWorker-6] Task sample_task[333f27ea-943d-4ebb-80ea-06c7c5076bb3] succeeded in 0.00026488499133847654s: None
[2017-03-09 00:37:30,227: INFO/MainProcess] Received task: sample_task[ce6d2fe3-02b9-45c8-8a1a-c93632a4a345]
[2017-03-09 00:37:30,229: INFO/MainProcess] Received task: sample_task[bfdf84f6-d312-4277-80b1-99ffb2db15bd]
[2017-03-09 00:37:30,230: WARNING/PoolWorker-10] 95
[2017-03-09 00:37:30,231: WARNING/PoolWorker-9] 94
[2017-03-09 00:37:30,230: INFO/PoolWorker-10] Task sample_task[bfdf84f6-d312-4277-80b1-99ffb2db15bd] succeeded in 0.00026138901012018323s: None
[2017-03-09 00:37:30,231: INFO/PoolWorker-9] Task sample_task[ce6d2fe3-02b9-45c8-8a1a-c93632a4a345] succeeded in 0.000259691005339846s: None
[2017-03-09 00:37:30,232: INFO/MainProcess] Received task: sample_task[e487bdc1-7fbf-47e8-bf42-1400b4d485c9]
[2017-03-09 00:37:30,235: INFO/MainProcess] Received task: sample_task[8c01566b-bec8-4c7c-a3f1-535dcb17b074]
[2017-03-09 00:37:30,236: WARNING/PoolWorker-8] 97
[2017-03-09 00:37:30,236: WARNING/PoolWorker-7] 96
[2017-03-09 00:37:30,237: INFO/PoolWorker-7] Task sample_task[e487bdc1-7fbf-47e8-bf42-1400b4d485c9] succeeded in 0.0002737749891821295s: None
[2017-03-09 00:37:30,237: INFO/PoolWorker-8] Task sample_task[8c01566b-bec8-4c7c-a3f1-535dcb17b074] succeeded in 0.0005120910063851625s: None
[2017-03-09 00:37:30,238: INFO/MainProcess] Received task: sample_task[0451f615-f45c-48cf-999f-da4895aec69e]
[2017-03-09 00:37:30,283: INFO/MainProcess] Received task: sample_task[2c492131-a795-4bc1-b085-5c0f256281a9]
[2017-03-09 00:37:30,372: WARNING/MainProcess] consumer: Connection to broker lost. Trying to re-establish the connection...
Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 543, in send_packed_command
    self._sock.sendall(item)
BrokenPipeError: [Errno 32] Broken pipe

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 320, in start
    blueprint.start(self)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 119, in start
    step.start(parent)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 596, in start
    c.loop(*c.loop_args())
  File "/usr/local/lib/python3.6/site-packages/celery/worker/loops.py", line 88, in asynloop
    next(loop)
  File "/usr/local/lib/python3.6/site-packages/kombu/async/hub.py", line 277, in create_loop
    tick_callback()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 1032, in on_poll_start
    cycle_poll_start()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 315, in on_poll_start
    self._register_BRPOP(channel)
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 301, in _register_BRPOP
    channel._brpop_start()
  File "/usr/local/lib/python3.6/site-packages/kombu/transport/redis.py", line 707, in _brpop_start
    self.client.connection.send_command('BRPOP', *keys)
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 563, in send_command
    self.send_packed_command(self.pack_command(*args))
  File "/usr/local/lib/python3.6/site-packages/redis/connection.py", line 556, in send_packed_command
    (errno, errmsg))
redis.exceptions.ConnectionError: Error 32 while writing to socket. Broken pipe.
[2017-03-09 00:37:30,373: WARNING/MainProcess] Restoring 4 unacknowledged message(s)
[2017-03-09 00:37:30,390: INFO/MainProcess] Connected to redis://redis:6379/1
[2017-03-09 00:37:30,399: INFO/MainProcess] mingle: searching for neighbors
[2017-03-09 00:37:31,405: INFO/MainProcess] mingle: all alone
[2017-03-09 00:37:31,416: CRITICAL/MainProcess] Unrecoverable error: AttributeError("'NoneType' object has no attribute 'fileno'",)
Traceback (most recent call last):
  File "/usr/local/lib/python3.6/site-packages/celery/worker/worker.py", line 203, in start
    self.blueprint.start(self)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 119, in start
    step.start(parent)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 370, in start
    return self.obj.start()
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 320, in start
    blueprint.start(self)
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 119, in start
    step.start(parent)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/consumer/consumer.py", line 596, in start
    c.loop(*c.loop_args())
  File "/usr/local/lib/python3.6/site-packages/celery/worker/loops.py", line 47, in asynloop
    obj.controller.register_with_event_loop(hub)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/worker.py", line 217, in register_with_event_loop
    description='hub.register',
  File "/usr/local/lib/python3.6/site-packages/celery/bootsteps.py", line 151, in send_all
    fun(parent, *args)
  File "/usr/local/lib/python3.6/site-packages/celery/worker/components.py", line 178, in register_with_event_loop
    w.pool.register_with_event_loop(hub)
  File "/usr/local/lib/python3.6/site-packages/celery/concurrency/prefork.py", line 134, in register_with_event_loop
    return reg(loop)
  File "/usr/local/lib/python3.6/site-packages/celery/concurrency/asynpool.py", line 472, in register_with_event_loop
    [self._track_child_process(w, hub) for w in self._pool]
  File "/usr/local/lib/python3.6/site-packages/celery/concurrency/asynpool.py", line 472, in <listcomp>
    [self._track_child_process(w, hub) for w in self._pool]
  File "/usr/local/lib/python3.6/site-packages/celery/concurrency/asynpool.py", line 455, in _track_child_process
    hub.add_reader(fd, self._event_process_exit, hub, proc)
  File "/usr/local/lib/python3.6/site-packages/kombu/async/hub.py", line 208, in add_reader
    return self.add(fds, callback, READ | ERR, args)
  File "/usr/local/lib/python3.6/site-packages/kombu/async/hub.py", line 157, in add
    fd = fileno(fd)
  File "/usr/local/lib/python3.6/site-packages/kombu/utils/compat.py", line 95, in fileno
    return f.fileno()
AttributeError: 'NoneType' object has no attribute 'fileno'
```
