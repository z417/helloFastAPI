FROM python:3.9-slim
LABEL maintainer="Yuri"
LABEL version="0.0.1"

ARG MODE=test \
    BACKEND_HOME=/root/backend \
    PIP_MIRROR=1

ENV ENV_FILE=.env

COPY . $BACKEND_HOME
WORKDIR $BACKEND_HOME
RUN if [ $PIP_MIRROR = 1 ]; then \
        mkdir -p ~/.pip/ \
        && mv pip.conf ~/.pip/; \
    fi \
    && pip install --user --no-cache-dir --upgrade -r requirements/$MODE.txt \
    && echo $BACKEND_HOME > ~/.local/lib/python3.9/site-packages/mydefine.pth

EXPOSE 8000
CMD ["python", "src"]
# CMD ["uvicorn", "--env-file $ENV_FILE", "src:app"]
