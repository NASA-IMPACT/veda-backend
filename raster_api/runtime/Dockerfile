FROM --platform=linux/amd64 public.ecr.aws/sam/build-python3.12:latest

RUN dnf install -y gcc-c++

WORKDIR /tmp

COPY raster_api/runtime /tmp/raster
RUN pip install "mangum<=0.19" "/tmp/raster[psycopg-binary]" -t /asset --no-binary pydantic
RUN rm -rf /tmp/raster
RUN cp /usr/lib64/libexpat.so.1 /asset/

# # Reduce package size and remove useless files
RUN cd /asset && find . -type f -name '*.pyc' | while read f; do n=$(echo $f | sed 's/__pycache__\///' | sed 's/.cpython-[0-9]*//'); cp $f $n; done;
RUN cd /asset && find . -type d -a -name '__pycache__' -print0 | xargs -0 rm -rf
RUN cd /asset && find . -type f -a -name '*.py' -print0 | xargs -0 rm -f
RUN find /asset -type d -a -name 'tests' -print0 | xargs -0 rm -rf
RUN rm -rdf /asset/numpy/doc/ /asset/boto3* /asset/botocore* /asset/bin /asset/geos_license /asset/Misc

# rasterio and pyproj each vendor a ~9.5MB PROJ database; keep only rasterio's.
# Must keep the newer one - GDAL rejects an older DATABASE.LAYOUT.VERSION.
# PROJ_DATA here is for the build check below; runtime gets it from construct.py.
RUN rm -f /asset/pyproj/proj_dir/share/proj/proj.db
ENV PROJ_DATA=/asset/rasterio/proj_data

COPY raster_api/runtime/handler.py /asset/handler.py
RUN dnf remove -y gcc-c++

WORKDIR /asset
RUN python -c "from handler import handler; print('All Good')"

CMD ["echo", "hello world"]