
test_staging:
	docker-compose -f docker-compose.akira.yml -f docker-compose.test.yml up -d

down_staging:
	docker-compose -f docker-compose.akira.yml -f docker-compose.test.yml down