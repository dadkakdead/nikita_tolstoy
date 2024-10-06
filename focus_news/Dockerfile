FROM python:3.10

COPY requirements.txt /app/requirements.txt

WORKDIR /app

RUN python -m pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y postgresql-client

COPY . /app

CMD [ "python", "./core.py" ]
