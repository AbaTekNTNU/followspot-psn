FROM alpine:3.20

RUN apk add --no-cache g++ python3 python3-dev py3-aiohttp git

RUN git clone --recursive https://github.com/vyv/psn-py.git
WORKDIR /psn-py/vendors/pybind11
# We need a newer version of pybind11 to compile agains python 3.12
RUN git fetch --tags && git checkout v2.13.6
WORKDIR /psn-py

RUN g++ -O3 -Wall -shared -fPIC $(python3-config --includes) \
-Ivendors/psn/include -Ivendors/pybind11/include src/main.cpp \
-o psn$(python3-config --extension-suffix)

COPY backend /backend
WORKDIR /backend
RUN cp /psn-py/psn$(python3-config --extension-suffix) .

ENTRYPOINT ["python3", "psn_server.py"]
