FROM python:3.9-slim
LABEL maintainer="Yuri"
LABEL version="0.0.1"

ARG MODE=dev \
    BACKEND_HOME=/root/backend \
    PIP_MIRROR=1

COPY . $BACKEND_HOME
WORKDIR $BACKEND_HOME
RUN if [ $PIP_MIRROR = 1 ]; then \
        mkdir -p ~/.pip/ \
        && mv pip.conf ~/.pip/; \
    fi \
    && cat requirements/base.txt requirements/$MODE.txt > requirements.txt \
    && pip install --no-cache-dir -r requirements.txt \
    && echo $BACKEND_HOME > /usr/local/lib/python3.9/site-packages/mydefine.pth

EXPOSE 12345
CMD ["python", "src/main.py"]
