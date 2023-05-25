FROM python:3.9-slim
LABEL maintainer="Yuri"
LABEL version="0.0.1"

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' > /etc/timezone
RUN mkdir -p /root/.pip/ \
    && mkdir -p /home/backend/data/ \
    && echo "/home/backend" > /usr/local/lib/python3.9/site-packages/mydefine.pth

COPY . /home/backend/
COPY ./pip.conf /root/.pip/

WORKDIR /home/backend
RUN pip install --no-cache-dir -r requirements/base.txt 
RUN pip install --no-cache-dir -r requirements/dev.txt

EXPOSE 12345
CMD ["python", "src/main.py"]
