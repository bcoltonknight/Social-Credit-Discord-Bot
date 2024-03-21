FROM python:3.11
WORKDIR /app
COPY ./app .
RUN pip install -r requirements.txt
RUN mkdir /var/data
CMD ["python3", "app.py"]