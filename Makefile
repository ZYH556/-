.PHONY: dev dev-graph dev-full down init-db serve test eval

dev:
	bash scripts/start_core.sh

dev-graph:
	bash scripts/start_graph.sh

dev-full:
	bash scripts/start_full.sh

down:
	bash scripts/stop_all.sh

init-db:
	bash scripts/init_all.sh

serve:
	bash scripts/start_api.sh

test:
	bash scripts/test_unit.sh

eval:
	bash scripts/run_eval.sh
