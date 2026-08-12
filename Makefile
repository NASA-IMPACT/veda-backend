.PHONY:
	install-dev
	install
	lint
	format
	diff
	deploy
	destroy

install-dev:
	uv sync --all-groups

install:
	uv sync --no-dev --frozen

lint:
	uv run ruff format --diff
	uv run ruff check
	uv run mypy .

format:
	uv run ruff check --fix
	uv run ruff check --select I --fix
	uv run ruff format

STACKS =
ARGS =

diff:
	uv run npx aws-cdk@2.1134 diff $(STACKS) -v

deploy:
	uv run npx aws-cdk@2.1134 deploy $(STACKS) $(ARGS)

destroy:
	uv run npx aws-cdk@2.1134 destroy $(STACKS)
