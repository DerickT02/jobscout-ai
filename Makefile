install:
	pip install -e packages/core
	pip install -e packages/db
	pip install -e packages/ingest
	pip install -e packages/pipeline
	pip install -e packages/agent
	pip install -e packages/eval
	pip install -e apps/api