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

# The CDK CLI that `npm ci` installs from package-lock.json
CDK = uv run node_modules/.bin/cdk

node_modules: package-lock.json
	npm ci

diff: node_modules
	$(CDK) diff -v

STACKS = --all
ARGS =

deploy: node_modules
	$(CDK) deploy $(STACKS) $(ARGS)

destroy: node_modules
	$(CDK) destroy $(STACKS)
