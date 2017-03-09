.PHONY: run build queue-up worker-up clean report redis-cli redis-monitor

run: build produce worker-up

build:
	docker-compose build

queue-up:
	docker-compose up -d redis rabbitmq
	sleep 2

worker-up:
	docker-compose up redis rabbitmq worker flower

produce: queue-up
	docker-compose run --rm worker python main.py

clean:
	docker-compose stop
	docker-compose rm -v --force

report:
	docker-compose run --rm worker celery report --app main.app

redis-cli: queue-up
	docker-compose run --rm redis redis-cli -h redis -p 6379

redis-monitor: queue-up
	docker-compose run --rm redis redis-cli -h redis -p 6379 monitor
