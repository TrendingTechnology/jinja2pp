FROM python:slim

WORKDIR /j2

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY j2pp.py .

ENTRYPOINT ["/j2/j2pp.py"]
