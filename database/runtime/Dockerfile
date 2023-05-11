FROM --platform=linux/amd64 public.ecr.aws/sam/build-python3.9:latest

ARG PGSTAC_VERSION
RUN echo "Using PGSTAC Version ${PGSTAC_VERSION}"

WORKDIR /tmp

COPY database/runtime/requirements.txt /tmp/requirements.txt

RUN pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt -t /asset

RUN pip install pypgstac==${PGSTAC_VERSION} -t /asset

COPY database/runtime/handler.py /asset/handler.py

# https://stackoverflow.com/a/61746719
# Tip from eoAPI: turns out, asyncio is part of python
RUN rm -rf /asset/asyncio*

CMD ["echo", "hello world database"]