FROM public.ecr.aws/sam/build-python3.9:latest

WORKDIR /tmp

COPY ingest_api /tmp/ingestor
RUN pip install -r /tmp/ingestor/requirements.txt -t /asset --no-binary pydantic uvicorn
RUN rm -rf /tmp/ingestor
# TODO this is temporary until we use a real packaging system like setup.py or poetry
COPY ingest_api/src /asset/src

# # Reduce package size and remove useless files
RUN cd /asset && find . -type f -name '*.pyc' | while read f; do n=$(echo $f | sed 's/__pycache__\///' | sed 's/.cpython-[2-3][0-9]//'); cp $f $n; done;
RUN cd /asset && find . -type d -a -name '__pycache__' -print0 | xargs -0 rm -rf
#RUN cd /asset && find . -type f -a -name '*.py' -print0 | xargs -0 rm -f
RUN find /asset -type d -a -name 'tests' -print0 | xargs -0 rm -rf
RUN rm -rdf /asset/numpy/doc/ /asset/boto3* /asset/botocore* /asset/bin /asset/geos_license /asset/Misc

COPY ingest_api/handler.py /asset/handler.py
COPY ingest_api/ingestor.py /asset/ingestor.py

CMD ["echo", "hello world"]