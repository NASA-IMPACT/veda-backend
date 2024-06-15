FROM --platform=linux/amd64 public.ecr.aws/sam/build-python3.9:latest

WORKDIR /tmp

RUN pip install requests "urllib3<2" psycopg[binary,pool] -t /asset

COPY features_api_database/runtime/handler.py /asset/handler.py

# https://stackoverflow.com/a/61746719
# Tip from eoAPI: turns out, asyncio is part of python
RUN rm -rf /asset/asyncio*

CMD ["echo", "hello world database"]