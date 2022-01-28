FROM --platform=linux/amd64 lambci/lambda:build-python3.8

WORKDIR /tmp

RUN pip install "importlib_resources;python_version>='3.8'" requests psycopg2-binary pypgstac==0.3.4 -t /asset

COPY database/infrastructure/handler.py /asset/handler.py

CMD ["echo", "hello world database"]