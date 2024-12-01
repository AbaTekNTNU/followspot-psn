FROM node:alpine3.20 AS frontend

WORKDIR /frontend

RUN npm install -g pnpm

COPY frontend/package.json frontend/pnpm-lock.yaml ./

RUN pnpm i

COPY frontend .

RUN pnpm build

FROM alpine:3.20 AS backend

RUN apk add --no-cache g++ python3 python3-dev git

RUN git clone --recursive https://github.com/vyv/psn-py.git
WORKDIR /psn-py/vendors/pybind11
# We need a newer version of pybind11 to compile agains python 3.12
RUN git fetch --tags && git checkout v2.13.6
WORKDIR /psn-py

RUN g++ -O3 -Wall -shared -fPIC $(python3-config --includes) \
  -Ivendors/psn/include -Ivendors/pybind11/include src/main.cpp \
  -o psn$(python3-config --extension-suffix)

RUN cp /psn-py/psn$(python3-config --extension-suffix) /output


FROM alpine:3.20 AS final

RUN apk add --no-cache python3 py3-aiohttp


COPY --from=backend /output /backend/psn.so
COPY backend/psn_server.py /backend/psn_server.py
COPY --from=frontend /frontend/dist /backend/static

WORKDIR /backend

ENTRYPOINT ["python3", "/backend/psn_server.py"]
