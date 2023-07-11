# docker build -t rafsdistroless -f Dockerfile .
# https://gealber.com/recipe-distroless-container-fastapi
ARG python_version=3.11
FROM mcr.microsoft.com/mirror/docker/library/python:${python_version}-slim AS build-env

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
      && pip install --no-cache-dir -r /app/requirements.txt

COPY ./app /app/
WORKDIR /app

# Only needed for production uvloop==0.17.0
RUN pip install --no-cache-dir uvicorn[standard]==0.22.0
RUN cp -v $(which uvicorn) .

# Google Distroless uses python 3.9 we are choosing to go with cgr.dev (gcr.io/distroless/python3:nonroot uses python 3.9)
# cgr.dev/chainguard/python:3.X can use either 3.10 -> 3.11 : https://github.com/chainguard-images/images/tree/main/images/python
# For permissions https://github.com/alexdmoss/distroless-python/blob/main/distroless.Dockerfile#L38
# Gunicorn distroless approach https://github.com/alexdmoss/distroless-python/tree/main/tests/gunicorn
FROM cgr.dev/chainguard/python:${python_version}
ARG python_version
ARG user_id=1001

COPY --from=build-env /usr/local/lib/python${python_version}/site-packages /usr/local/lib/python${python_version}/site-packages
COPY --from=build-env --chown=${user_id}:0 /app /app/app
COPY --from=build-env --chown=${user_id}:0 /app/uvicorn /app/uvicorn

ARG build_date
ARG commit_id
ARG commit_branch
ARG commit_message
ENV BUILD_DATE $build_date
ENV COMMIT_ID $commit_id
ENV COMMIT_BRANCH $commit_branch
ENV COMMIT_MESSAGE=$commit_message

ENV PYTHONPATH=/usr/local/lib/python${python_version}/site-packages
ENV PYTHONUNBUFFERED 1

WORKDIR /app
EXPOSE 8080

USER $user_id

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "8", "--loop", "uvloop"]

# If we want to control server settings through python run.py file
# COPY --chown=${user_id}:0 ./devops/run.py /app/run.py
# ENTRYPOINT ["python", "run.py"]
