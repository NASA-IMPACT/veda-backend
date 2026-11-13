FROM --platform=linux/amd64 public.ecr.aws/sam/build-python3.12:latest

ARG PGSTAC_VERSION
RUN echo "Using PGSTAC Version ${PGSTAC_VERSION}"

WORKDIR /tmp

RUN pip install requests "psycopg[binary,pool]!=3.3.7" pypgstac==${PGSTAC_VERSION} -t /asset

# handler_sha256 in database/infrastructure/construct.py hashes only handler.py.
# Add any other file copied into /asset to that hash, or edits to it will not
# rerun the bootstrap.
COPY database/runtime/handler.py /asset/handler.py

# https://stackoverflow.com/a/61746719
# Tip from eoAPI: turns out, asyncio is part of python
RUN rm -rf /asset/asyncio*

CMD ["echo", "hello world database"]