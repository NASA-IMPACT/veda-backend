FROM ghcr.io/stac-utils/pgstac:v0.6.6

ARG PGSTAC_VERSION
ARG ENV
RUN echo "Using PGSTAC Version ${PGSTAC_VERSION}"

ENV ENV=${ENV}
WORKDIR /tmp

RUN apt-get install python3
RUN pip install boto3 requests psycopg[binary,pool] pypgstac==${PGSTAC_VERSION} -t /asset

COPY database/runtime/handler.py /asset/handler.py

# https://stackoverflow.com/a/61746719
# Tip from eoAPI: turns out, asyncio is part of python
RUN rm -rf /asset/asyncio*

RUN python3 /asset/handler.py
