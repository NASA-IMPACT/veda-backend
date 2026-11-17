.PHONY:
	install-dev
	install
	lint
	format
	diff
	deploy
	destroy

install-dev:
	uv sync --all-groups --locked

install:
	uv sync --no-dev --locked

lint:
	uv run pre-commit run --all-files

STACKS =
ARGS =

diff:
	uv run npx aws-cdk@2.1134 diff $(STACKS) -v

deploy:
	uv run npx aws-cdk@2.1134 deploy $(STACKS) $(ARGS)

destroy:
	uv run npx aws-cdk@2.1134 destroy $(STACKS)
