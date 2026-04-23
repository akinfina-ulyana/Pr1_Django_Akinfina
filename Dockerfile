FROM python:3.12-alpine3.20

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy --system

WORKDIR /app

RUN apk add --no-cache gcc musl-dev postgresql-dev

COPY ./app /app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]