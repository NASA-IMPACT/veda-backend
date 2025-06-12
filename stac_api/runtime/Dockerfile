FROM --platform=linux/amd64 public.ecr.aws/sam/build-python3.12:latest

WORKDIR /tmp

COPY stac_api/runtime /tmp/stac

RUN pip install "mangum" "plpygis>=0.2.1" /tmp/stac -t /asset --no-binary pydantic
RUN rm -rf /tmp/stac

# Reduce package size and remove useless files
RUN cd /asset && find . -type f -name '*.pyc' | while read f; do n=$(echo $f | sed 's/__pycache__\///' | sed 's/.cpython-[0-9]*//'); cp $f $n; done;
RUN cd /asset && find . -type d -a -name '__pycache__' -print0 | xargs -0 rm -rf
RUN cd /asset && find . -type f -a -name '*.py' -print0 | xargs -0 rm -f
RUN find /asset -type d -a -name 'tests' -print0 | xargs -0 rm -rf

COPY stac_api/runtime/handler.py /asset/handler.py

CMD ["echo", "hello world"]
