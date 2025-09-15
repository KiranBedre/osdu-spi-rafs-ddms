# docker build -t rafsdistroless -f Dockerfile .
# https://gealber.com/recipe-distroless-container-fastapi
ARG python_version=3.11
ARG python_distroless_image=gcr.io/distroless/python3-debian12:nonroot
FROM python:${python_version}-bookworm AS build-env

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools \
      && pip install --no-cache-dir -r /app/requirements.txt

COPY ./app /app/
WORKDIR /app

# Only needed for production uvloop==0.18.0
RUN pip install --no-cache-dir uvicorn[standard]==0.23.2
RUN cp -v $(which uvicorn) .

# Google Distroless uses python 3.9 we are choosing to go with cgr.dev (gcr.io/distroless/python3:nonroot uses python 3.9)
# Originally sourced from cgr.dev/chainguard/python:3.X | can use either 3.10 -> 3.11 : https://github.com/chainguard-images/images/tree/main/images/python
# For permissions https://github.com/alexdmoss/distroless-python/blob/main/distroless.Dockerfile#L38
# Gunicorn distroless approach https://github.com/alexdmoss/distroless-python/tree/main/tests/gunicorn
FROM ${python_distroless_image}
ARG python_version
ARG user_id=nonroot

COPY --from=build-env /usr/local/lib/python${python_version}/site-packages /usr/local/lib/python${python_version}/site-packages
COPY --from=build-env --chown=${user_id}:${user_id} /app /app/app
COPY --from=build-env --chown=${user_id}:${user_id} /app/uvicorn /app/uvicorn

ARG build_date
ARG commit_id
ARG commit_branch
ARG commit_message
ARG release_version
ENV BUILD_DATE $build_date
ENV COMMIT_ID $commit_id
ENV COMMIT_BRANCH $commit_branch
ENV COMMIT_MESSAGE=$commit_message
ENV RELEASE_VERSION=$release_version

ENV PYTHONPATH=/usr/local/lib/python${python_version}/site-packages
ENV PYTHONUNBUFFERED 1

WORKDIR /app
EXPOSE 8080

USER $user_id

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4", "--loop", "uvloop"]
