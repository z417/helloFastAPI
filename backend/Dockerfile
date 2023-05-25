FROM python:3.9-slim
LABEL author="Yuri"
LABEL version="0.0.1"

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' > /etc/timezone
RUN mkdir -p /root/.pip/ &&

RUN git clone https://github.com/z417/helloFastAPI.git

WORKDIR helloFastAPI/backend

COPY ./pip.conf /root/.pip/

RUN pip3 install --no-cache-dir -r requirements/base.txt requirements/dev.txt

EXPOSE 12345
CMD ["python", "src/main.py"]
