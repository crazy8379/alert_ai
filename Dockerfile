FROM python:3.11-slim 

ENV TZ=Asia/Shanghai

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app 

COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY src/ /app/

EXPOSE 8000 8001 

CMD ["python","monitor.py"]



