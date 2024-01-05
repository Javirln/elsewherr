FROM bitnami/python:3.10.13

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY elsewherr.py .

CMD [ "python3", "-u",  "elsewherr.py"]